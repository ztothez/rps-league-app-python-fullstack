import asyncio
import contextlib

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router
from app.clients.rps_client import RpsClient
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.services.sync_service import sync_history

app = FastAPI(title="RPS League API (Python)")
app.include_router(router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

_sync_task: asyncio.Task | None = None


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


async def _sync_loop() -> None:
    while True:
        db = SessionLocal()
        client = RpsClient()
        try:
            await sync_history(
                db=db,
                client=client,
                max_pages=settings.sync_pages_per_run,
                stop_when_no_new=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"background sync error: {exc}")
        finally:
            db.close()
            await client.close()
        await asyncio.sleep(settings.sync_interval_seconds)


@app.on_event("startup")
async def on_startup() -> None:
    global _sync_task
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    client = RpsClient()
    try:
        await sync_history(
            db=db,
            client=client,
            max_pages=settings.initial_sync_pages,
            stop_when_no_new=False,
        )
    finally:
        db.close()
        await client.close()
    _sync_task = asyncio.create_task(_sync_loop())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if _sync_task:
        _sync_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _sync_task
