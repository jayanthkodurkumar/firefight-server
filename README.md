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
uv run alembic upgrade head
uv run python scripts/seed_bms_sim_fleet.py
uv run python scripts/seed_technicians.py
```

## BMS telemetry (simulation → SQS → Postgres)

**Contract** (field names/types): [`bms_json_logs/telemetry_record.schema.json`](bms_json_logs/telemetry_record.schema.json)  
**Example JSONL** under `bms_json_logs/out/examples/` is reference only — runtime data comes from the simulator.

Copy [`.env.example`](.env.example) → `.env` and set `TELEMETRY_QUEUE_URL`.

**Terminal 1 — worker:**

```bash
uv run python worker/bms_telemetry_consumer.py
```

**Terminal 2 — fleet at 1 Hz (every unit, every tick; faults appear on the same stream as normal data):**

```bash
uv run python scripts/publish_bms_telemetry_sim.py
```

Runs until Ctrl+C: **one message every 0.5 s**; every **2 s** one of those messages advances a ticket scenario. Rules run in randomized, balanced rounds across R-THM-02, R-ELE-02, R-COM-02, and R-ELE-01. Multi-sample rules receive exactly their required consecutive samples on dedicated units, so each completed round produces one ticket of every type. Keep the worker running.

**You must run the worker at the same time** or messages only sit in SQS:

```bash
uv run python worker/bms_telemetry_consumer.py
```

SQS body: JSON envelope `{"format":"bms_telemetry_record","record":{…}}` → **`bms_telemetry_records`** + **`bms_metric_snapshots`**. Each new record is evaluated against **`ticket_policy`** (loaded from [`rules.yaml`](rules.yaml)); matching rules create a row in **`tickets`**.

```bash
uv run alembic upgrade head
uv run python scripts/seed_ticket_policy.py
# optional: --rules "/path/to/rules.yaml"
```

Re-seeding policy clears existing tickets and eval state for that table.

### Still to build (after ingest)

- **Alert rules** seed + evaluator in the worker → `incidents` / `incident_events`
- **Coordinator API** — list/detail/PATCH incidents (not raw telemetry inbox)
- **Lambda** — same handler as `worker/bms_telemetry_consumer.py` behind SQS trigger (optional deploy)
