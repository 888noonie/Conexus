# Conexus engineering handover

## Product direction

Build a business brain that turns investigation into a small, real commercial test. Prioritize reachable buyers, paid outcomes, founder capacity, delivery economics, and contrary evidence. Do not replace uncertainty with an arbitrary confidence score or promise guaranteed profitable execution. Do not add personal founder history to this public repository.

## Implemented

Django 5.2 LTS modular monolith; PostgreSQL production / SQLite local; authenticated owner workspaces; operating brief; opportunity dossiers; epistemically labelled evidence; rule-based review; bounded optional AI review; scheduled HN/RSS ingestion; durable jobs; one active experiment and immutable outcomes; audit events; responsive HTML UI; JSON endpoints; migrations; Docker; CI.

All screens use live database records. Optional sample data is visibly fictional. The application works without an AI key; AI provider integration is exercised with mock responses until the operator configures a real endpoint/model. Broad social/news/financial data access is not implied by the existence of source monitors.

## Why this shape

A separate SPA, agent framework, vector database, message broker, microservices, and Kubernetes would enlarge the first operating burden without establishing value. Shared Django forms/services keep API and HTML behavior aligned. PostgreSQL locks/constraints enforce the critical cross-instance rule. Network work stays in the worker.

## Next product milestone

Run a small private pilot through one real opportunity → source evidence → customer test → recorded outcome. Measure research time, missing information, support burden, and whether users take the next commercial step. Do not treat activity counts as commercial success.

Then, in evidence-driven order:

1. Add assisted opportunity discovery from collected signals: candidate clusters with source-linked draft problem/buyer hypotheses, human acceptance, and explicit duplicate detection. Do not auto-create claims of demand.
2. Add an execution plan view that records experiment tasks and progress against the frozen budget/deadline. Integrations that send messages or spend funds need explicit authority boundaries.
3. Improve source breadth where pilot customers need it: licensed Reddit/social/news/financial connectors; credentials, quotas, provenance, and monitoring per adapter. Do not scrape around denied access.
4. Add customer-facing identity/recovery, roles, retention/export/deletion, observability, and published service policies before opening registration.
5. Add infrastructure only after measured limits: pooled PostgreSQL, web/worker replicas, CDN, managed queue, cursor pagination, and archival storage.

## Release status

Consult CI for the exact commit's PostgreSQL tests and image build. Unit tests cover ownership, CSRF, validation, budget checks, uniqueness, snapshots, outcomes, deduplication, quotas, leases, retries, and model-output validation. The browser test exercises the primary HTML journey and mobile overflow. Live model-provider interoperability, licensed data access, public hosting, load capacity, and a backup restore drill require the deployment environment.

## Operating reminders

- Production requires a random SECRET_KEY and DATABASE_URL; do not run DEBUG on the Internet.
- Apply migrations once per deployment, separately from replicas.
- A supervised worker is required for scheduling; source status is not evidence that the worker is healthy.
- SQLite is for local convenience only; use PostgreSQL for concurrent production writes.
- Preserve the one-active-experiment index, workspace scoping, source provenance, and immutable outcomes in future features.
- No user data, .env files, passwords, or provider credentials belong in commits, screenshots, or CI artifacts.
