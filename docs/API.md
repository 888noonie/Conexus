# JSON API v1

Base: `/api/v1/`. Same-origin Django session authentication. Sign in through `/login/`; mutations require a valid `csrftoken` cookie and `X-CSRFToken` header. No bearer token is stored in the browser. Requests cannot select a different workspace.

POST bodies must be JSON objects with `Content-Type: application/json`. The HTML forms and API use the same validation and business services. Updates use full-form POST semantics, not PATCH; send all required fields. Money is encoded as decimal strings, timestamps as ISO 8601, and IDs as UUID strings.

| Method | Endpoint | Purpose |
|---|---|---|
| GET / POST | `/workspace/` | Read/update operating brief |
| GET / POST | `/opportunities/` | List/create candidates |
| GET / POST | `/opportunities/{id}/` | Read/update a candidate |
| POST | `/opportunities/{id}/assess/` | Append deterministic evidence checklist |
| GET | `/opportunities/{id}/assessments/` | Read checklist and AI-review history |
| POST | `/opportunities/{id}/review/` | Queue optional AI review (202); requires configured provider |
| POST | `/opportunities/{id}/experiments/` | Start one bounded experiment (201) |
| GET / POST | `/evidence/` | List/add source records or labelled assumptions |
| POST | `/evidence/{id}/link/` | Set workspace-owned opportunity and stance |
| GET | `/experiments/` | Read active tests and immutable outcomes |
| POST | `/experiments/{id}/outcome/` | Record outcome and release active slot |
| GET / POST | `/sources/` | List/create source monitors |
| POST | `/sources/{id}/run/` | Queue one collection (202) |
| POST | `/sources/{id}/toggle/` | Pause/resume scheduled collection |
| GET | `/jobs/` | Read recent research status and bounded error messages |
| GET | `/events/` | Read mutation audit history |

Unversioned `/healthz/` is liveness and `/readyz/` checks database connectivity. They expose no connection details and are exempted from TLS redirects for internal health probes. Restrict internal probes at ingress where appropriate.

## Examples

Create an opportunity:

```json
{
  "title": "Reduce missed handover information",
  "field": "Business operations",
  "problem": "Hypothesis: small service teams lose time recovering missing context.",
  "buyer": "Owner of a small service company",
  "reach": "Ask a professional contact for an introduction",
  "status": "inbox",
  "price": "100.00",
  "variable_cost": "15.00",
  "hours_per_sale": "2.00",
  "hourly_value": "25.00"
}
```

Unspecified optional text fields become blank; optional economics can be omitted. `title`, `field`, `problem`, and `status` are required. This is an illustrative hypothesis, not validated demand.

Add evidence:

```json
{
  "title": "Customer interview notes",
  "body": "Record what was actually said, distinguish interpretation, and omit unnecessary personal data.",
  "source": "Firsthand interview",
  "kind": "observed",
  "stance": "context"
}
```

Optional `opportunity` links to an existing workspace UUID. `url` accepts HTTP(S) links only. `observed_at` defaults to the server time if omitted. Kinds: `observed`, `inferred`, `hypothesis`, `unknown`, `counterfactual`. Stances: `supports`, `challenges`, `context`.

Start an experiment after setting the operating brief:

```json
{
  "hypothesis": "A reachable buyer will pay for a bounded pilot",
  "action": "Offer the pilot to three relevant buyers",
  "success_criteria": "One completed, paid pilot",
  "stop_criteria": "No payment by the deadline",
  "budget": "50.00",
  "deadline": "2027-01-15"
}
```

Choose a real future deadline and a budget within the workspace limit. POST `{}` to checklist, AI review, and source run/toggle endpoints.

An outcome requires all of:

```json
{
  "status": "completed",
  "outcome": "Describe actual results, surprises, and what remains unknown",
  "actual_spend": "0.00",
  "revenue": "0.00",
  "paying_customers": 0
}
```

`status` is `completed` or `stopped`; neither implies that the idea succeeded commercially.

## Pagination and errors

Lists return `{ "count": 0, "next_page": null, "items": [] }` with a fixed page size of 20. Request `?page=2` for the next page. Out-of-range pages return an empty list. Unknown/foreign IDs return 404.

- 400: malformed JSON/page number; 401: unauthenticated; 403: missing/invalid CSRF; 404: unknown or foreign resource.
- 405: unsupported method; 409: database conflict; 415: wrong content type; 422: validation/business rule; 429: rate limit.
- Validation returns `{"errors":["field: explanation"]}`. Other API errors use `{"error":"explanation"}`. Django's CSRF and routing errors may return HTML; clients must check status/content type before parsing JSON.
- API reads/writes share a 120 request/minute account limit. HTML writes are limited to 60/minute. Up to 10 monitors and a configurable rolling-day research allowance (default 20 jobs) bound work.

No destructive business-data deletion or public data export route is exposed in v1. Account deletion, export, correction, and retention processes are deployment responsibilities for the private pilot and must be formalized before public signup.
