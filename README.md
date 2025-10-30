# Baileys-Bridge

Baileys-Bridge is the Symbióza hybrid orchestrator that coordinates a constellation of independently deployable services. This repository now serves as the control plane and integration hub: it provisions shared infrastructure, describes interoperability contracts, and links to each service module via Git submodules.

## Repository Layout

```
Baileys-Bridge/
├─ core/
│  ├─ infra/           # Terraform for shared DigitalOcean resources
│  ├─ ci/              # Reusable GitHub Actions workflows
│  └─ env/             # Shared environment templates and secrets contracts
├─ contracts/          # OpenAPI schemas, data models, interface specs
├─ modules/            # Independent service modules tracked as submodules
│  ├─ baileys-api/     # FastAPI backend
│  ├─ bridge-sql/      # PostgreSQL + migrations
│  ├─ bridge-worker/   # Node.js async worker
│  ├─ bridge-monitoring/ # Prometheus/Grafana stack
│  └─ bridge-ai/       # AI orchestration and automation
├─ docker-compose.yml  # Local orchestrator composed from module subrepos
└─ README.md
```

Each directory contains a README with additional detail and onboarding context.

## Architecture Layers

| Layer | Purpose |
| --- | --- |
| **Core** (`core/`) | Houses Terraform, shared CI/CD workflows, and common environment configuration.
| **Contracts** (`contracts/`) | Defines API schemas, data models, and cross-module interoperability agreements.
| **Modules** (`modules/`) | Aggregates independently deployable services that evolve on their own cadence.

The orchestrator composes modules through Docker Compose, Terraform-managed infrastructure, and GitHub Actions workflows to keep the swarm in sync.

## Infrastructure & Automation Core

Terraform configuration lives in `core/infra/` and continues to provision the DigitalOcean droplet, firewall, and optional floating IP for the control plane. Cloud-init prepares `/opt/baileys-bridge` with Docker tooling so that the orchestrator can deploy and manage all downstream modules.

The GitHub Actions workflow in `.github/workflows/deploy.yml` runs on pushes to `main` and performs three stages:

1. **Build and Test** – Uses the top-level `docker-compose.yml` to build module containers and execute their tests (`pytest` for the API and `npm test` for the worker).
2. **Terraform** – Executes from `core/infra/` to validate, plan, and apply shared infrastructure changes against DigitalOcean using the `DO_TOKEN` secret.
3. **Deploy** – SSHs into the orchestrator droplet, pulls the latest repository state, refreshes Docker images, and ensures the stack is healthy.

Required GitHub Secrets:

| Secret | Purpose |
| --- | --- |
| `DO_TOKEN` | DigitalOcean API token consumed by Terraform. |
| `SSH_HOST` | Target droplet host or floating IP. |
| `SSH_USER` | SSH username used by the deploy step. |
| `SSH_PRIVATE_KEY` | Private key for authenticating to the droplet. |

### Orchestrate Workflow

`.github/workflows/orchestrate.yml` introduces a matrix job that builds the entire stack and executes module-specific tests for `baileys-api`, `bridge-sql`, `bridge-worker`, and `bridge-monitoring`. Successful runs annotate deployment candidates so Expanze can trigger rollouts with confidence.

## Working with Modules

Each folder under `modules/` is registered as a Git submodule. Clone the repository with submodules to pull their sources:

```sh
git clone --recurse-submodules git@github.com:matejviezan93-spec/baileys-bridge.git
```

Existing clones can be updated with:

```sh
git submodule update --init --recursive
```

### Managing Submodules

Add a new module:

```sh
git submodule add <module_git_url> modules/<module-name>
```

Sync with upstream changes:

```sh
git submodule update --remote --merge
```

Remove a module:

```sh
git submodule deinit -f modules/<module-name>
rm -rf .git/modules/modules/<module-name>
git rm -f modules/<module-name>
```

### Local Orchestration

Local orchestration is available via Docker Compose:

```sh
docker compose --env-file core/env/.env up --build
```

This spins up the API, database, worker, monitoring, and AI components using the shared environment variables defined in `core/env/.env`.

### CI/CD Flow Diagram

```
┌────────────────┐        ┌──────────────────┐        ┌────────────────────┐
│  Git Push / PR │ ─────▶ │  Orchestrate CI │ ─────▶ │  Deploy Workflow   │
└────────────────┘        │  matrix build   │        │  terraform + ssh   │
                          │  module tests   │        │  production update │
                          └────────┬────────┘        └──────────┬─────────┘
                                   │                            │
                                   ▼                            ▼
                           Codex swarm review          Expanze approval & merge
```

## Codex Swarm Evolution

The `agents/codex` directory documents how Codex runs evolve modules independently. Each Codex iteration:

1. Receives a Spec Prompt from Expanze.
2. Spawns divergent implementation strategies per module.
3. Executes tests and reports results via GitHub PRs.
4. Competes for merge based on CI health, diff footprint, and reproducibility.

The `auto_pr.yml` workflow automates PR evaluation, while `orchestrate.yml` and `deploy.yml` ensure every successful mutation becomes part of the Symbióza organism.
