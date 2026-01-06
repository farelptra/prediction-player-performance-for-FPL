from __future__ import annotations
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Boolean, BigInteger, DECIMAL, TIMESTAMP, text

Base = declarative_base()

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    name = Column(String(96), nullable=False)
    short_name = Column(String(16), nullable=True)

    strength_attack = Column(Integer, nullable=False, default=50)
    strength_defense = Column(Integer, nullable=False, default=50)
    strength_overall_home = Column(Integer, nullable=True)
    strength_overall_away = Column(Integer, nullable=True)

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    position = Column(Enum("GK","DEF","MID","FWD"), nullable=False)

    price = Column(DECIMAL(5,2), nullable=False, default=5.00)
    status = Column(Enum("fit","injured","doubt","suspended","unknown"), nullable=False, default="fit")

    chance_playing_next = Column(Integer, nullable=True)
    chance_playing_this = Column(Integer, nullable=True)
    selected_by_percent = Column(DECIMAL(6,3), nullable=True)
    form = Column(DECIMAL(6,3), nullable=True)
    points_per_game = Column(DECIMAL(6,3), nullable=True)
    total_points = Column(Integer, nullable=True)
    now_cost = Column(Integer, nullable=True)
    photo = Column(String(64), nullable=True)

    team = relationship("Team")

class Gameweek(Base):
    __tablename__ = "gameweeks"
    gw = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=True)
    deadline_time = Column(DateTime, nullable=True)
    finished = Column(Boolean, nullable=False, default=False)
    is_current = Column(Boolean, nullable=False, default=False)
    is_next = Column(Boolean, nullable=False, default=False)

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)  # FPL fixture id
    gw = Column(Integer, nullable=True)
    kickoff_time = Column(DateTime, nullable=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_difficulty = Column(Integer, nullable=True)
    away_difficulty = Column(Integer, nullable=True)
    finished = Column(Boolean, nullable=False, default=False)

class PlayerGameweekStats(Base):
    __tablename__ = "player_gameweek_stats"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gw = Column(Integer, nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    opponent_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    was_home = Column(Boolean, nullable=False, default=False)
    difficulty = Column(Integer, nullable=True)

    started = Column(Boolean, nullable=False, default=False)
    minutes = Column(Integer, nullable=False, default=0)

    total_points = Column(Integer, nullable=False, default=0)
    goals = Column(Integer, nullable=False, default=0)
    assists = Column(Integer, nullable=False, default=0)
    clean_sheet = Column(Integer, nullable=False, default=0)
    goals_conceded = Column(Integer, nullable=False, default=0)
    saves = Column(Integer, nullable=False, default=0)
    penalties_saved = Column(Integer, nullable=False, default=0)
    penalties_missed = Column(Integer, nullable=False, default=0)
    own_goals = Column(Integer, nullable=False, default=0)
    yellow = Column(Integer, nullable=False, default=0)
    red = Column(Integer, nullable=False, default=0)
    bonus = Column(Integer, nullable=False, default=0)
    bps = Column(Integer, nullable=False, default=0)

    influence = Column(Float, nullable=False, default=0.0)
    creativity = Column(Float, nullable=False, default=0.0)
    threat = Column(Float, nullable=False, default=0.0)
    ict_index = Column(Float, nullable=False, default=0.0)
    xg = Column(Float, nullable=False, default=0.0)
    xa = Column(Float, nullable=False, default=0.0)

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gw = Column(Integer, nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    p_start = Column(Float, nullable=False)
    expected_points = Column(Float, nullable=False)
    model_version = Column(String(32), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
