from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("game_id", name="uq_matches_game_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    player_a: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    player_b: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    throw_a: Mapped[str] = mapped_column(String(16), nullable=False)
    throw_b: Mapped[str] = mapped_column(String(16), nullable=False)
    winner: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class SyncState(Base):
    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    cursor: Mapped[str | None] = mapped_column(String(256), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
