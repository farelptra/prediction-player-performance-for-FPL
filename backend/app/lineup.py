from __future__ import annotations
from typing import List, Dict, Tuple

FORMATION_MAP = {
    "4-4-2": {"GK":1, "DEF":4, "MID":4, "FWD":2},
    "4-3-3": {"GK":1, "DEF":4, "MID":3, "FWD":3},
    "3-5-2": {"GK":1, "DEF":3, "MID":5, "FWD":2},
    "3-4-3": {"GK":1, "DEF":3, "MID":4, "FWD":3},
    "5-3-2": {"GK":1, "DEF":5, "MID":3, "FWD":2},
}

def generate_lineup(pred_rows: List[dict], formation: str="4-4-2", budget: float=100.0, max_per_team:int=3):
    if formation not in FORMATION_MAP:
        formation = "4-4-2"
    need = FORMATION_MAP[formation].copy()

    # score = expected_points * p_start
    rows = []
    for r in pred_rows:
        r = dict(r)
        status = (r.get("status") or "").lower()
        # Skip players who are marked as injured
        if status == "injured":
            continue
        r["p_start"] = float(r["p_start"])
        r["expected_points"] = float(r["expected_points"])
        r["price"] = float(r["price"])
        r["score"] = float(r["expected_points"] * r["p_start"])
        rows.append(r)

    # sort by score desc
    rows.sort(key=lambda x: x["score"], reverse=True)

    picked = []
    spent = 0.0
    team_count: Dict[int,int] = {}

    # greedy by best available for each position count
    for pos in ["GK","DEF","MID","FWD"]:
        candidates = [r for r in rows if r["position"] == pos]
        for r in candidates:
            if need[pos] <= 0:
                break
            if spent + r["price"] > budget:
                continue
            tid = int(r["team_id"])
            if team_count.get(tid,0) >= max_per_team:
                continue
            # avoid duplicates
            if any(p["player_id"] == r["player_id"] for p in picked):
                continue
            picked.append(r)
            spent += r["price"]
            team_count[tid] = team_count.get(tid,0) + 1
            need[pos] -= 1

    # if not complete, fill remaining regardless of position (still respect budget/team cap)
    remaining = sum(need.values())
    if remaining > 0:
        for r in rows:
            if remaining <= 0:
                break
            if any(p["player_id"] == r["player_id"] for p in picked):
                continue
            if spent + r["price"] > budget:
                continue
            tid = int(r["team_id"])
            if team_count.get(tid,0) >= max_per_team:
                continue
            picked.append(r)
            spent += r["price"]
            team_count[tid] = team_count.get(tid,0) + 1
            remaining -= 1

    total_expected = sum(float(p["expected_points"]) for p in picked)
    total_score = sum(float(p["score"]) for p in picked)
    return picked, total_expected, total_score
