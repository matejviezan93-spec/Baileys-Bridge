# Baileys-Bridge Documentation

This page collects operational notes and reference material for contributors, operators, and downstream agents working with the Symbióza Baileys-Bridge stack.

---

## 1. Architecture Overview

```
WhatsApp Device
    │ (Baileys API)
    ▼
baileys-api (Node.js, CommonJS)
    │ publishes ai_request (Redis)
    ▼
Redis  ──► bridge-ai (FastAPI)
    ▲             │ emits ai_response (Redis)
    │             ▼
bridge-worker (Node.js, ES modules)
    │ sends WhatsApp replies
    ▼
WhatsApp Device

Optional branches:
    ► bridge-sql (Redis subscriber → Postgres)
    ► bridge-monitoring → Prometheus → Grafana
```

Each module lives under `modules/<name>` with its own Dockerfile, runtime configuration, and optional CI templates. Docker Compose wires the services together on the `bridge_net` network.

---

## 2. Message Flow Breakdown

1. **Inbound user message** arrives on WhatsApp.
2. `baileys-api` receives the event via Baileys, extracts text, and publishes JSON to the Redis channel `ai_request`.
3. `bridge-ai` listens on `ai_request`. For user-originated messages the payload is added to the per-conversation history and the multi-model chain is executed. The generated response is published to `ai_response`. Outbound messages (`from_me=true`) are only archived to history (no inference run).
4. `bridge-worker` subscribes to `ai_response`, parses the payload, and sends the message back to the user on WhatsApp, persisting session data under `wa_session`.
5. Optional consumers:
   - `bridge-sql` listens to `ai_response` and writes records to Postgres.
   - `bridge-monitoring` exports metrics for Prometheus/Grafana dashboards.

---

## 3. Redis Payload Contract

Messages published on `ai_request` must follow this schema:

| Field           | Type    | Required | Description |
|----------------|---------|----------|-------------|
| `jid`          | string  | yes      | WhatsApp JID (e.g. `12345@c.us`). Used as default `persona_id`/`conversation_id`. |
| `text`         | string  | yes      | Message body or caption. |
| `source`       | string  | yes      | Upstream source identifier (`whatsapp` today). |
| `from_me`      | bool    | no       | `true` if message originated from the linked WhatsApp account (manual outbound message); `false`/missing otherwise. |
| `persona_id`   | string  | no       | Explicit persona override; falls back to `jid`. |
| `conversation_id` | string | no     | Explicit conversation history key; defaults to `persona_id` or `jid`. |
| Additional fields | any | no | Passed through but ignored by default handlers. |

Example payload (user message):

```json
{
  "source": "whatsapp",
  "jid": "12345@c.us",
  "text": "Hey, can you remind me about tomorrow?",
  "conversation_id": "12345@c.us"
}
```

Example payload (manual outbound message, archived only):

```json
{
  "source": "whatsapp",
  "jid": "12345@c.us",
  "text": "Sure, talk tomorrow!",
  "from_me": true
}
```

---

## 4. API Reference (`bridge-ai`)

### `POST /multi_chain`

| Field | Type | Description |
|-------|------|-------------|
| `history` | string (optional) | Raw conversation transcript. If omitted and `conversation_id` is provided, the service loads the transcript from disk. |
| `user_input` | string | Latest user message (required). |
| `settings.target_words` | int | Target length (default 1,000, 250–2,500). |
| `persona_id` | string (optional) | Persona prompt identifier (defaults to JID). |
| `conversation_id` | string (optional) | History file identifier (defaults to `persona_id`). |

Response:

```json
{
  "output": "<final response>",
  "cost_usd": 0.000123,
  "latency_s": 1.42
}
```

deps / environment of interest:
- `GROQ_API_KEY`, `OPENAI_API_KEY`
- `CHAIN_CONFIG_PATH`, `PERSONA_DIR`, `HISTORY_DIR`
- `COST_CAP_USD`, `HISTORY_MAX_TOK`

---

## 5. Storage Layout

| Path | Contents | Notes |
|------|----------|-------|
| `modules/bridge-ai/app/personas/*.txt` | Persona prompt overrides per contact. | Filenames sanitized from `persona_id`/JID (`12345@c.us` → `12345_c.us.txt`). `default.txt` provides a fallback. |
| `modules/bridge-ai/app/history/*.jsonl` | Conversation transcripts (JSON Lines). | Each line stores `{timestamp, role, text}`. Updated on every request when `conversation_id` is provided or inferred. |
| `logs/costs.jsonl` | Multi-chain cost telemetry. | Appended per run. |
| `wa_session/` (Docker volume) | WhatsApp session data (Baileys). | Shared between `baileys-api` and `bridge-worker`. |

Use the `PERSONA_DIR` and `HISTORY_DIR` env vars to relocate persona and history storage (e.g., mount persistent volumes in production).

---

## 6. Operational Checklist

1. **Local Python setup**
   ```bash
   cd modules/bridge-ai
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   Run `pytest` from repo root once dependencies are installed.

2. **Local Node setup**
   ```bash
   cd modules/baileys-api && npm install
   cd modules/bridge-worker && npm install
   ```

3. **Docker Compose loop**
   ```bash
   cp .env.example .env   # fill API keys, etc.
   docker compose up --build
   ```
   Scan the QR printed by `baileys_worker` to link WhatsApp.

4. **WhatsApp session reset**  
   Delete the `wa_session` volume (`docker volume rm baileys-bridge_wa_session`) or the path set in `.env`, then restart compose to trigger a new QR.

5. **persona/history management**
   - Add or update `<contact>.txt` under the persona directory for custom prompts.
   - Inspect conversation files in the history directory for debugging; remove them to reset context.

---

## 7. Troubleshooting Guide

| Symptom | Possible Cause | Remedy |
|---------|----------------|--------|
| No QR shown on first run | `baileys_worker` not ready | Check container logs (`docker compose logs -f baileys_worker`); ensure network access to WhatsApp. |
| AI response ignores persona | Missing persona file or `persona_id` not passed | Verify filename (`12345_c.us.txt`), ensure request payload includes the correct ID. |
| History not updating | `conversation_id` absent or history dir unwritable | Include `conversation_id` in payload, check `HISTORY_DIR` permissions. |
| Missing `langchain` errors during pytest | Dependencies not installed | Activate venv, run `pip install -r modules/bridge-ai/requirements.txt`. |
| Redis connection refused | Redis container down or host mismatch | `docker compose ps redis`, ensure `REDIS_HOST`/`REDIS_PORT` match. |
| Grafana empty | Monitoring services not running | Start `bridge-monitoring`, Prometheus, Grafana via compose; verify metrics exporters in services. |

---

## 8. Release Workflow

1. Ensure working tree is clean (`git status`) and tests pass.
2. Stage changes: `git add ...`.
3. Commit with Conventional Commit message (e.g., `feat(bridge-ai): add persona history`).
4. Tag the release: `git tag vX.Y.Z` (use `-a` for annotated tag if desired).
5. Push branch and tag:  
   ```bash
   git push origin <branch>
   git push origin vX.Y.Z
   ```
6. Draft release notes / PR referencing the tag. Update `CHANGELOG.md` as needed.

---

## 9. At-a-Glance Reference

- **Channels**
  - Ingress: `ai_request`
  - Egress: `ai_response`
- **Key Environment Variables**
  - `REDIS_HOST`, `REDIS_PORT`, `GROQ_API_KEY`, `OPENAI_API_KEY`
  - `CHAIN_CONFIG_PATH`, `PERSONA_DIR`, `HISTORY_DIR`
  - `COST_CAP_USD`, `HISTORY_MAX_TOK`
- **Main Scripts**
  - `monitor_messages.sh`, `whatsapp-qr.sh`, `codex-boost.sh`

Keep this document updated as modules evolve. Contributions and clarifications welcome!
