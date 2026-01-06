from __future__ import annotations

import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import get_db
from . import crud
from .schemas import (
    TeamOut,
    TeamFixtureOut,
    PlayerOut,
    PlayerDetailOut,
    PlayerHistory,
    LeadersOut,
    PredictResponse,
    LineupRequest,
    LineupResponse,
    ActualLineupRequest,
    ActualLineupResponse,
)
from .ml.predict import predict_gw
from .lineup import generate_lineup
from .services.lineup_actual import build_actual_lineup

MODEL_DIR = os.getenv("MODEL_DIR", "./models_store")
MODEL_VERSION = os.getenv("MODEL_VERSION", "rf_v1")

app = FastAPI(title="EPL Lineup & Performance Predictor (FPL)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True, "model_version": MODEL_VERSION}


@app.get("/meta")
def api_meta(db: Session = Depends(get_db)):
    """Helper for UI: current/next/last-finished GW (requires import_fpl_api.py)."""
    m = crud.get_meta(db) or {}
    return {
        "current_gw": int(m["current_gw"]) if m.get("current_gw") is not None else None,
        "next_gw": int(m["next_gw"]) if m.get("next_gw") is not None else None,
        "last_finished_gw": int(m["max_finished_gw"]) if m.get("max_finished_gw") is not None else None,
        "max_stats_gw": int(m["max_stats_gw"]) if m.get("max_stats_gw") is not None else None,
    }

@app.get("/leaders", response_model=LeadersOut)
def api_leaders(limit: int = 5, db: Session = Depends(get_db)):
    safe_limit = max(1, min(int(limit or 5), 50))
    rows = crud.get_leaders(db, limit=safe_limit)
    def to_list(key: str):
        out = []
        for r in rows.get(key, []):
            out.append({
                "player_id": int(r["player_id"]),
                "name": r["name"],
                "position": r["position"],
                "team_id": int(r["team_id"]),
                "team_short": r.get("team_short"),
                "minutes": int(r["minutes"]) if r.get("minutes") is not None else None,
                "avg_bps": float(r["avg_bps"]) if r.get("avg_bps") is not None else None,
                "goals": int(r.get("goals") or 0),
                "assists": int(r.get("assists") or 0),
                "saves": int(r.get("saves") or 0),
                "yellow": int(r.get("yellow") or 0),
                "red": int(r.get("red") or 0),
                "bonus": int(r.get("bonus") or 0),
            })
        return out
    return {
        "top_scorers": to_list("top_scorers"),
        "top_assists": to_list("top_assists"),
        "most_yellow": to_list("most_yellow"),
        "most_red": to_list("most_red"),
        "most_pom": to_list("most_pom"),
        "best_gk": to_list("best_gk"),
    }


@app.get("/teams", response_model=list[TeamOut])
def api_list_teams(db: Session = Depends(get_db)):
    rows = crud.list_teams(db)
    return [dict(r) for r in rows]

@app.get("/teams/{team_id}/next-fixture", response_model=TeamFixtureOut | None)
def api_team_next_fixture(team_id: int, db: Session = Depends(get_db)):
    r = crud.get_team_next_fixture(db, team_id)
    if not r:
        return None
    is_home = 1 if int(r["home_team_id"]) == team_id else 0
    opponent_team_id = int(r["away_team_id"]) if is_home else int(r["home_team_id"])
    opponent_name = r["away_name"] if is_home else r["home_name"]
    opponent_short = r["away_short"] if is_home else r["home_short"]
    kickoff = r["kickoff_time"].isoformat() if r.get("kickoff_time") else None
    return {
        "gw": int(r["gw"]) if r.get("gw") is not None else None,
        "kickoff_time": kickoff,
        "finished": int(r.get("finished") or 0),
        "is_home": int(is_home),
        "opponent_team_id": opponent_team_id,
        "opponent_name": opponent_name,
        "opponent_short": opponent_short,
    }

@app.get("/teams/{team_id}/last-fixture", response_model=TeamFixtureOut | None)
def api_team_last_fixture(team_id: int, db: Session = Depends(get_db)):
    r = crud.get_team_last_fixture(db, team_id)
    if not r:
        return None
    is_home = 1 if int(r["home_team_id"]) == team_id else 0
    opponent_team_id = int(r["away_team_id"]) if is_home else int(r["home_team_id"])
    opponent_name = r["away_name"] if is_home else r["home_name"]
    opponent_short = r["away_short"] if is_home else r["home_short"]
    kickoff = r["kickoff_time"].isoformat() if r.get("kickoff_time") else None
    return {
        "gw": int(r["gw"]) if r.get("gw") is not None else None,
        "kickoff_time": kickoff,
        "finished": int(r.get("finished") or 0),
        "is_home": int(is_home),
        "opponent_team_id": opponent_team_id,
        "opponent_name": opponent_name,
        "opponent_short": opponent_short,
    }


@app.get("/fixtures/gw/{gw}")
def api_fixtures_gw(gw: int, db: Session = Depends(get_db)):
    """Return fixtures (matches table) for a GW with team names."""
    rows = crud.list_matches_for_gw(db, gw)
    return [dict(r) for r in rows]


@app.get("/players", response_model=list[PlayerOut])
def api_list_players(
    search: str | None = None,
    team_id: int | None = None,
    position: str | None = None,
    db: Session = Depends(get_db),
):
    rows = crud.list_players(db, search=search, team_id=team_id, position=position)
    return [dict(r) for r in rows]


@app.get("/players/{player_id}", response_model=PlayerDetailOut)
def api_get_player(player_id: int, db: Session = Depends(get_db)):
    r = crud.get_player(db, player_id)
    if not r:
        raise HTTPException(404, "Player not found")
    out = {
        "id": r["id"],
        "name": r["name"],
        "team_id": r["team_id"],
        "team_name": r.get("t_name"),
        "team_short": r.get("t_short"),
        "position": r["position"],
        "price": float(r["price"]),
        "status": r["status"],
        "team": {
            "id": r["t_id"],
            "name": r["t_name"],
            "short_name": r.get("t_short"),
            "strength_attack": int(r["strength_attack"]),
            "strength_defense": int(r["strength_defense"]),
        },
        "photo": r.get("photo"),
    }
    return out


@app.get("/players/{player_id}/history", response_model=list[PlayerHistory])
def api_player_history(
    player_id: int,
    from_gw: int = 1,
    to_gw: int = 99,
    db: Session = Depends(get_db),
):
    rows = crud.get_player_history(db, player_id, from_gw, to_gw)
    return [dict(r) for r in rows]


@app.get("/predictions/gw/{gw}")
def api_predictions_gw(
    gw: int,
    team_id: int | None = None,
    position: str | None = None,
    db: Session = Depends(get_db),
):
    rows = crud.get_predictions_for_gw(db, gw, team_id, position)
    if not rows:
        # Try auto-predict if missing
        try:
            new_rows = predict_gw(db, gw=gw, model_dir=MODEL_DIR, model_version=MODEL_VERSION)
            payload = [
                {
                    "player_id": int(r["player_id"]),
                    "p_start": float(r["p_start"]),
                    "expected_points": float(r["expected_points"]),
                    "model_version": MODEL_VERSION,
                }
                for r in new_rows
            ]
            if payload:
                crud.upsert_predictions(db, gw, payload)
                rows = crud.get_predictions_for_gw(db, gw, team_id, position)
        except Exception as e:
            raise HTTPException(400, f"No predictions for this GW and auto-predict failed: {e}")
    out = []
    for r in rows:
        out.append(
            {
                "gw": int(r["gw"]),
                "player_id": int(r["player_id"]),
                "name": r["name"],
                "team_id": int(r["team_id"]),
                "position": r["position"],
                "price": float(r["price"]),
                "p_start": float(r["p_start"]),
                "expected_points": float(r["expected_points"]),
                "model_version": r["model_version"],
            }
        )
    return out


@app.post("/predict/gw/{gw}", response_model=PredictResponse)
def api_predict_gw(gw: int, db: Session = Depends(get_db)):
    try:
        rows = predict_gw(db, gw=gw, model_dir=MODEL_DIR, model_version=MODEL_VERSION)
    except Exception as e:
        raise HTTPException(400, str(e))

    if not rows:
        raise HTTPException(400, f"No features/data for GW {gw}. Past stats might be missing.")

    payload = [
        {
            "player_id": int(r["player_id"]),
            "p_start": float(r["p_start"]),
            "expected_points": float(r["expected_points"]),
            "model_version": MODEL_VERSION,
        }
        for r in rows
    ]
    inserted = crud.upsert_predictions(db, gw, payload)
    return {"gw": gw, "model_version": MODEL_VERSION, "inserted": inserted}


@app.post("/lineup/gw/{gw}", response_model=LineupResponse)
def api_lineup(gw: int, req: LineupRequest, db: Session = Depends(get_db)):
    rows = crud.get_predictions_for_gw(db, gw)
    if not rows:
        # Attempt auto-predict if missing
        try:
            new_rows = predict_gw(db, gw=gw, model_dir=MODEL_DIR, model_version=MODEL_VERSION)
            payload = [
                {
                    "player_id": int(r["player_id"]),
                    "p_start": float(r["p_start"]),
                    "expected_points": float(r["expected_points"]),
                    "model_version": MODEL_VERSION,
                }
                for r in new_rows
            ]
            crud.upsert_predictions(db, gw, payload)
            rows = crud.get_predictions_for_gw(db, gw)
        except Exception as e:
            raise HTTPException(400, f"No predictions for this GW and auto-train failed: {e}")
    if not rows:
        raise HTTPException(400, "No predictions for this GW. Run POST /predict/gw/{gw} first.")

    pred_rows = []
    for r in rows:
        pred_rows.append(
            {
                "player_id": int(r["player_id"]),
                "name": r["name"],
                "team_id": int(r["team_id"]),
                "position": r["position"],
                "price": float(r["price"]),
                "p_start": float(r["p_start"]),
                "expected_points": float(r["expected_points"]),
                "status": r.get("status"),
                "photo": r.get("photo"),
                "team_short": r.get("team_short"),
            }
        )

    picked, total_expected, total_score = generate_lineup(
        pred_rows, formation=req.formation, budget=req.budget, max_per_team=req.max_per_team
    )
    return {
        "formation": req.formation,
        "budget": req.budget,
        "total_expected_points": float(total_expected),
        "total_score": float(total_score),
        "players": picked,
    }

@app.post("/lineup/actual/gw/{gw}", response_model=ActualLineupResponse)
def api_lineup_actual(gw: int, body: ActualLineupRequest, db: Session = Depends(get_db)):
    candidates = crud.get_actual_candidates(db, gw)
    if not candidates:
        raise HTTPException(404, "No gameweek stats found for this GW. Import FPL stats first.")
    try:
        players, total = build_actual_lineup(
            candidates,
            formation=body.formation,
            max_per_team=body.max_per_team,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "gw": gw,
        "formation": body.formation,
        "total_score": float(total),
        "players": players,
    }
