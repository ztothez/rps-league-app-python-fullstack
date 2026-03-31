import asyncio
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.clients.rps_client import RpsClient
from app.db import get_db
from app.models import Match
from app.services.leaderboard_service import get_leaderboard
from app.services.sync_service import sync_history
from app.utils import helsinki_day_utc_range, parse_iso_day, sanitize_player_filter

router = APIRouter(prefix="/api")

def _match_to_dict(row: Match) -> dict:
    return {
        "game_id": row.game_id,
        "player_a": row.player_a,
        "player_b": row.player_b,
        "throw_a": row.throw_a,
        "throw_b": row.throw_b,
        "winner": row.winner,
        "played_at": row.played_at.isoformat(),
    }


@router.get("/matches/latest")
def latest_matches(take: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db)):
    rows = db.scalars(select(Match).order_by(Match.played_at.desc()).limit(take)).all()
    return {"data": [_match_to_dict(row) for row in rows], "total_matches": len(rows)}


@router.get("/matches/history")
def match_history(
    player: str | None = None,
    date: str | None = None,
    startDate: str | None = None,
    endDate: str | None = None,
    take: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Match)
    clean_player = sanitize_player_filter(player)
    if clean_player:
        pattern = f"%{clean_player}%"
        stmt = stmt.where(or_(Match.player_a.ilike(pattern), Match.player_b.ilike(pattern)))

    day = parse_iso_day(date)
    start_day = parse_iso_day(startDate)
    end_day = parse_iso_day(endDate)
    if day:
        start, end = helsinki_day_utc_range(day)
        stmt = stmt.where(Match.played_at >= start, Match.played_at < end)
    else:
        if start_day:
            start, _ = helsinki_day_utc_range(start_day)
            stmt = stmt.where(Match.played_at >= start)
        if end_day:
            _, end = helsinki_day_utc_range(end_day)
            stmt = stmt.where(Match.played_at < end)

    rows = db.scalars(stmt.order_by(Match.played_at.desc()).limit(take)).all()
    return {"data": [_match_to_dict(row) for row in rows], "total_matches": len(rows)}


@router.get("/leaderboard/today")
def leaderboard_today(db: Session = Depends(get_db)):
    rows = get_leaderboard(db, day=date.today())
    return {"data": [row.model_dump() for row in rows]}


@router.get("/leaderboard/history")
def leaderboard_history(
    date: str | None = None,
    startDate: str | None = None,
    endDate: str | None = None,
    db: Session = Depends(get_db),
):
    day = parse_iso_day(date)
    start_day = parse_iso_day(startDate)
    end_day = parse_iso_day(endDate)
    rows = get_leaderboard(db, day=day, start_day=start_day, end_day=end_day)
    return {"data": [row.model_dump() for row in rows], "total_players": len(rows)}


@router.post("/matches/sync")
async def sync_matches(pages: int = Query(default=20, ge=1, le=1000), db: Session = Depends(get_db)):
    client = RpsClient()
    try:
        result = await sync_history(db=db, client=client, max_pages=pages, stop_when_no_new=False)
        return {"message": "Sync completed", **result}
    finally:
        await client.close()


@router.get("/live")
async def live_stream():
    keepalive_timeout_seconds = 15

    async def gen():
        try:
            while True:
                client = RpsClient()
                try:
                    async for chunk in client.stream_live():
                        # Pass-through upstream SSE chunks.
                        yield chunk
                finally:
                    await client.close()

                # Upstream ended. Keep client connected and retry shortly.
                yield ": upstream ended, reconnecting\n\n"
                await asyncio.sleep(2)
        finally:
            # Final heartbeat comment so the stream closes cleanly client-side.
            yield ": stream closed\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Keep-Alive": f"timeout={keepalive_timeout_seconds}",
        },
    )
