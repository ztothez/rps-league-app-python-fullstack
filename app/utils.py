from datetime import date, datetime, timedelta, timezone
from re import fullmatch


ISO_DATE_PATTERN = r"\d{4}-\d{2}-\d{2}"


def parse_iso_day(raw: str | None) -> date | None:
    if not raw or not fullmatch(ISO_DATE_PATTERN, raw.strip()):
        return None
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        return None


def helsinki_day_utc_range(day: date) -> tuple[datetime, datetime]:
    # Assignment-specific: treat day boundary as UTC+2 for consistency.
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) - timedelta(hours=2)
    end = start + timedelta(days=1)
    return start, end


def sanitize_player_filter(raw: str | None, max_len: int = 64) -> str:
    if not raw:
        return ""
    return raw.strip().lower().replace("%", "").replace("_", "").replace("\\", "")[:max_len]


def winner_for(player_a: str, throw_a: str, player_b: str, throw_b: str) -> str:
    if throw_a == throw_b:
        return "DRAW"
    a_wins = (
        (throw_a == "ROCK" and throw_b == "SCISSORS")
        or (throw_a == "PAPER" and throw_b == "ROCK")
        or (throw_a == "SCISSORS" and throw_b == "PAPER")
    )
    return player_a if a_wins else player_b
