import asyncio
from collections.abc import AsyncIterator

import httpx

from app.config import settings
from app.schemas import ApiHistoryPage


class RpsClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.rps_base_url,
            headers={"Authorization": f"Bearer {settings.rps_token}"},
            timeout=httpx.Timeout(connect=10.0, read=None, write=20.0, pool=20.0),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_history_page(self, path: str, max_attempts: int = 5) -> ApiHistoryPage:
        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._client.get(path)
                response.raise_for_status()
                return ApiHistoryPage.model_validate(response.json())
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
