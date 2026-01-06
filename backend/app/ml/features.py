from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

# --- Data extraction (FPL schema) -------------------------------------------------

def load_flat_table(db: Session) -> pd.DataFrame:
    """
    Returns one row per (gw, player).
    Target columns:
      - started (classification)
      - expected_points_actual (regression)  -> uses total_points
    Feature raw columns:
      - minutes, total_points, goals, assists, xg, xa, ict_index, influence, creativity, threat
      - context: is_home, opp_strength_def, team_att, team_def, injury_flag, price
    """
    q = """SELECT
                s.gw,
                p.id AS player_id,
                p.team_id,
                p.position,
                CAST(p.price AS DOUBLE) AS price,
                p.status,
                COALESCE(p.chance_playing_next, 100) AS chance_playing_next,

                -- team strength
                t.strength_attack AS team_att,
                t.strength_defense AS team_def,

                -- opponent strength
                COALESCE(opp.strength_defense, 50) AS opp_strength_def,

                -- per-GW stats (targets + raw)
                s.started,
                s.minutes,
                s.total_points AS expected_points_actual,
                s.goals,
                s.assists,
                s.clean_sheet,
                s.saves,
                s.yellow,
                s.red,
                s.bonus,
                s.bps,
                s.influence,
                s.creativity,
                s.threat,
                s.ict_index,
                s.xg,
                s.xa,

                s.was_home AS is_home,
                COALESCE(s.difficulty, 3) AS difficulty
            FROM player_gameweek_stats s
            JOIN players p ON p.id = s.player_id
            JOIN teams t ON t.id = p.team_id
            LEFT JOIN teams opp ON opp.id = s.opponent_team_id
            ORDER BY s.gw ASC"""
    df = pd.DataFrame(db.execute(text(q)).mappings().all())
    if df.empty:
        return df

    # injury flag: not fit OR chance < 75
    df["injury_flag"] = ((df["status"] != "fit") | (df["chance_playing_next"].fillna(100) < 75)).astype(int)

    # ensure numeric
    for c in ["price","team_att","team_def","opp_strength_def","difficulty"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    return df

# --- Feature engineering -----------------------------------------------------------

def build_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.sort_values(["player_id","gw"]).copy()

    # numeric series we want rolling stats for
    num_cols = [
        "minutes","expected_points_actual","goals","assists",
        "xg","xa","ict_index","influence","creativity","threat",
        "bonus","bps"
    ]

    # shift by 1 to avoid leakage (use history only)
    for c in num_cols:
        s = df.groupby("player_id")[c].shift(1)
        df[f"{c}_avg_3"] = s.groupby(df["player_id"]).rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)
        df[f"{c}_avg_5"] = s.groupby(df["player_id"]).rolling(5, min_periods=1).mean().reset_index(level=0, drop=True)
        df[f"{c}_trend"] = df[f"{c}_avg_3"] - df[f"{c}_avg_5"]

    # fill NaNs for early GWs
    feat_cols = [c for c in df.columns if c.endswith("_avg_3") or c.endswith("_avg_5") or c.endswith("_trend")]
    df[feat_cols] = df[feat_cols].fillna(0.0)

    # ensure ints
    df["injury_flag"] = df["injury_flag"].astype(int)
    df["is_home"] = df["is_home"].astype(int)

    return df

def dataset_for_training(df_feat: pd.DataFrame):
    feature_cols = [c for c in df_feat.columns if c.endswith("_avg_3") or c.endswith("_avg_5") or c.endswith("_trend")]
    feature_cols += ["is_home","difficulty","opp_strength_def","team_att","team_def","injury_flag","price"]

    X = df_feat[feature_cols].astype(float)
    y_start = df_feat["started"].astype(int)
    y_points = df_feat["expected_points_actual"].astype(float)
    meta = df_feat[["player_id","gw","team_id","position"]]
    return X, y_start, y_points, meta, feature_cols

# --- Features for prediction -------------------------------------------------------

def features_for_gw(db: Session, gw: int) -> pd.DataFrame:
    """Return one row per player for a target GW, using only history < gw, and context for gw."""
    # We will build by taking latest known row per (player) from player_gameweek_stats where gw < target,
    # then attach the fixture context for gw.
    # If player has no history, rolling features will become 0.
    # We'll compute rolling features by loading flat table up to gw-1 and also a 'context' frame for gw.

    df_hist = load_flat_table(db)
    if df_hist.empty:
        return df_hist

    df_hist = df_hist[df_hist["gw"] < gw].copy()
    if df_hist.empty:
        return df_hist

    df_feat_hist = build_rolling_features(df_hist)

    # take ONLY rolling feature columns from the last available history row
    # (avoid duplicating context cols like is_home/difficulty on merge, which causes is_home_x/is_home_y)
    roll_cols = [c for c in df_feat_hist.columns if c.endswith("_avg_3") or c.endswith("_avg_5") or c.endswith("_trend")]
    last = (
        df_feat_hist.sort_values(["player_id", "gw"])
        .groupby("player_id")
        .tail(1)[["player_id", *roll_cols]]
        .copy()
    )

    # context for target gw from fixtures table
    q_ctx = """SELECT
                 p.id AS player_id,
                 p.team_id,
                 p.position,
                 CAST(p.price AS DOUBLE) AS price,
                 p.status,
                 COALESCE(p.chance_playing_next, 100) AS chance_playing_next,
                 t.strength_attack AS team_att,
                 t.strength_defense AS team_def,
                 -- determine opponent + home/away + difficulty from fixture
                 CASE
                   WHEN f.home_team_id = p.team_id THEN f.away_team_id
                   WHEN f.away_team_id = p.team_id THEN f.home_team_id
                   ELSE NULL
                 END AS opponent_team_id,
                 CASE
                   WHEN f.home_team_id = p.team_id THEN 1
                   WHEN f.away_team_id = p.team_id THEN 0
                   ELSE 0
                 END AS is_home,
                 CASE
                   WHEN f.home_team_id = p.team_id THEN f.home_difficulty
                   WHEN f.away_team_id = p.team_id THEN f.away_difficulty
                   ELSE 3
                 END AS difficulty,
                 COALESCE(opp.strength_defense, 50) AS opp_strength_def
               FROM players p
               JOIN teams t ON t.id = p.team_id
               LEFT JOIN matches f
                 ON f.gw = :gw AND (f.home_team_id = p.team_id OR f.away_team_id = p.team_id)
               LEFT JOIN teams opp
                 ON opp.id = (CASE
                   WHEN f.home_team_id = p.team_id THEN f.away_team_id
                   WHEN f.away_team_id = p.team_id THEN f.home_team_id
                   ELSE NULL
                 END)
               ORDER BY p.id"""
    ctx = pd.DataFrame(db.execute(text(q_ctx), {"gw": gw}).mappings().all())
    if ctx.empty:
        # if fixtures missing, still allow predicting with neutral context
        ctx = pd.DataFrame(db.execute(text("""SELECT p.id AS player_id, p.team_id, p.position,
                                              CAST(p.price AS DOUBLE) AS price, p.status,
                                              COALESCE(p.chance_playing_next, 100) AS chance_playing_next,
                                              t.strength_attack AS team_att, t.strength_defense AS team_def,
                                              0 AS is_home, 3 AS difficulty, 50 AS opp_strength_def
                                            FROM players p JOIN teams t ON t.id=p.team_id""")).mappings().all())

    ctx["injury_flag"] = ((ctx["status"] != "fit") | (ctx["chance_playing_next"].fillna(100) < 75)).astype(int)

    # merge rolling features
    out = ctx.merge(last, on="player_id", how="left")
    # fill missing rolling features with 0
    roll_cols = [c for c in out.columns if c.endswith("_avg_3") or c.endswith("_avg_5") or c.endswith("_trend")]
    out[roll_cols] = out[roll_cols].fillna(0.0)

    out["is_home"] = out["is_home"].astype(int)
    out["difficulty"] = pd.to_numeric(out["difficulty"], errors="coerce").fillna(3)
    out["opp_strength_def"] = pd.to_numeric(out["opp_strength_def"], errors="coerce").fillna(50)
    out["team_att"] = pd.to_numeric(out["team_att"], errors="coerce").fillna(50)
    out["team_def"] = pd.to_numeric(out["team_def"], errors="coerce").fillna(50)
    out["price"] = pd.to_numeric(out["price"], errors="coerce").fillna(5.0)

    return out
