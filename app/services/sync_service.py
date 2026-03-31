from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clients.rps_client import RpsClient
from app.models import Match, SyncState
from app.utils import winner_for

SYNC_KEY = "history_backfill_cursor"


def _upsert_cursor(db: Session, cursor: str | None) -> None:
    state = db.scalar(select(SyncState).where(SyncState.key == SYNC_KEY))
    if state is None:
        state = SyncState(key=SYNC_KEY, cursor=cursor)
        db.add(state)
    else:
        state.cursor = cursor
    db.commit()


def _store_page(db: Session, raw_matches: list[dict]) -> int:
    inserted = 0
    for m in raw_matches:
        played_at = datetime.fromtimestamp(m["time"] / 1000, tz=timezone.utc)
        model = Match(
            game_id=m["gameId"],
            player_a=m["playerA"]["name"],
            player_b=m["playerB"]["name"],
            throw_a=m["playerA"]["played"],
            throw_b=m["playerB"]["played"],
            winner=winner_for(m["playerA"]["name"], m["playerA"]["played"], m["playerB"]["name"], m["playerB"]["played"]),
            played_at=played_at,
        )
        db.add(model)
        try:
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()
    return inserted


async def sync_history(db: Session, client: RpsClient, max_pages: int, stop_when_no_new: bool) -> dict:
    state = db.scalar(select(SyncState).where(SyncState.key == SYNC_KEY))
    cursor = state.cursor if state and state.cursor else "/history"

    pages = 0
    inserted_total = 0
    while cursor and pages < max_pages:
        page = await client.get_history_page(cursor)
        inserted = _store_page(db, page["data"])
        inserted_total += inserted
        pages += 1
        cursor = page["cursor"]
        _upsert_cursor(db, cursor)
        if stop_when_no_new and inserted == 0:
            break

    return {"pages_fetched": pages, "inserted_matches": inserted_total, "next_cursor": cursor}
