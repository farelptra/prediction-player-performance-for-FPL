from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any

def list_players(db: Session, search: Optional[str]=None, team_id: Optional[int]=None, position: Optional[str]=None, limit:int=200):
    q = """SELECT p.id, p.name, p.team_id, p.position, p.price, p.status, p.photo,
                   t.name AS team_name, t.short_name AS team_short
            FROM players p
            LEFT JOIN teams t ON t.id = p.team_id
            WHERE 1=1"""
    params: Dict[str, Any] = {}
    if search:
        q += " AND p.name LIKE :search"
        params["search"] = f"%{search}%"
    if team_id:
        q += " AND p.team_id = :team_id"
        params["team_id"] = team_id
    if position:
        q += " AND p.position = :position"
        params["position"] = position
    q += " ORDER BY p.team_id, p.position, p.name LIMIT :limit"
    params["limit"] = limit
    return db.execute(text(q), params).mappings().all()

def list_teams(db: Session):
    q = """SELECT id, name, short_name, strength_attack, strength_defense
             FROM teams
             ORDER BY name ASC"""
    return db.execute(text(q)).mappings().all()

def get_gw_meta(db: Session):
    """Return current/next GW from gameweeks table (may be empty if not imported)."""
    q = """SELECT
             MAX(CASE WHEN is_current=1 THEN gw END) AS current_gw,
             MAX(CASE WHEN is_next=1 THEN gw END) AS next_gw
           FROM gameweeks"""
    return db.execute(text(q)).mappings().first()

def list_matches_for_gw(db: Session, gw: int):
    q = """SELECT m.id, m.gw, m.kickoff_time,
                    m.home_team_id, ht.name AS home_team_name, ht.short_name AS home_team_short,
                    m.away_team_id, at.name AS away_team_name, at.short_name AS away_team_short,
                    m.home_difficulty, m.away_difficulty, m.finished
             FROM matches m
             JOIN teams ht ON ht.id = m.home_team_id
             JOIN teams at ON at.id = m.away_team_id
             WHERE m.gw = :gw
             ORDER BY m.kickoff_time ASC, m.id ASC"""
    return db.execute(text(q), {"gw": gw}).mappings().all()

def get_player(db: Session, player_id: int):
    q = """SELECT p.id, p.name, p.team_id, p.position, p.price, p.status, p.photo,
                    t.id AS t_id, t.name AS t_name, t.short_name AS t_short, t.strength_attack, t.strength_defense
             FROM players p
             JOIN teams t ON t.id = p.team_id
             WHERE p.id = :pid"""
    row = db.execute(text(q), {"pid": player_id}).mappings().first()
    return row

def get_player_history(db: Session, player_id: int, from_gw:int=1, to_gw:int=99):
    q = """SELECT s.gw, s.minutes, s.total_points, s.goals, s.assists,
                    s.clean_sheet, s.goals_conceded, s.saves, s.penalties_saved, s.penalties_missed, s.own_goals,
                    s.yellow, s.red,
                    s.influence, s.creativity, s.threat, s.ict_index, s.xg, s.xa, s.started
             FROM player_gameweek_stats s
             WHERE s.player_id = :pid AND s.gw BETWEEN :from_gw AND :to_gw
             ORDER BY s.gw ASC"""
    return [dict(r) for r in db.execute(text(q), {'pid': player_id, 'from_gw': from_gw, 'to_gw': to_gw}).mappings().all()]

def get_predictions_for_gw(db: Session, gw:int, team_id: int|None=None, position: str|None=None):
    q = """SELECT pr.gw, pr.player_id, pr.p_start, pr.expected_points, pr.model_version,
                    p.name, p.team_id, p.position, p.price, p.status, p.photo,
                    t.short_name AS team_short
             FROM predictions pr
             JOIN players p ON p.id = pr.player_id
             LEFT JOIN teams t ON t.id = p.team_id
             WHERE pr.gw = :gw"""
    params = {"gw": gw}
    if team_id:
        q += " AND p.team_id = :team_id"
        params["team_id"] = team_id
    if position:
        q += " AND p.position = :position"
        params["position"] = position
    q += " ORDER BY pr.expected_points DESC"
    return db.execute(text(q), params).mappings().all()

def get_actual_candidates(db: Session, gw: int):
    q = text("""
        SELECT
          p.id AS player_id,
          p.name AS name,
          p.team_id AS team_id,
          p.position AS position,
          COALESCE(p.price, 0) AS price,
          p.photo AS photo,
          t.short_name AS team_short,
          s.total_points AS total_points
        FROM player_gameweek_stats s
        JOIN players p ON p.id = s.player_id
        LEFT JOIN teams t ON t.id = p.team_id
        WHERE s.gw = :gw
        ORDER BY s.total_points DESC
    """)
    rows = db.execute(q, {"gw": gw}).mappings().all()
    return [dict(r) for r in rows]

def upsert_predictions(db: Session, gw:int, rows: list[dict]):
    # rows: {player_id, p_start, expected_points, model_version}
    sql = """INSERT INTO predictions (gw, player_id, p_start, expected_points, model_version)
             VALUES (:gw, :player_id, :p_start, :expected_points, :model_version)
             ON DUPLICATE KEY UPDATE
               p_start=VALUES(p_start),
               expected_points=VALUES(expected_points),
               model_version=VALUES(model_version)"""
    inserted = 0
    for r in rows:
        db.execute(text(sql), {"gw": gw, **r})
        inserted += 1
    db.commit()
    return inserted

def get_meta(db: Session):
    current = db.execute(text("SELECT gw FROM gameweeks WHERE is_current=1 ORDER BY gw DESC LIMIT 1")).mappings().first()
    nxt = db.execute(text("SELECT gw FROM gameweeks WHERE is_next=1 ORDER BY gw ASC LIMIT 1")).mappings().first()
    max_finished = db.execute(text("SELECT MAX(gw) AS gw FROM gameweeks WHERE finished=1")).mappings().first()
    max_stats = db.execute(text("SELECT MAX(gw) AS gw FROM player_gameweek_stats")).mappings().first()
    return {
        "current_gw": current["gw"] if current else None,
        "next_gw": nxt["gw"] if nxt else None,
        "max_finished_gw": max_finished["gw"] if max_finished and max_finished["gw"] is not None else None,
        "max_stats_gw": max_stats["gw"] if max_stats and max_stats["gw"] is not None else None,
    }

def get_team_next_fixture(db: Session, team_id: int):
    q = """SELECT m.gw, m.kickoff_time, m.finished, m.home_team_id, m.away_team_id,
                  m.home_difficulty, m.away_difficulty,
                  th.name AS home_name, th.short_name AS home_short,
                  ta.name AS away_name, ta.short_name AS away_short
           FROM matches m
           JOIN teams th ON th.id = m.home_team_id
           JOIN teams ta ON ta.id = m.away_team_id
           WHERE (m.home_team_id=:tid OR m.away_team_id=:tid) AND m.kickoff_time IS NOT NULL AND m.finished=0
           ORDER BY m.kickoff_time ASC
           LIMIT 1"""
    return db.execute(text(q), {"tid": team_id}).mappings().first()

def get_team_last_fixture(db: Session, team_id: int):
    q = """SELECT m.gw, m.kickoff_time, m.finished, m.home_team_id, m.away_team_id,
                  m.home_difficulty, m.away_difficulty,
                  th.name AS home_name, th.short_name AS home_short,
                  ta.name AS away_name, ta.short_name AS away_short
           FROM matches m
           JOIN teams th ON th.id = m.home_team_id
           JOIN teams ta ON ta.id = m.away_team_id
           WHERE (m.home_team_id=:tid OR m.away_team_id=:tid) AND m.kickoff_time IS NOT NULL AND m.finished=1
           ORDER BY m.kickoff_time DESC
           LIMIT 1"""
    return db.execute(text(q), {"tid": team_id}).mappings().first()

def _leader_query(order_by: str, extra_where: str = ""):
    where_clause = f"WHERE {extra_where}" if extra_where else ""
    return f"""
        SELECT
            p.id AS player_id, p.name, p.position, p.team_id,
            t.short_name AS team_short,
            SUM(s.minutes) AS minutes,
            SUM(s.goals) AS goals,
            SUM(s.assists) AS assists,
            SUM(s.saves) AS saves,
            SUM(s.yellow) AS yellow,
            SUM(s.red) AS red,
            SUM(s.bonus) AS bonus
        FROM player_gameweek_stats s
        JOIN players p ON p.id = s.player_id
        LEFT JOIN teams t ON t.id = p.team_id
        {where_clause}
        GROUP BY p.id, p.name, p.position, p.team_id, t.short_name
        ORDER BY {order_by}, p.name ASC
        LIMIT :limit
    """

def get_leaders(db: Session, limit: int = 5):
    def fetch(order_by: str, extra_where: str = ""):
        q = _leader_query(order_by, extra_where)
        return db.execute(text(q), {"limit": limit}).mappings().all()

    pom_q = """
        SELECT
            p.id AS player_id, p.name, p.position, p.team_id,
            t.short_name AS team_short,
            AVG(s.bps) AS avg_bps,
            SUM(s.minutes) AS minutes,
            SUM(s.goals) AS goals,
            SUM(s.assists) AS assists,
            SUM(s.bonus) AS bonus
        FROM players p
        JOIN player_gameweek_stats s ON s.player_id = p.id
        LEFT JOIN teams t ON t.id = p.team_id
        WHERE s.minutes >= 60
        GROUP BY p.id, p.name, p.position, p.team_id, t.short_name
        HAVING SUM(s.minutes) >= 900
        ORDER BY avg_bps DESC, minutes DESC
        LIMIT :limit
    """

    best_gk_q = """
        SELECT
            p.id AS player_id, p.name, p.position, p.team_id,
            t.short_name AS team_short,
            AVG(s.bps) AS avg_bps,
            SUM(s.minutes) AS minutes,
            SUM(s.saves) AS saves,
            SUM(s.clean_sheet) AS clean_sheet,
            SUM(s.goals_conceded) AS goals_conceded
        FROM players p
        JOIN player_gameweek_stats s ON s.player_id = p.id
        LEFT JOIN teams t ON t.id = p.team_id
        WHERE p.position = 'GK' AND s.minutes >= 60
        GROUP BY p.id, p.name, p.position, p.team_id, t.short_name
        HAVING SUM(s.minutes) >= 900
        ORDER BY avg_bps DESC, minutes DESC
        LIMIT :limit
    """

    return {
        "top_scorers": fetch("SUM(s.goals) DESC, SUM(s.assists) DESC"),
        "top_assists": fetch("SUM(s.assists) DESC, SUM(s.goals) DESC"),
        "most_yellow": fetch("SUM(s.yellow) DESC"),
        "most_red": fetch("SUM(s.red) DESC"),
        "most_pom": db.execute(text(pom_q), {"limit": limit}).mappings().all(),
        "best_gk": db.execute(text(best_gk_q), {"limit": limit}).mappings().all(),
    }
