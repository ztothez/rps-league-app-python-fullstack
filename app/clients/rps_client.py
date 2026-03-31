import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings

VALID_MOVES = {"ROCK", "PAPER", "SCISSORS"}
MIN_TIMESTAMP_MS = 1_767_225_600_000  # 2026-01-01T00:00:00Z


def _normalize_timestamp_ms(raw: Any) -> int | None:
    if isinstance(raw, (int, float)):
        ts = int(raw)
        # Upstream occasionally sends epoch seconds.
        if ts < 100_000_000_000:
            ts *= 1000
        return ts if ts >= MIN_TIMESTAMP_MS else None

    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        if text.isdigit():
            return _normalize_timestamp_ms(int(text))
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ts = int(dt.timestamp() * 1000)
            return ts if ts >= MIN_TIMESTAMP_MS else None
        except ValueError:
            return None

    return None


def _normalize_move(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    move = raw.strip().upper()
    return move if move in VALID_MOVES else None


def _normalize_match(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    if raw.get("type") != "GAME_RESULT":
        return None

    game_id = str(raw.get("gameId", "")).strip()
    if not game_id:
        return None

    player_a = raw.get("playerA")
    player_b = raw.get("playerB")
    if not isinstance(player_a, dict) or not isinstance(player_b, dict):
        return None

    name_a = str(player_a.get("name", "")).strip()
    name_b = str(player_b.get("name", "")).strip()
    if not name_a or not name_b:
        return None

    move_a = _normalize_move(player_a.get("played"))
    move_b = _normalize_move(player_b.get("played"))
    if move_a is None or move_b is None:
        return None

    ts = _normalize_timestamp_ms(raw.get("time"))
    if ts is None:
        return None

    return {
        "type": "GAME_RESULT",
        "gameId": game_id,
        "time": ts,
        "playerA": {"name": name_a, "played": move_a},
        "playerB": {"name": name_b, "played": move_b},
    }


class RpsClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.rps_base_url,
            headers={"Authorization": f"Bearer {settings.rps_token}"},
            timeout=httpx.Timeout(connect=10.0, read=None, write=20.0, pool=20.0),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_history_page(self, path: str, max_attempts: int = 5) -> dict[str, Any]:
        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._client.get(path)
                response.raise_for_status()
                payload = response.json()
                raw_rows = payload.get("data", []) if isinstance(payload, dict) else []
                cleaned_rows = [
                    item for item in (_normalize_match(raw) for raw in raw_rows) if item is not None
                ]
                cursor = payload.get("cursor") if isinstance(payload, dict) else None
                return {"data": cleaned_rows, "cursor": cursor if isinstance(cursor, str) else None}
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in (429, 500, 502, 503, 504) and attempt < max_attempts:
                    retry_after = exc.response.headers.get("retry-after")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else (5.0 if status == 429 else 3.0)
                    await asyncio.sleep(delay)
                    continue
                raise

        raise RuntimeError("unreachable")

    async def stream_live(self) -> AsyncIterator[str]:
        async with self._client.stream("GET", "/live") as response:
            response.raise_for_status()
            async for chunk in response.aiter_text():
                if chunk:
                    yield chunk
