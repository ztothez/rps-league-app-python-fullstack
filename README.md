# RPS League (Python Version)

[![Smoke Test](https://github.com/ztothez/rps-league-app-python-fullstack/actions/workflows/smoke.yml/badge.svg)](https://github.com/ztothez/rps-league-app-python-fullstack/actions/workflows/smoke.yml)

Python-first implementation of an RPS assignment with a proper backend, persistent storage, robust sync, explicit data validation decisions, and a built-in web dashboard frontend.

## Stack

- FastAPI (REST + SSE proxy endpoint + server-rendered frontend)
- SQLAlchemy + SQLite (persistent local storage)
- httpx (async upstream API client)
- Pydantic (input validation/sanitation)

## Architecture

- `app/clients/rps_client.py`: upstream API integration, retries for `429` + `5xx`, `Retry-After` support.
- `app/services/sync_service.py`: history ingestion, deduplication (`game_id` unique), cursor-based backfill state.
- `app/services/leaderboard_service.py`: in-process aggregation for player stats.
- `app/api/routes.py`: thin API layer for history/leaderboards/latest/live/manual sync.
- `app/templates/index.html` + `app/static/*`: dashboard UI for fans/stakeholders, including a Top 5 wins mini chart.
- `app/main.py`: startup bootstrap sync + continuous background syncing loop.

## Why this addresses common gaps

- **Backend + persistence + frontend**: includes both a real backend and a UI layer, avoiding one-sided implementations.
- **Rate-limit/error handling**: automatic retry with backoff for `429/500/502/503/504`.
- **Validation/sanitation**:
  - strict move enum: `ROCK | PAPER | SCISSORS`
  - timestamp validity guard
  - player query sanitation against wildcard widening (`%`, `_`, `\`)
  - date parsing for `YYYY-MM-DD`
- **Separation of concerns**: routes, services, client, models, and utility modules are isolated.
- **Continuous sync**: startup backfill + periodic fetches.

## API

- `GET /api/matches/latest?take=50`
- `GET /api/matches/history?player=&date=&startDate=&endDate=&take=`
- `GET /api/leaderboard/today`
- `GET /api/leaderboard/history?date=&startDate=&endDate=`
- `POST /api/matches/sync?pages=20`
- `GET /api/live` (SSE stream proxied from upstream)

Frontend route:

- `GET /` (dashboard)

## Date semantics

- A single `date=YYYY-MM-DD` is interpreted with Helsinki-day semantics (UTC+2 boundary), mapped to a UTC range.
- Range filters (`startDate`, `endDate`) follow the same conversion logic.

## Setup

1. Create virtual env and install dependencies:

```bash
cd redo-website/github/RPS-league-app-python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment:

```bash
cp .env.example .env
# set RPS_TOKEN in .env
# set RPS_BASE_URL to your assignment provider endpoint
```

3. Run server:

```bash
uvicorn app.main:app --reload --port 4000
```

4. Open docs:

- `http://localhost:4000/docs`
- `http://localhost:4000/` (dashboard UI)

5. Run smoke tests (optional but recommended before demo/interview):

```bash
./scripts/smoke_test.sh
# or custom base URL:
./scripts/smoke_test.sh http://127.0.0.1:4000
```

## Assumptions and explicit decisions

- Invalid records are rejected during validation and not persisted.
- Duplicate `gameId` records are ignored via DB uniqueness + insert error handling.
- Draws are tracked explicitly (`winner = "DRAW"`).
- Live endpoint is included but treated as best-effort bonus.

## Software development lifecycle practices

- **Design**: clear module boundaries (`clients`, `services`, `api`, `templates/static`) and explicit data contracts.
- **Implementation**: defensive coding for upstream/API failures and empty states in both API and UI.
- **Verification**:
  - Static checks: `python3 -m compileall app`
  - Repeatable smoke checks: `./scripts/smoke_test.sh`
  - CI gate: GitHub Actions workflow at `.github/workflows/smoke.yml` runs smoke checks on push/PR.
  - Manual system checks:
    - `GET /` renders dashboard
    - filter actions update both tables and chart
    - `/api/live` remains connected without aggressive reconnect loops
    - `/docs` and key endpoints return 200
- **Documentation**: assumptions, tradeoffs, and extension ideas are tracked in this README.
- **Operations**: no hardcoded secrets, configurable `.env`, local persistence for deterministic reads.

## If more time was available

- Add automated tests (unit + integration against a mocked upstream API).
- Add structured logging and metrics.
- Add DB migrations and indexes tuned for large historical datasets.
- Add auth for manual sync endpoint in shared deployments.

## AI usage (for interview disclosure)

AI tooling was used to speed up scaffolding and documentation quality. Design decisions, validation rules, and architecture boundaries were reviewed and adjusted manually.
