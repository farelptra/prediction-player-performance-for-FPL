#!/usr/bin/env python
from __future__ import annotations

import os
import time
import argparse
from datetime import datetime
import requests
import pymysql
from dotenv import load_dotenv

load_dotenv()

FPL_BOOTSTRAP = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_FIXTURES = "https://fantasy.premierleague.com/api/fixtures/"
FPL_EVENT_LIVE = "https://fantasy.premierleague.com/api/event/{gw}/live/"

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "epl_predictor")

def connect():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )

def http_get(url, params=None, sleep_s=0.15):
    if params:
        print(f"GET {url} params={params}")
    else:
        print(f"GET {url}")
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    time.sleep(sleep_s)
    return r.json()

def truncate_all(cur):
    print("Truncating tables (predictions, player_gameweek_stats, matches, gameweeks, players, teams)...")
    # order matters because of FK
    cur.execute("SET FOREIGN_KEY_CHECKS=0;")
    for t in ["predictions","player_gameweek_stats","matches","gameweeks","players","teams"]:
        cur.execute(f"TRUNCATE TABLE {t};")
    cur.execute("SET FOREIGN_KEY_CHECKS=1;")

def map_position(element_type: int) -> str:
    # FPL element_type: 1 GK, 2 DEF, 3 MID, 4 FWD
    return {1:"GK",2:"DEF",3:"MID",4:"FWD"}.get(int(element_type), "MID")

def map_status(status: str, chance_next, chance_this) -> str:
    # FPL status usually: a (available), d (doubtful), i (injured), s (suspended), u (unavailable)
    s = (status or "").lower()
    if s == "a":
        return "fit"
    if s == "i":
        return "injured"
    if s == "s":
        return "suspended"
    if s == "d":
        return "doubt"
    # fallback: use chance
    try:
        if chance_next is not None and int(chance_next) < 75:
            return "doubt"
    except Exception:
        pass
    return "unknown"

def import_teams(cur, bootstrap):
    print("Importing teams...")
    teams = bootstrap["teams"]
    sql = """INSERT INTO teams
             (id, name, short_name, strength_attack, strength_defense, strength_overall_home, strength_overall_away)
             VALUES (%s,%s,%s,%s,%s,%s,%s)
             ON DUPLICATE KEY UPDATE
               name=VALUES(name),
               short_name=VALUES(short_name),
               strength_attack=VALUES(strength_attack),
               strength_defense=VALUES(strength_defense),
               strength_overall_home=VALUES(strength_overall_home),
               strength_overall_away=VALUES(strength_overall_away)
          """
    n=0
    for t in teams:
        # create a simple overall attack/def from home+away values if present
        sa = int(round((t.get("strength_attack_home", 50) + t.get("strength_attack_away", 50)) / 2))
        sd = int(round((t.get("strength_defence_home", 50) + t.get("strength_defence_away", 50)) / 2))
        cur.execute(sql, (
            int(t["id"]),
            t["name"],
            t.get("short_name"),
            sa, sd,
            t.get("strength_overall_home"),
            t.get("strength_overall_away"),
        ))
        n+=1
    print(f"Inserted/updated {n} teams.")

def import_players(cur, bootstrap):
    print("Importing players...")
    elements = bootstrap["elements"]
    sql = """INSERT INTO players
             (id, name, team_id, position, price, status, chance_playing_next, chance_playing_this,
              selected_by_percent, form, points_per_game, total_points, now_cost, photo)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
             ON DUPLICATE KEY UPDATE
               name=VALUES(name),
               team_id=VALUES(team_id),
               position=VALUES(position),
               price=VALUES(price),
               status=VALUES(status),
               chance_playing_next=VALUES(chance_playing_next),
               chance_playing_this=VALUES(chance_playing_this),
               selected_by_percent=VALUES(selected_by_percent),
               form=VALUES(form),
               points_per_game=VALUES(points_per_game),
               total_points=VALUES(total_points),
               now_cost=VALUES(now_cost),
               photo=VALUES(photo)
          """
    n=0
    for e in elements:
        pid = int(e["id"])
        name = (e.get("web_name") or f'{e.get("first_name","")} {e.get("second_name","")}'.strip()).strip()
        team_id = int(e["team"])
        pos = map_position(int(e["element_type"]))
        now_cost = int(e.get("now_cost", 0))
        price = float(now_cost) / 10.0 if now_cost else 5.0
        chance_next = e.get("chance_of_playing_next_round")
        chance_this = e.get("chance_of_playing_this_round")
        status = map_status(e.get("status"), chance_next, chance_this)

        def _to_float(x):
            try:
                return float(x) if x is not None and x != "" else None
            except Exception:
                return None

        cur.execute(sql, (
            pid, name, team_id, pos, price, status,
            chance_next, chance_this,
            _to_float(e.get("selected_by_percent")),
            _to_float(e.get("form")),
            _to_float(e.get("points_per_game")),
            int(e.get("total_points", 0)),
            now_cost,
            e.get("photo"),
        ))
        n+=1
    print(f"Inserted/updated {n} players.")

def import_gameweeks(cur, bootstrap):
    print("Importing gameweeks...")
    events = bootstrap["events"]
    sql = """INSERT INTO gameweeks (gw, name, deadline_time, finished, is_current, is_next)
             VALUES (%s,%s,%s,%s,%s,%s)
             ON DUPLICATE KEY UPDATE
               name=VALUES(name),
               deadline_time=VALUES(deadline_time),
               finished=VALUES(finished),
               is_current=VALUES(is_current),
               is_next=VALUES(is_next)
          """
    n=0
    for ev in events:
        gw = int(ev["id"])
        deadline = ev.get("deadline_time")
        # deadline is ISO: 2025-08-16T16:30:00Z; store as naive UTC string
        dt = None
        if deadline:
            try:
                dt = datetime.fromisoformat(deadline.replace("Z","+00:00")).replace(tzinfo=None)
            except Exception:
                dt = None
        cur.execute(sql, (
            gw,
            ev.get("name"),
            dt,
            1 if ev.get("finished") else 0,
            1 if ev.get("is_current") else 0,
            1 if ev.get("is_next") else 0,
        ))
        n+=1
    print(f"Inserted/updated {n} gameweeks.")
    # return finished gw list
    finished = [int(ev["id"]) for ev in events if ev.get("finished")]
    return finished

def import_fixtures(cur):
    print("Importing fixtures (matches)...")
    fixtures = http_get(FPL_FIXTURES)
    sql = """INSERT INTO matches
             (id, gw, kickoff_time, home_team_id, away_team_id, home_difficulty, away_difficulty, finished)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
             ON DUPLICATE KEY UPDATE
               gw=VALUES(gw),
               kickoff_time=VALUES(kickoff_time),
               home_team_id=VALUES(home_team_id),
               away_team_id=VALUES(away_team_id),
               home_difficulty=VALUES(home_difficulty),
               away_difficulty=VALUES(away_difficulty),
               finished=VALUES(finished)
          """
    n=0
    for f in fixtures:
        fid = int(f["id"])
        gw = f.get("event")
        gw = int(gw) if gw is not None else None
        kick = f.get("kickoff_time")
        kt = None
        if kick:
            try:
                kt = datetime.fromisoformat(kick.replace("Z","+00:00")).replace(tzinfo=None)
            except Exception:
                kt = None
        cur.execute(sql, (
            fid, gw, kt, int(f["team_h"]), int(f["team_a"]),
            f.get("team_h_difficulty"), f.get("team_a_difficulty"),
            1 if f.get("finished") else 0
        ))
        n+=1
    print(f"Inserted/updated {n} fixtures.")

def build_fixture_lookup(cur, gw: int):
    """Return dict team_id -> (opp_id, was_home, difficulty)."""
    cur.execute("""SELECT home_team_id, away_team_id, home_difficulty, away_difficulty
                   FROM matches WHERE gw=%s""", (gw,))
    lookup = {}
    for r in cur.fetchall():
        h = int(r["home_team_id"]); a = int(r["away_team_id"])
        lookup[h] = (a, 1, r.get("home_difficulty"))
        lookup[a] = (h, 0, r.get("away_difficulty"))
    return lookup

def import_gw_stats(cur, finished_gws, max_gw=None):
    if max_gw is not None:
        finished_gws = [g for g in finished_gws if g <= max_gw]
    finished_gws = sorted(finished_gws)
    print("Importing GW stats...")
    sql = """INSERT INTO player_gameweek_stats
             (gw, player_id, team_id, opponent_team_id, was_home, difficulty,
              started, minutes, total_points, goals, assists, clean_sheet, goals_conceded, saves,
             penalties_saved, penalties_missed, own_goals,
              yellow, red,
              bonus, bps, influence, creativity, threat, ict_index, xg, xa)
             VALUES (%s,%s,%s,%s,%s,%s,
                     %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                     %s,%s,%s,%s,%s,%s,%s,%s,%s)
             ON DUPLICATE KEY UPDATE
              team_id=VALUES(team_id),
              opponent_team_id=VALUES(opponent_team_id),
              was_home=VALUES(was_home),
              difficulty=VALUES(difficulty),
              started=VALUES(started),
              minutes=VALUES(minutes),
              total_points=VALUES(total_points),
              goals=VALUES(goals),
              assists=VALUES(assists),
              clean_sheet=VALUES(clean_sheet),
              goals_conceded=VALUES(goals_conceded),
              saves=VALUES(saves),
              penalties_saved=VALUES(penalties_saved),
              penalties_missed=VALUES(penalties_missed),
              own_goals=VALUES(own_goals),
              yellow=VALUES(yellow),
              red=VALUES(red),
              bonus=VALUES(bonus),
              bps=VALUES(bps),
              influence=VALUES(influence),
              creativity=VALUES(creativity),
              threat=VALUES(threat),
              ict_index=VALUES(ict_index),
              xg=VALUES(xg),
              xa=VALUES(xa)
          """
    # we need players team_id for lookup
    cur.execute("SELECT id, team_id FROM players")
    player_team = {int(r["id"]): int(r["team_id"]) for r in cur.fetchall()}

    for gw in finished_gws:
        print(f"  GW {gw}...")
        live = http_get(FPL_EVENT_LIVE.format(gw=gw))
        elements = live.get("elements", [])
        fixture_lookup = build_fixture_lookup(cur, gw)

        batch = 0
        for el in elements:
            pid = int(el["id"])
            stats = el.get("stats", {})
            team_id = player_team.get(pid)
            if team_id is None:
                continue

            opp_id, was_home, diff = fixture_lookup.get(team_id, (None, 0, None))

            minutes = int(stats.get("minutes", 0) or 0)
            starts = stats.get("starts")
            if starts is None:
                started = 1 if minutes >= 60 else 0
            else:
                started = 1 if int(starts) > 0 else 0

            def fnum(x, default=0.0):
                try:
                    if x is None or x == "":
                        return float(default)
                    return float(x)
                except Exception:
                    return float(default)

            # expected_goals / expected_assists fields exist on newer seasons; keep 0 if missing
            xg = fnum(stats.get("expected_goals", 0.0), 0.0)
            xa = fnum(stats.get("expected_assists", 0.0), 0.0)

            stat_map = {
                "goals": int(stats.get("goals_scored", 0) or 0),
                "assists": int(stats.get("assists", 0) or 0),
                "clean_sheet": int(stats.get("clean_sheets", 0) or 0),
                "goals_conceded": int(stats.get("goals_conceded", 0) or 0),
                "saves": int(stats.get("saves", 0) or 0),
                "penalties_saved": int(stats.get("penalties_saved", 0) or 0),
                "penalties_missed": int(stats.get("penalties_missed", 0) or 0),
                "own_goals": int(stats.get("own_goals", 0) or 0),
                "yellow": int(stats.get("yellow_cards", 0) or 0),
                "red": int(stats.get("red_cards", 0) or 0),
            }

            cur.execute(sql, (
                int(gw), pid, team_id, opp_id, was_home, diff,
                started, minutes,
                int(stats.get("total_points", 0) or 0),
                stat_map["goals"],
                stat_map["assists"],
                stat_map["clean_sheet"],
                stat_map["goals_conceded"],
                stat_map["saves"],
                stat_map["penalties_saved"],
                stat_map["penalties_missed"],
                stat_map["own_goals"],
                stat_map["yellow"],
                stat_map["red"],
                int(stats.get("bonus", 0) or 0),
                int(stats.get("bps", 0) or 0),
                fnum(stats.get("influence", 0.0), 0.0),
                fnum(stats.get("creativity", 0.0), 0.0),
                fnum(stats.get("threat", 0.0), 0.0),
                fnum(stats.get("ict_index", 0.0), 0.0),
                xg, xa
            ))
            batch += 1

        print(f"    upserted {batch} rows")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-gw", type=int, default=None, help="Only import finished gameweeks up to this GW")
    ap.add_argument("--no-truncate", action="store_true", help="Do not truncate tables before import")
    args = ap.parse_args()

    bootstrap = http_get(FPL_BOOTSTRAP)
    conn = connect()
    try:
        with conn.cursor() as cur:
            if not args.no_truncate:
                truncate_all(cur)

            import_teams(cur, bootstrap)
            import_players(cur, bootstrap)
            finished_gws = import_gameweeks(cur, bootstrap)
            import_fixtures(cur)

            conn.commit()

            import_gw_stats(cur, finished_gws, max_gw=args.max_gw)
            conn.commit()

        print("DONE.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
