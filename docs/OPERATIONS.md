# Operations and deployment

## Private pilot deployment

1. Provision PostgreSQL 17 (or a compatible supported version), a web service, and a worker service from the same image. Give the app its own database/credentials; protect administrator credentials separately.
2. Generate a random `SECRET_KEY` (50+ characters), configure `DATABASE_URL`, `ALLOWED_HOSTS`, and exact HTTPS `CSRF_TRUSTED_ORIGINS`. Set `CONEXUS_ENV=production`; keep `ALLOW_SIGNUP=0`.
3. Require database TLS with `DB_SSLMODE=require` or stricter verification appropriate for your provider. `disable` is for the isolated local/CI database only.
4. Place web behind managed HTTPS ingress. Enable `TRUST_PROXY=1` only if the ingress strips and sets X-Forwarded-Proto and the app cannot be reached around it. The application does not trust X-Forwarded-For for rate limiting. Configure edge IP throttling separately; backend IP limits may group users behind a proxy.
5. Apply migrations as a release job, never independently from every web replica. Build/collect static assets from the same source version. Start Gunicorn and the separately supervised `manage.py worker` process.
6. Create the initial account with `manage.py create_workspace <username>`. Recovery for the closed pilot is `manage.py changepassword <username>` after verifying the user's identity through your established process. Do not expose a public registration form until verified email, recovery, abuse controls, and user policies are in place.
7. Run `manage.py check --deploy --fail-level WARNING` with actual deployment configuration. Smoke-test sign-in, a source collection, tenant isolation, and the full experiment/outcome loop over HTTPS.
8. Back up PostgreSQL, complete a restore drill, and confirm data deletion/export procedures before storing real customer information.

## Source and model configuration

Hacker News uses the fixed public endpoint `https://hn.algolia.com/api/v1/search_by_date`. Coverage is technology-biased and query-dependent; it is not a representative demand survey. Respect the provider's terms and quotas. An inaccessible provider results in a visible failed/retried job, never simulated successful data.

RSS requires an exact HTTPS URL in `RSS_FEEDS`. The operator must approve the host, path, content rights, and network destination. URLs from evidence are never fetched. HTTP redirects are disabled; responses are bounded to 1 MB; XML entities are disabled; at most 20 records are imported. Add an outbound firewall/egress proxy for a hardened public service. Operator-supplied feed/model destinations are trusted deployment configuration, not user permissions.

AI is off unless `LLM_BASE_URL` and `LLM_MODEL` are set. `LLM_API_KEY` remains in server secrets. The provider must support `/chat/completions` and the documented parameters. The configured model receives opportunity fields and up to 20 evidence excerpts of 2,000 characters each. Confirm your provider's data retention and pricing before using real material. The app clearly describes this transfer next to the review button. No model call occurs merely by viewing a page.

AI reviews have a bounded response token limit (1,500), at most one pending review per opportunity, and share the workspace's daily research job allowance. Provider dollar budgets are **not** enforced by Conexus; set a hard spend cap with the provider. Review calls are not automatically retried after an ambiguous timeout or expired lease. Citation IDs are checked for membership, not semantic support. Malformed output fails without creating an assessment.

## Worker behavior

- Source schedules have a minimum interval of one hour and a maximum of 10 monitors per workspace.
- Default allowance: 20 jobs per rolling 24 hours, including collection and AI review.
- Collection retries: at most 3 attempts, with bounded backoff. Jobs are claimed transactionally with a five-minute lease and fencing token. Source writes and job success are committed together.
- Worker crashes are recoverable from persisted jobs. A stale claim cannot commit after another worker takes the lease.
- Pause stops future scheduling; a queued/in-flight collection may still complete. The UI reports job status separately from monitor scheduling.
- `worker --once` is a diagnostic single iteration. Keep at least one supervised worker running for continuous monitoring.

Monitor queue age, failed job count, process restarts, source/provider rate responses, database connections, query latency, web error rate, and HTTP latency. Liveness alone does not prove that the worker is processing jobs. Add your hosting provider's alerting and error reporting before public operation. Logs intentionally avoid provider payloads/secrets.

## Maintenance and recovery

Run `python manage.py clearsessions` daily. Run `python manage.py prune_rate_limits` daily to remove rate buckets last updated more than two days ago, without resetting active limits. Define a privacy retention policy for audit/evidence/job history; v1 does not silently delete it.

Use managed automated backups with point-in-time recovery where possible. Before a schema release, verify a backup and test the migration against a staging clone. Application rollback is safe only while the previous image supports the migrated schema; prefer expand/migrate/contract changes. Do not automatically reverse migrations containing user data.

API/HTML writes are authenticated and throttled, but infrastructure-level DDoS protection, resource limits, distributed observability, and formal disaster recovery are outside this repository's local runtime. The image runs as a non-root user. Review and update pinned dependencies using Dependabot.

## Before claiming scale or opening public signup

Measure representative tenant sizes, query patterns, concurrent sessions, provider throughput, worker backlog, and storage growth. Exercise cross-tenant tests on every API addition. Load-test PostgreSQL locking and queue behavior. Establish backup recovery objectives, alert ownership, accessibility checks, email recovery, deletion/export, and a privacy policy. Capacity in millions of registered accounts is an architecture goal, not a tested release claim.
