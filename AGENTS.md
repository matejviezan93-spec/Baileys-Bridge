# 🧬 AGENTS.md — Symbióza / Baileys-Bridge Integration Guide (v1.1.1)

## 🌍 System Overview

**Baileys-Bridge** is part of the **Symbióza ecosystem** — a modular AI orchestration stack connecting **WhatsApp (Baileys)** ↔ **Redis** ↔ **FastAPI (bridge-ai)** ↔ **PostgreSQL (bridge-sql)**.  
Each service lives under `modules/` and runs independently inside Docker but communicates through a shared virtual network `bridge_net`.

```
📱 baileys-api      → publishes inbound WhatsApp messages to ai_request  
🤖 bridge-ai        → listens to ai_request, responds via ai_response  
💬 bridge-worker    → sends ai_response back to WhatsApp users  
💾 bridge-sql       → persists messages + responses  
📡 bridge-redis     → message bus (RedisJSON, Search, Bloom, TS)  
📊 bridge-monitoring→ Prometheus + Grafana dashboards  
🧩 bridge-core-infra→ Terraform, CI/CD, and Docker scaffolding  
```

Automation and agent coordination live under `agents/`, where **Codex agents** receive specs, implement code, test, and commit updates through evolutionary pull requests.

---

## 🧱 Repository & Module Layout

All operational code resides in `modules/`.  
Each service is a self-contained microservice with its own Dockerfile, environment template, and build context.

```
modules/
├── baileys-api       # WhatsApp ingress → Redis publisher (Node.js)
├── bridge-ai         # FastAPI responder (Python)
├── bridge-worker     # Redis subscriber → WhatsApp sender (Node.js)
├── bridge-sql        # PostgreSQL persistence (Python asyncpg)
├── bridge-redis      # Redis stack w/ modules enabled
├── bridge-monitoring # Prometheus + Grafana
├── bridge-core-infra # Shared infra, CI, and Terraform
└── agents/           # Codex automation configs
```

Shared patterns, CI templates, and environment examples live under `core/` or `agents/codex/`.

---

## ⚙️ Build, Test & Development

### 🧠 Python Services (`bridge-ai`, `bridge-sql`)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # bridge-ai
python -m modules.bridge-sql.main
```
Both services depend on the `REDIS_*` and `PG*` variables (copy `.env.example`).

### 💬 Node Services (`baileys-api`, `bridge-worker`)
```bash
npm install
npm run start
```
Both use Node 18+ and connect automatically to Redis + WhatsApp (Baileys).  
`baileys-api` listens for messages and publishes to `ai_request`.  
`bridge-worker` subscribes to `ai_response` and relays messages back to WhatsApp.

### 🐳 Full System Loop
Run the complete stack from the root repository:
```bash
docker compose down -v
docker compose up --build
```
Expected log chain:
```
WhatsApp → Redis(ai_request) → FastAPI(ai_response) → Redis → WhatsApp
AI → WhatsApp: Hello from AI sent to <jid>
```

---

## 🧩 Coding Style & Conventions

**Python:**  
- Follow PEP 8, 4-space indent, type hints for all public methods.  
- Use `asyncio` for all Redis/SQL I/O.  
- Centralize configuration at module top; log with `logging` module.

**Node.js:**  
- Two-space indent, `const`/`let`.  
- `bridge-worker` uses ES Modules (`"type": "module"`).  
- `baileys-api` may use CommonJS or ES Modules; both must explicitly import Baileys correctly.  
- Always log lifecycle events: connection, message in/out, reconnects.

**Env / Redis naming:**  
Upper-case snake case, e.g. `REDIS_HOST`, `AI_REQUEST`, `AI_RESPONSE`.

---

## 🧪 Testing Guidelines

- Python tests → `<module>/tests/test_*.py` (run via `pytest`).  
- Node tests → `<module>/__tests__/*.spec.js` (run via `node --test`, `jest`, or `vitest`).  
- Include Redis/PG fakes or mocks for unit tests.  
- End-to-end tests execute only under Docker integration pipelines.  
- Each module’s CI must pass before the composed environment runs.

---

## 🧠 Codex Agent Workflow

Codex agents operate evolutionarily:
1. **Spec** → Expanze defines module intent & constraints.  
2. **Implement** → Codex writes code, tests locally.  
3. **Commit** → Conventional Commit message (`feat:`, `fix:`, etc.).  
4. **Push / PR** → GitHub Actions in `.github/workflows/auto_pr.yml` triggers review + merge.

Submodules must remain isolated — each module can evolve independently and is pinned by commit hash.

---

## 🧾 Commit & PR Guidelines

Follow Conventional Commits:
```
feat(bridge-ai): add Redis reconnect loop  
fix(baileys-worker): correct makeWASocket import  
chore: sync all submodules to latest main
```

Each PR should:
- Describe functional intent & scope.  
- Include test or run logs.  
- Note environment variable changes or migrations.  
- For WhatsApp modules: attach anonymized screenshots or logs verifying round-trip.  
- Maintain `vX.Y.Z` tagging consistency across modules and root repo.

---

## 🧩 Release Rhythm

- **v1.0.0 – MVP Stable Loop** (Redis ↔ AI ↔ Worker)  
- **v1.1.1 – WhatsApp Integration** (Baileys API & Worker)  
- **v1.2.0 – Cognitive Loop** (Monitoring + Observability)  

Each release = artifact + test + commit + tag.  
Functionality > perfection — release early, measure, iterate.

---
