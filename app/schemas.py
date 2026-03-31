from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


Move = Literal["ROCK", "PAPER", "SCISSORS"]


class ApiPlayerThrow(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    played: Move


class ApiMatch(BaseModel):
    type: Literal["GAME_RESULT"]
    gameId: str = Field(min_length=1, max_length=128)
    time: int
    playerA: ApiPlayerThrow
    playerB: ApiPlayerThrow

    @field_validator("time")
    @classmethod
    def valid_timestamp(cls, value: int) -> int:
        # Reject clearly invalid epoch millis (pre-2026 assignment window guard).
        if value < 1_770_000_000_000:
            raise ValueError("timestamp too old")
        return value


class ApiHistoryPage(BaseModel):
    data: list[ApiMatch]
    cursor: str | None = None


class MatchOut(BaseModel):
    game_id: str
    player_a: str
    player_b: str
    throw_a: str
    throw_b: str
    winner: str
    played_at: datetime


class LeaderboardRow(BaseModel):
    player: str
    wins: int
    losses: int
    draws: int
    games: int
    win_rate: float
