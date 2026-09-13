# Security

This repository is an early, private-pilot application foundation. Do not include passwords, provider keys, personal customer data, or exploit details in public GitHub issues. Report a suspected vulnerability privately to the repository owner through an existing trusted channel; use GitHub private vulnerability reporting if the owner enables it.

## Implemented boundaries

- Django authentication/password hashing, server-side sessions, CSRF middleware, session expiry, and POST-only state changes.
- Workspace ownership derived from the authenticated user for every domain endpoint. Foreign resource IDs return 404.
- Escaped templates, HTTP(S)-only evidence links, local assets only, restrictive CSP, secure cookies/HSTS in production, and frame denial.
- Database-backed request throttling, disabled public signup by default, bounded request bodies, paginated lists, and source/job quotas.
- Exact operator-approved RSS endpoints; no user-controlled generic fetcher. No redirects; response size/time bounds; safe XML parser. Deployment egress controls remain necessary.
- Source material is untrusted model input. The model has no tools or external-action authority; output schema and citation IDs are checked. It cannot author observed evidence, start experiments, contact customers, or spend funds outside a user-requested provider inference call.
- Immutable experiment outcomes through application routes; snapshots; database exclusivity constraint; durable jobs with leases and fencing.
- Runtime secrets are environment-owned. No application credentials or real founder/customer data are committed. Demo records are fictional and development-only.

## Known boundaries before broader release

No MFA/SSO, verified-email onboarding, automated password recovery, multi-user roles, public billing, or self-service export/deletion yet. Operators can recover accounts, export/delete data, and administer PostgreSQL for the closed pilot. Public signup must remain disabled until those processes and policies are ready.

A workspace owner can enter incorrect observations. A language model can produce unsupported conclusions even when its cited IDs exist. Audit records are not cryptographically tamper-proof. Database administrators retain full authority. There is no independent security audit, formal accessibility audit, or million-user load-test result.

Money fields are research records, not payment processing. The experiment budget limits the recorded commitment; it does not control purchases made elsewhere. Provider quotas limit work count/token output, not a guaranteed GBP bill. Configure provider spending controls independently.
