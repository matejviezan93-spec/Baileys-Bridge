# Baileys-Bridge

Symbióza’s Baileys-Bridge links WhatsApp to an AI inference core, Redis message bus, and observability stack. Each service ships as an isolated module under `modules/` and can run on its own or together through Docker Compose.

```
WhatsApp ⇄ baileys-api ⇄ Redis(ai_request/ai_response) ⇄ bridge-ai ⇄ bridge-worker ⇄ WhatsApp
                                   └── bridge-sql (Postgres persistence)
                                   └── bridge-monitoring → Prometheus → Grafana
```

---

## 1. Prerequisites

- Docker and Docker Compose v2
- Node.js 18+ and npm (for local module development)
- Python 3.11+ (for FastAPI and SQL services)
- Redis and Postgres client CLIs (optional diagnostics)

Optional but helpful:
- `qrencode` (pretty-print WhatsApp QR codes) – `sudo apt install qrencode`

---

## 2. Quick Start (Docker Compose)

Run the core loop completely inside Docker:

```bash
cp .env.example .env           # populate GROQ_API_KEY and any overrides
docker compose down -v         # optional: clean previous data
docker compose up --build      # add -d to detach
```

What to expect:
- `baileys_worker` prints a WhatsApp QR code. Scan it from the target WhatsApp account (Linked Devices). Session files persist in the `wa_session` volume.
- Send a WhatsApp message to the linked account. Logs should show:
  - `baileys_worker` receiving the QR and Redis subscriptions
  - `bridge-ai` publishing `{"text": "Hello from AI"}` (or a multi-chain response if configured)
  - `bridge-worker` delivering the reply back to WhatsApp
- Monitoring endpoints once healthy:
  - Prometheus: <http://localhost:9090>
  - Grafana (anonymous viewer): <http://localhost:3000>

Stop the stack:

```bash
docker compose down            # add -v to clear Redis data + WhatsApp session
```

> **Note:** `baileys-api` (WhatsApp ingress) and the Python SQL listener are currently launched manually. See Sections 3 and 4.

---

## 3. Running Individual Services

### 3.1 bridge-ai (FastAPI + Redis listener)

```bash
cd modules/bridge-ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Environment:
- `REDIS_HOST`, `REDIS_PORT`
- Optional multi-chain vars: `GROQ_API_KEY`, `OPENAI_API_KEY`, `CHAIN_CONFIG_PATH`, `COST_CAP_USD`, `HISTORY_MAX_TOK`
- Optional persona overrides: set `PERSONA_DIR` and pass `persona_id` (e.g., WhatsApp JID) in `/multi_chain` requests to pull per-contact prompts.
- Optional conversation history: calls can omit `history` and provide `conversation_id` (defaults to `persona_id`). bridge-ai will load and persist transcripts under `HISTORY_DIR` (defaults to `modules/bridge-ai/app/history/`).

### 3.2 bridge-sql (Redis → Postgres persister)

```bash
cd modules/bridge-sql
python -m venv .venv
source .venv/bin/activate
pip install -r modules/bridge-sql/requirements.txt
psql "$DATABASE_URL" -f init.sql
python -m modules.bridge-sql.main
```

Required environment:
`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, plus either `REDIS_URL` or `REDIS_HOST/REDIS_PORT`.

### 3.3 baileys-api (WhatsApp ingress → Redis publisher)

```bash
cd modules/baileys-api
npm install
cp .env.example .env
npm run start
```

Set `REDIS_HOST`, `REDIS_PORT`, and `WA_SESSION_PATH`. Scan the terminal QR to authorize the WhatsApp session.

### 3.4 bridge-worker (WhatsApp sender)

```bash
cd modules/bridge-worker
npm install
cp .env.example .env
npm run start
```

Ensure `WA_SESSION_PATH` points to the same directory used by `baileys-api` so both services share credentials.

---

## 4. Configuration Reference

- Root `.env` (used by Docker Compose) – copy from `.env.example` and supply:
  - Redis/Postgres connection info
  - `GROQ_API_KEY` if multi-chain is enabled
  - Prompt file overrides (`PROMPT_FILE`, `PERSONA_FILE`, `MEMORY_FILE`)
- Service-specific `.env.example` files live in each module directory.
- `modules/bridge-ai/app/chain_config.json` defines the Analyzer → Imitator → Post-Editor → Masker pipeline. Customize stages, models, pricing, and ordering here or point `CHAIN_CONFIG_PATH` at an alternate file.
- Persona overrides live in `modules/bridge-ai/app/personas/`. Create `<contact_id>.txt` (e.g., WhatsApp JID `12345@c.us` → `12345_c.us.txt`) with persona guidance; set `PERSONA_DIR` to relocate the directory. The text is injected as an extra system prompt for every pipeline stage when `persona_id` matches.
- Conversation history persists as JSONL files under `modules/bridge-ai/app/history/` by default. Override with `HISTORY_DIR` to relocate storage. Each run appends the latest user/assistant turns when `conversation_id` (or `persona_id`) is provided.

Helper scripts:
- `monitor_messages.sh`: colorized Redis pub/sub viewer for `ai_request` and `ai_response`
- `whatsapp-qr.sh`: streams the latest WhatsApp QR code from Docker logs using `qrencode`
- `codex-boost.sh`: spins up docker compose and prepares directories for Codex evolution runs

---

## 5. Testing

### 5.1 Python (bridge-ai multi-chain)

Install dependencies once, then run pytest from the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r modules/bridge-ai/requirements.txt
pytest
```

`tests/test_multi_chain.py` exercises the multi-model pipeline with stubbed LLM clients.

### 5.2 Node services

No automated specs are bundled yet. Recommended baseline:

```bash
cd modules/bridge-worker
npm test   # add your own tests
```

Add unit or integration tests under `__tests__/` and wire them into package scripts.

---

## 6. Service Cheat Sheet

| Module              | Runtime      | Purpose                                             | Entrypoint                                  |
|---------------------|--------------|-----------------------------------------------------|---------------------------------------------|
| `baileys-api`       | Node.js CJS  | Ingest WhatsApp messages, publish to `ai_request`   | `node index.js`                             |
| `bridge-ai`         | FastAPI      | Consume `ai_request`, emit `ai_response`            | `uvicorn app.main:app --host 0.0.0.0`       |
| `bridge-worker`     | Node.js ESM  | Subscribe to `ai_response`, reply over WhatsApp     | `node worker.js` (via `npm run start`)      |
| `bridge-sql`        | Python async | Persist Redis responses to Postgres                 | `python -m modules.bridge-sql.main`         |
| `bridge-monitoring` | Docker assets| Prometheus + Grafana dashboards                     | Built in compose, expose `:9100/:9090/:3000`|
| `bridge-redis`      | Redis Stack  | Message bus + modules (JSON/Search/Bloom/TS)        | `redis-server --appendonly no`              |

---

## 7. Modifying the Project

1. Pick the module you want to change under `modules/`.
2. For Python modules:
   - Work in a virtual environment.
   - Keep to PEP 8, use async redis/pg clients.
3. For Node modules:
   - Use ES modules in `bridge-worker`, CommonJS in `baileys-api`.
   - Log lifecycle events (connect, reconnect, message in/out).
4. Update or add tests in the module.
5. Run module locally or via `docker compose up --build` to verify.
6. Commit using Conventional Commit messages (e.g., `feat(bridge-ai): add tracing`).

---

## 8. Troubleshooting Tips

- **Missing `langchain` or other deps** – install `modules/bridge-ai/requirements.txt` inside your venv before running pytest or the multi-chain API.
- **WhatsApp session expired** – delete the session directory (`wa_session` volume or path set in `.env`) and restart `baileys-api`/`bridge-worker` to rescan the QR.
- **Redis connection refused** – ensure Redis is running (`docker compose ps redis`) and the correct host/port is set.
- **Grafana shows no data** – verify services expose Prometheus metrics and `bridge-monitoring` is running; adjust scrape targets in `prometheus/prometheus.yml` if needed.

Happy bridging! Reach out via Codex agents under `agents/` for automated evolution workflows.
