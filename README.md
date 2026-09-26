# firefight-server

## Setup (uv)

[uv](https://docs.astral.sh/uv/) is the project package manager (see [FastAPI docs](https://fastapi.tiangolo.com/)).

```bash
uv sync
```

## Run API

```bash
uv run fastapi dev app/main.py
```

Or:

```bash
uv run uvicorn app.main:app --reload
```

Health: http://127.0.0.1:8000/health  
Docs: http://127.0.0.1:8000/docs

## Migrations (Alembic)

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "describe_change"
```

Config: [`alembic.ini`](alembic.ini), [`alembic/env.py`](alembic/env.py) (uses `DATABASE_URL` from `.env`).

## Seed data

```bash
uv run alembic upgrade head   # if tables are not created yet
uv run python scripts/seed_batteries.py
uv run python scripts/seed_batteries.py --count 200 --start 1001
uv run python scripts/seed_technicians.py
uv run python scripts/seed_technicians.py --count 50 --start 1 --seed 42
```

## Telemetry stream (SQS worker)

Copy [`.env.example`](.env.example) → `.env` and set `TELEMETRY_QUEUE_URL`. AWS credentials must be available (`aws configure`, env vars, or IAM role).

**Terminal 1 — consumer:**

```bash
uv run python worker/telemetry_consumer.py
```

**Terminal 2 — simulator (publishes metrics for seeded `BAT-*` rows):**

```bash
uv run python scripts/publish_telemetry_stream.py --count 100 --interval 0.1
```

Message shape matches [`app/features/telemetry/schemas.py`](app/features/telemetry/schemas.py).

### Still to build (after ingest)

- **Alert rules** seed + evaluator in the worker → `incidents` / `incident_events`
- **Coordinator API** — list/detail/PATCH incidents (not raw telemetry inbox)
- **Lambda** — same handler as `worker/telemetry_consumer.py` behind SQS trigger (optional deploy)
