from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import date

Position = Literal["GK","DEF","MID","FWD"]

class TeamOut(BaseModel):
    id: int
    name: str
    short_name: str | None = None
    strength_attack: int
    strength_defense: int
    class Config:
        from_attributes = True

class TeamFixtureOut(BaseModel):
    gw: int | None = None
    kickoff_time: str | None = None
    finished: int = 0
    is_home: int
    opponent_team_id: int
    opponent_name: str
    opponent_short: str | None = None

class PlayerOut(BaseModel):
    id: int
    name: str
    team_id: int
    team_name: str | None = None
    team_short: str | None = None
    position: Position
    price: float
    status: str
    photo: str | None = None
    class Config:
        from_attributes = True

class PlayerDetailOut(PlayerOut):
    team: Optional[TeamOut] = None

class PlayerHistory(BaseModel):
    gw: int
    minutes: int
    total_points: int = 0
    goals: int = 0
    assists: int = 0
    clean_sheet: int = 0
    goals_conceded: int = 0
    saves: int = 0
    penalties_saved: int = 0
    penalties_missed: int = 0
    own_goals: int = 0
    yellow: int = 0
    red: int = 0
    bonus: int = 0
    bps: int = 0
    xg: float = 0.0
    xa: float = 0.0
    ict_index: float = 0.0
    influence: float = 0.0
    creativity: float = 0.0
    threat: float = 0.0
    started: int = 0

class LeaderRow(BaseModel):
    player_id: int
    name: str
    position: Position
    team_id: int
    team_short: str | None = None
    minutes: int | None = None
    avg_bps: float | None = None
    goals: int = 0
    assists: int = 0
    saves: int = 0
    yellow: int = 0
    red: int = 0
    bonus: int = 0

class LeadersOut(BaseModel):
    top_scorers: list[LeaderRow]
    top_assists: list[LeaderRow]
    most_yellow: list[LeaderRow]
    most_red: list[LeaderRow]
    most_pom: list[LeaderRow]
    best_gk: list[LeaderRow]

class PredictionOut(BaseModel):
    gw: int
    player_id: int
    p_start: float
    expected_points: float
    model_version: str

class PredictResponse(BaseModel):
    gw: int
    model_version: str
    inserted: int

class LineupRequest(BaseModel):
    formation: str = "4-4-2"
    budget: float = 100.0
    max_per_team: int = 3

class LineupPlayer(BaseModel):
    player_id: int
    name: str
    team_id: int
    position: Position
    price: float
    p_start: float
    expected_points: float
    score: float
    photo: str | None = None

class LineupResponse(BaseModel):
    formation: str
    budget: float
    total_expected_points: float
    total_score: float
    players: List[LineupPlayer]

class ActualLineupRequest(BaseModel):
    formation: str = "4-4-2"
    max_per_team: int = 3

class ActualLineupPlayer(BaseModel):
    player_id: int
    name: str
    team_id: int
    position: Position
    price: float = 0.0
    total_points: float = 0.0
    score: float = 0.0
    photo: str | None = None

class ActualLineupResponse(BaseModel):
    gw: int
    formation: str
    total_score: float
    players: List[ActualLineupPlayer]
