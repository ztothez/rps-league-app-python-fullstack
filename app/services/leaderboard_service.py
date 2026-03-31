from collections import defaultdict
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Match
from app.schemas import LeaderboardRow
from app.utils import helsinki_day_utc_range


def _apply_date_filters(stmt: Select[tuple[Match]], day: date | None, start_day: date | None, end_day: date | None) -> Select[tuple[Match]]:
    if day:
        start, end = helsinki_day_utc_range(day)
        return stmt.where(Match.played_at >= start, Match.played_at < end)
    if start_day:
        start, _ = helsinki_day_utc_range(start_day)
        stmt = stmt.where(Match.played_at >= start)
    if end_day:
        _, end = helsinki_day_utc_range(end_day)
        stmt = stmt.where(Match.played_at < end)
    return stmt


def get_leaderboard(db: Session, day: date | None = None, start_day: date | None = None, end_day: date | None = None) -> list[LeaderboardRow]:
    stmt = _apply_date_filters(select(Match), day, start_day, end_day)
    matches = db.scalars(stmt).all()

    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "games": 0})
    for m in matches:
        stats[m.player_a]["games"] += 1
        stats[m.player_b]["games"] += 1
        if m.winner == "DRAW":
            stats[m.player_a]["draws"] += 1
            stats[m.player_b]["draws"] += 1
        elif m.winner == m.player_a:
            stats[m.player_a]["wins"] += 1
            stats[m.player_b]["losses"] += 1
        elif m.winner == m.player_b:
            stats[m.player_b]["wins"] += 1
            stats[m.player_a]["losses"] += 1

    rows = [
        LeaderboardRow(
            player=player,
            wins=s["wins"],
            losses=s["losses"],
            draws=s["draws"],
            games=s["games"],
            win_rate=round((s["wins"] / s["games"]) * 100, 1) if s["games"] else 0.0,
        )
        for player, s in stats.items()
    ]
    rows.sort(key=lambda r: (-r.win_rate, -r.wins, r.player.lower()))
    return rows
