from __future__ import annotations

from collections import defaultdict

def parse_formation(formation: str):
    """Parse formation like '4-4-2' into position requirements."""
    parts = [int(x) for x in str(formation).split("-") if x]
    if len(parts) != 3:
        raise ValueError("Formation must be like 4-4-2")
    return {"GK": 1, "DEF": parts[0], "MID": parts[1], "FWD": parts[2]}

def build_actual_lineup(candidates, formation: str = "4-4-2", max_per_team: int = 3):
    need = parse_formation(formation)

    by_pos = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for c in candidates:
        pos = c.get("position")
        if pos in by_pos:
            by_pos[pos].append(c)

    # sort desc by total_points
    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: (x.get("total_points") or 0), reverse=True)

    chosen = []
    team_count = defaultdict(int)

    def pick(pos, n):
        nonlocal chosen
        for p in by_pos[pos]:
            if n <= 0:
                break
            if team_count[p["team_id"]] >= max_per_team:
                continue
            chosen.append(p)
            team_count[p["team_id"]] += 1
            n -= 1
        if n > 0:
            raise ValueError(f"Not enough players to fill position {pos}")

    pick("GK", need["GK"])
    pick("DEF", need["DEF"])
    pick("MID", need["MID"])
    pick("FWD", need["FWD"])

    out_players = []
    total = 0.0
    for p in chosen:
        tp = float(p.get("total_points") or 0)
        total += tp
        out_players.append({
            "player_id": p["player_id"],
            "name": p["name"],
            "team_id": p["team_id"],
            "position": p["position"],
            "price": float(p.get("price") or 0),
            "total_points": tp,
            "score": tp,  # keep field for frontend consistency
            "photo": p.get("photo"),
        })

    return out_players, total
