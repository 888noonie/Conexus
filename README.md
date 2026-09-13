# Conexus

**From scattered signals to a deliberate next move.**

Conexus is a private business-research workspace: monitor selected sources, preserve evidence and uncertainty, investigate opportunities, run one bounded commercial experiment, and record what actually happened.

![Conexus workspace with fictional browser-test data](docs/images/overview.png)

It is designed to help a founder reach commercial evidence. It does not guarantee income, invent market validation, or autonomously spend money.

## What works in this MVP

- Session-authenticated, isolated workspaces; public registration is disabled by default.
- Operating brief: income target, budget, available hours, focus fields, and constraints. Unknowns stay blank.
- Opportunity dossiers with buyer access, existing alternatives, delivery approach, and contribution estimates that count the founder's time.
- Evidence ledger with sources, timestamps, deduplication, epistemic labels, and supporting/challenging/context stances.
- Repeatable evidence checklist, with no fabricated success percentage.
- One active experiment per workspace, enforced by PostgreSQL; frozen assumptions and criteria; immutable recorded outcomes.
- Scheduled Hacker News search and operator-approved RSS collection through a durable background queue, with quotas, leases, retries, and visible job status.
- Optional bounded AI review using a configured OpenAI-compatible provider. Drafts are labelled, supplied citation IDs are checked, and AI cannot approve an experiment.
- Responsive server-rendered UI and versioned, paginated JSON API.
- Migrations, audit trail, Docker configuration, and PostgreSQL-backed CI with browser tests.

## Start locally (Python 3.12+)

```bash
git clone https://github.com/888noonie/Conexus.git
cd Conexus
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export CONEXUS_ENV=development
python manage.py migrate
python manage.py create_workspace founder
python manage.py runserver
```

Open **http://127.0.0.1:8000** and sign in with the account you just created. The command securely prompts for a password. No default login or hard-coded customer records exist.

In a second terminal, activate the environment and run:

```bash
export CONEXUS_ENV=development
python manage.py worker
```

The worker is required for monitoring and optional AI reviews. `python manage.py worker --once` schedules due monitors and processes one job, useful for diagnostics. It is not a substitute for a supervised process in production.

For optional **fictional** sample opportunities in a fresh development workspace:

```bash
python manage.py seed_demo founder
```

The sample data is explicitly hypothetical, includes no real customer validation, and does not set your financial targets.

## Docker with PostgreSQL

```bash
cp .env.example .env
# Edit .env and replace the example secrets before proceeding.
docker compose up --build -d
docker compose exec web python manage.py create_workspace founder
```

Open http://localhost:8000. Compose runs PostgreSQL, a one-off migration, web, and worker. The local database is not exposed to the host network. This configuration is for a local pilot; follow the operations guide before Internet exposure. Passwords containing URI-reserved characters must be URL-encoded in DATABASE_URL; for the Compose template use a randomly generated hex password.

## First useful loop

1. Set your operating brief; avoid arbitrary invented targets.
2. Capture one opportunity with an identifiable buyer and a route to reach them.
3. Add source records or configure a monitor, then link relevant collected signals.
4. Run the evidence checklist and investigate missing or contrary evidence.
5. Design a small test with a budget, deadline, and explicit success/stop criteria.
6. Record actual spend, revenue, paying customers, and the outcome before starting the next test.

## Architecture and engineering docs

- [System architecture and scaling decisions](docs/ARCHITECTURE.md)
- [Database schema and invariants](docs/DATABASE.md)
- [JSON API and request examples](docs/API.md)
- [UI architecture](docs/UI.md)
- [Production operations and deployment](docs/OPERATIONS.md)
- [Security boundaries and limitations](SECURITY.md)
- [Implementation handover and next milestones](docs/HANDOVER.md)

## Verification

```bash
ruff check .
ruff format --check .
python manage.py makemigrations --check --dry-run
python manage.py test
python -m playwright install chromium
python scripts/browser_smoke.py
```

SQLite tests skip PostgreSQL-specific concurrency checks. CI uses PostgreSQL and runs them. Browser tests start and stop their own local server and delete their temporary account. Use a disposable database for test execution. All retrieval and AI unit tests use fixtures; no paid provider calls are needed.

## Intentional boundaries

This is a production-oriented MVP foundation, not a claim of tested million-user capacity. It does not yet include billing, shared team roles, email verification/recovery, broad social/financial integrations, automated opportunity synthesis, or a self-running venture fleet. Source research is bounded; human review and customer experiments decide what to do next. See the handover for the remaining release gates.
