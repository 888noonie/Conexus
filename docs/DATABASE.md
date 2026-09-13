# Database schema

The executable schema is `core/models.py`; `core/migrations/0001_initial.py` initializes it. Django owns users, password hashes, database sessions, permissions, and their migrations. Domain IDs are UUIDs; creation times are UTC timestamps.

| Table | Main fields | Relationships / purpose |
|---|---|---|
| Workspace | owner, name, monthly_income_target, experiment_budget, weekly_hours, target_date, focus_fields, constraints | One owner account per workspace; user-supplied operating limits |
| Opportunity | title, field, problem, buyer, reach, workaround, advantage, delivery, status, price, variable_cost, hours_per_sale, hourly_value | Belongs to workspace; status is investigating (`inbox`), parked, or archived |
| Evidence | title, body, url, source, kind, stance, fingerprint, observed_at | Workspace-owned; optional opportunity; source/uncertainty preserved |
| Assessment | method, report JSON, input_snapshot JSON | Belongs to opportunity; append-only through the API/UI; rules-v1 or explicitly labelled AI draft |
| Experiment | hypothesis, action, success_criteria, stop_criteria, budget, deadline, status, snapshot JSON, outcome, actual_spend, revenue, paying_customers, completed_at | Workspace and protected opportunity reference; one active per workspace |
| SourceMonitor | name, adapter, query, feed_url, interval_hours, enabled, next_run_at | Workspace; scheduled HN/RSS collection |
| ResearchJob | kind, status, attempts, available_at, lease_until, claim_token, result JSON, error, finished_at | Workspace; optional monitor/opportunity; persisted asynchronous work |
| AuditEvent | action, entity_id, detail JSON | Workspace; mutation history, without storing passwords or API credentials |
| RateBucket | key, window, count | Hashed rate-limit key; fixed-window, database-coordinated counters |

## Core invariants

- `one_active_experiment`: partial unique index on workspace when status = active. Application transaction locks the workspace before starting a test; the index is the cross-process backstop.
- `unique_workspace_evidence`: unique workspace + fingerprint. Manual notes hash URL + body; connectors hash adapter + original record identity. Connector reruns do not duplicate a source record. This is identity deduplication, not proof of independent sources.
- `one_pending_monitor_job`: at most one queued/running collection per monitor.
- `one_pending_review_job`: at most one queued/running AI review per opportunity.
- Required money inputs use fixed-precision decimal fields and shared form validation, not floating-point values. Blank estimates are null, distinct from zero.
- Evidence links, API resource IDs, jobs, and all lists are restricted to the authenticated workspace. Workspace identity is derived from the session, never trusted from an API payload.
- Starting an experiment requires a buyer, route to buyer, configured hours and budget, non-past deadline, and a budget within the configured limit. A checklist need not be complete: an experiment may deliberately resolve an uncertainty.
- Outcomes must include status, explanation, actual spend, revenue, and paying customers, including explicit zeros. They cannot be overwritten via application routes.
- Opportunity edits are blocked while its experiment is active. Snapshots preserve opportunity fields, the checklist, brief limits, and up to 200 linked evidence records. Later evidence linking does not rewrite history.
- Database administrators can alter rows. The audit trail is operational history, not a cryptographically tamper-proof ledger.

## Index and retention strategy

Opportunity, evidence, experiment, audit, and job access paths include workspace and creation/status indexes. Jobs have a status/available_at index; monitors index next_run_at. Lists return 20 records per page. Count-based pagination is sufficient for this pilot; use cursor pagination once measured deep-page queries warrant it.

There is no automatic deletion of business evidence or outcomes. Operators must define a disclosed retention/export/deletion policy before public launch. Run `clearsessions` regularly and prune old rate-limit buckets under the operations procedure. Avoid retaining entire fetched documents: adapters store bounded excerpts and links.

For larger datasets, compact snapshot repetition into immutable evidence revisions/object storage and partition archival tables after profiling. Do not weaken tenant filtering or database invariants while optimizing.
