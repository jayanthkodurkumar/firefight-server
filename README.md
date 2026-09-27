# Firefight

### Problem

When a home battery fails in the field, the alert starts a long manual relay. A coordinator reads the ticket, guesses severity and priority, and works out which team should own it. A technician then digs through raw BMS logs to find what went wrong, runs tests, and updates the ticket. Each handoff costs time, and a lot of that time goes to working out why the ticket fired at all, while a family may be without backup power.

### Who it helps

Field operations engineers and dispatch coordinators at distributed-battery companies like Base, who triage failures across thousands of deployed homes.

### Solution

Firefight turns BMS telemetry into tickets that are already triaged:

- A **rules engine** flags out-of-range signals and opens a ticket with a DTC, severity, and priority.
- An **AI agent** adds root cause analysis. It checks whether a reading is physically real or a sensor fault, separates the cause from its symptoms, and compares the unit with the rest of the fleet to spot repeating patterns, like a single firmware version.
- Engineers can **chat** with the agent about any ticket: “Which signals went out of range?”, “Why was this raised?”, “Is this happening elsewhere?”
- The agent then **recommends the right technician** based on skills, region, on-call status, and current workload.

### Impact

Triage that took several people and handoffs becomes one screen and one conversation. Critical issues, like thermal runaway precursors or homes without backup, reach the right technician first. Fleet-wide patterns show up at the second ticket instead of the thirtieth. On a simulated 40-home fleet, the pipeline caught 29 of 30 planted faults with zero false alarms.

**Tracks:** Most Commercializable (primary), Orchestration.


|                     |                                                                                                                                                                                                             |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Frontend (repo)** | [github.com/jayanthkodurkumar/firefight-BP-client](https://github.com/jayanthkodurkumar/firefight-BP-client)                                                                                                |
| **Frontend (live)** | [firefight-bp-client.vercel.app/login](https://firefight-bp-client.vercel.app/login)                                                                                                                        |
| **Backend (live)**  | [Elastic Beanstalk `/health](http://bp-ai-env.eba-k32w42zi.us-east-2.elasticbeanstalk.com/health)`                                                                                                          |
| **LLM (chat)**      | [OpenAI GPT-4o mini](https://platform.openai.com/docs/models/gpt-4o-mini) (`gpt-4o-mini`) — router, QA agent, and allocation agent via LangChain; override with `CHAT_MODEL` (default `openai:gpt-4o-mini`) |


---

## Prerequisites


| Requirement                          | Notes                                                           |
| ------------------------------------ | --------------------------------------------------------------- |
| **Python 3.12+**                     | Matches `pyproject.toml`                                        |
| **[uv](https://docs.astral.sh/uv/)** | Package manager and virtualenv                                  |
| **PostgreSQL**                       | Connection string in `DATABASE_URL`                             |
| **Docker & Docker Compose**          | Optional; for containerized server + client                     |
| **AWS credentials**                  | For SQS telemetry (local profile or env vars boto3 understands) |
| **OpenAI API key**                   | For chat / allocation agents                                    |


The **web client** is the React app [firefight-BP-client](https://github.com/jayanthkodurkumar/firefight-BP-client). Docker Compose expects a sibling checkout at `../firefight-client` (clone the repo and use that folder name, or adjust `docker-compose.yaml`).

---

## Quick start (local)

### 1. Clone and install dependencies

```bash
git clone <your-repo-url> firefight-server
cd firefight-server
uv sync
```

### 2. Environment file

Copy the example env file and fill in values (see [Environment variables](#environment-variables)):

```bash
cp .env.example .env
```

### 3. Database migrations

```bash
uv run alembic upgrade head
```

### 4. Run the API

```bash
uv run fastapi dev app/main.py
```

Or with Uvicorn directly:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```


| Endpoint     | URL                                                          |
| ------------ | ------------------------------------------------------------ |
| Health       | [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) |
| OpenAPI docs | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)     |


### 5. Optional seed data

```bash
uv run python scripts/seed_bms_sim_fleet.py
uv run python scripts/seed_technicians.py
uv run python scripts/seed_ticket_policy.py
```

---

## Docker Compose

Compose runs the **API** (this repo) and the **Vite client** (sibling `firefight-client`).

### Layout

```
Desktop/
├── firefight-server/    # this repo — docker-compose.yaml lives here
└── firefight-client/    # React app — required for the `client` service
```

### Steps

1. Create `.env` in `firefight-server` (same as local setup).
2. Ensure `firefight-client` is checked out next to this repo.
3. From `firefight-server`:

```bash
docker compose up --build
```


| Service  | Port | Description                                           |
| -------- | ---- | ----------------------------------------------------- |
| `server` | 8000 | FastAPI (`uvicorn app.main:app`)                      |
| `client` | 5173 | Vite dev server; `VITE_API_URL=http://localhost:8000` |


Run migrations against your database **before** or **after** starting the server (from the host, with the same `.env`):

```bash
uv run alembic upgrade head
```

The server image does not run migrations automatically on startup.

---

## Environment variables

Create `.env` from [.env.example](.env.example). Variable names map to [app/core/config/settings.py](app/core/config/settings.py) (Pydantic reads them in uppercase).

### Required


| Variable       | Description                                                                                |
| -------------- | ------------------------------------------------------------------------------------------ |
| `DATABASE_URL` | PostgreSQL URL for SQLAlchemy, e.g. `postgresql+psycopg://USER:PASSWORD@HOST:5432/DB_NAME` |


### Strongly recommended (production)


| Variable         | Description                                                                |
| ---------------- | -------------------------------------------------------------------------- |
| `JWT_SECRET_KEY` | Long random string for signing access tokens. Default in code is dev-only. |
| `OPENAI_API_KEY` | API key for LangChain/LangGraph chat and allocation agents                 |


### AWS / telemetry


| Variable              | Description                                       |
| --------------------- | ------------------------------------------------- |
| `TELEMETRY_QUEUE_URL` | SQS queue URL for BMS telemetry messages          |
| `AWS_REGION`          | AWS region for SQS (default in code: `us-east-2`) |


Configure AWS credentials on your machine or in the deployment environment so boto3 can read from the queue (e.g. `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, or an IAM role).

### Optional (defaults in settings)


| Variable                  | Default                                    | Description                                                           |
| ------------------------- | ------------------------------------------ | --------------------------------------------------------------------- |
| `CORS_ORIGINS`            | Local Vite ports + production frontend URL | Comma-separated allowed origins                                       |
| `CHAT_MODEL`              | `openai:gpt-4o-mini`                       | Model id for `init_chat_model`                                        |
| `JWT_ALGORITHM`           | `HS256`                                    | JWT signing algorithm                                                 |
| `JWT_EXPIRE_MINUTES`      | `1440`                                     | Access token lifetime                                                 |
| `AUTH_EXPOSE_RESET_TOKEN` | `true`                                     | Dev: return password-reset token in JSON; disable when email is wired |
| `SQS_WAIT_TIME_SECONDS`   | `20`                                       | Long-poll wait for telemetry worker                                   |
| `SQS_MAX_MESSAGES`        | `10`                                       | Max messages per SQS receive                                          |


`.env` is loaded via `python-dotenv` and is **not** committed (see `.gitignore`).

---

## Architecture

Diagrams live in `[docs/](docs/)`.

### System overview

![System overview](docs/system-overview.png)

BMS telemetry flows through SQS into PostgreSQL; the FastAPI server exposes tickets, technicians, auth, and orchestrated multi-agent chat. The React client calls the API.

### AI multi-agent flow

Orchestrated routing: one message is classified, then either the **QA** or **allocation** specialist runs (not both in parallel).

![Multi-agent chat flow](docs/multi-agent-flow.png)

### Deployment

![Deployment](docs/deployment.png)

---

## Tech stack

### Server (this repository)


| Layer      | Technology                                                                                                                                                                                   |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Runtime    | Python 3.12                                                                                                                                                                                  |
| API        | [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/)                                                                                                                |
| Data       | [SQLAlchemy 2](https://www.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/), PostgreSQL ([psycopg](https://www.psycopg.org/))                                                    |
| Config     | [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/), `python-dotenv`                                                                                           |
| Auth       | JWT ([python-jose](https://github.com/mpdavis/python-jose)), [bcrypt](https://github.com/pyca/bcrypt/)                                                                                       |
| Messaging  | [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) (AWS SQS)                                                                                                        |
| AI / chat  | [LangGraph](https://langchain-ai.github.io/langgraph/), [LangChain](https://www.langchain.com/), **GPT-4o mini** (`[init_chat_model](https://python.langchain.com/docs/integrations/chat/)`) |
| Tooling    | [uv](https://docs.astral.sh/uv/) (deps & lockfile)                                                                                                                                           |
| Containers | Docker, Docker Compose                                                                                                                                                                       |


### Client ([firefight-BP-client](https://github.com/jayanthkodurkumar/firefight-BP-client))


| Layer      | Technology                               |
| ---------- | ---------------------------------------- |
| UI         | [React](https://react.dev/)              |
| Components | [Mantine](https://mantine.dev/)          |
| State      | [Zustand](https://zustand.docs.pmnd.rs/) |
| Build      | Vite (typical for Mantine + React)       |


---

## BMS telemetry (local dev)

**Schema:** [bms_json_logs/telemetry_record.schema.json](bms_json_logs/telemetry_record.schema.json)  
**Rules:** [rules.yaml](rules.yaml) — loaded into `ticket_policy` for ticket evaluation.

1. Set `TELEMETRY_QUEUE_URL` (and AWS) in `.env`.
2. **Terminal 1 — consumer:**

```bash
uv run python worker/bms_telemetry_consumer.py
```

1. **Terminal 2 — simulator:**

```bash
uv run python scripts/publish_bms_telemetry_sim.py
```

Keep the worker running while publishing; otherwise messages accumulate in SQS only.

SQS payload: JSON envelope `{"format":"bms_telemetry_record","record":{…}}` → `bms_telemetry_records` / `bms_metric_snapshots`, then policy evaluation → `tickets`.

```bash
uv run alembic upgrade head
uv run python scripts/seed_ticket_policy.py
```

Re-seeding policy clears existing tickets and eval state for that policy table.

---

## Migrations (Alembic)

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "describe_change"
```

Config: [alembic.ini](alembic.ini), [alembic/env.py](alembic/env.py) (uses `DATABASE_URL` from `.env`).

---

## Project layout (high level)

```
app/
├── main.py              # FastAPI app, CORS, routers
├── core/                # config, DB session, shared models
└── features/            # auth, tickets, technicians, chat
alembic/                 # database migrations
worker/                  # SQS telemetry consumer
scripts/                 # seeds and BMS simulator publisher
```

---

