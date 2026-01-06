from __future__ import annotations
import os, random
import pymysql
from datetime import date

random.seed(42)

DB_HOST = os.getenv("DB_HOST","127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT","3306"))
DB_USER = os.getenv("DB_USER","root")
DB_PASS = os.getenv("DB_PASS","")
DB_NAME = os.getenv("DB_NAME","epl_predictor")

def connect():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME, charset="utf8mb4", autocommit=True)

def fpl_like_points(position: str, minutes: int, goals:int, assists:int, clean_sheet:int, saves:int, yellow:int, red:int) -> float:
    pts = 0.0
    if minutes >= 60: pts += 2
    elif minutes > 0: pts += 1
    if goals:
        if position in ("DEF","GK"): pts += goals*6
        elif position == "MID": pts += goals*5
        else: pts += goals*4
    pts += assists*3
    if clean_sheet:
        if position in ("DEF","GK"): pts += 4
        elif position == "MID": pts += 1
    if position == "GK":
        pts += (saves//3)*1
    pts -= yellow
    pts -= red*3
    return pts

def main():
    conn = connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # fetch matches
    cur.execute("SELECT id, gw, home_team_id, away_team_id, home_goals, away_goals FROM matches ORDER BY gw, id")
    matches = cur.fetchall()

    # fetch players grouped by team
    cur.execute("SELECT id, team_id, position FROM players ORDER BY team_id, id")
    players = cur.fetchall()
    team_players = {}
    for p in players:
        team_players.setdefault(p["team_id"], []).append(p)

    # clear old stats
    cur.execute("DELETE FROM player_match_stats")

    def pick_starters(team_id):
        plist = team_players[team_id]
        gk = [p for p in plist if p["position"]=="GK"][:1]
        defs = [p for p in plist if p["position"]=="DEF"][:4]
        mids = [p for p in plist if p["position"]=="MID"][:4]
        fwds = [p for p in plist if p["position"]=="FWD"][:2]
        starters = gk+defs+mids+fwds
        bench = [p for p in plist if p not in starters]
        return starters, bench

    insert_sql = """INSERT INTO player_match_stats
        (match_id, player_id, started, minutes, goals, assists, shots, key_passes, xg, xa, clean_sheet, saves, yellow, red)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

    for m in matches:
        match_id = m["id"]
        home = m["home_team_id"]
        away = m["away_team_id"]
        home_goals = m["home_goals"] or 0
        away_goals = m["away_goals"] or 0

        # starters/bench
        home_starters, home_bench = pick_starters(home)
        away_starters, away_bench = pick_starters(away)

        def add_team(team_id, starters, bench, goals_for, goals_against):
            clean_sheet = 1 if goals_against == 0 else 0
            # distribute goals among FW/MID mostly
            scorers_pool = [p for p in starters if p["position"] in ("FWD","MID")] or starters
            assists_pool = [p for p in starters if p["position"] in ("MID","FWD")] or starters

            goals_map = {p["id"]:0 for p in starters+bench}
            assists_map = {p["id"]:0 for p in starters+bench}
            for _ in range(goals_for):
                s = random.choice(scorers_pool)
                goals_map[s["id"]] += 1
                if random.random() < 0.7:
                    a = random.choice(assists_pool)
                    if a["id"] != s["id"]:
                        assists_map[a["id"]] += 1

            for p in starters:
                minutes = random.randint(70,95)
                shots = random.randint(0,5) + goals_map[p["id"]]*2
                keyp = random.randint(0,4) + assists_map[p["id"]]
                xg = round(min(3.5, shots*0.12 + goals_map[p["id"]]*0.3 + random.random()*0.2), 2)
                xa = round(min(2.5, keyp*0.10 + assists_map[p["id"]]*0.25 + random.random()*0.15), 2)
                saves = random.randint(0,6) if p["position"]=="GK" else 0
                y = 1 if random.random() < 0.08 else 0
                r = 1 if random.random() < 0.01 else 0
                cur.execute(insert_sql, (match_id, p["id"], 1, minutes, goals_map[p["id"]], assists_map[p["id"]],
                                        shots, keyp, xg, xa,
                                        clean_sheet if p["position"] in ("DEF","GK") else 0,
                                        saves, y, r))
            for p in bench:
                minutes = random.choice([0,0,0,10,15,20,25,30])
                if minutes == 0 and random.random() < 0.1:
                    minutes = 5
                shots = random.randint(0,2)
                keyp = random.randint(0,2)
                xg = round(min(1.0, shots*0.10 + random.random()*0.1), 2)
                xa = round(min(0.8, keyp*0.08 + random.random()*0.1), 2)
                saves = random.randint(0,3) if p["position"]=="GK" and minutes>0 else 0
                y = 1 if random.random() < 0.05 else 0
                r = 1 if random.random() < 0.005 else 0
                cur.execute(insert_sql, (match_id, p["id"], 0, minutes, 0, 0, shots, keyp, xg, xa, 0, saves, y, r))

        add_team(home, home_starters, home_bench, home_goals, away_goals)
        add_team(away, away_starters, away_bench, away_goals, home_goals)

    print("Dummy player_match_stats generated for all matches.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
