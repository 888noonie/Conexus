# UI architecture

Conexus uses server-rendered Django templates with a single responsive stylesheet (`static/css/conexus.css`). No third-party JavaScript frameworks or analytics scripts are included.

## Layout

- `templates/base.html` — authenticated navigation, message display, CSP-compliant local assets.
- Sticky header with links to Dashboard, Brief, Opportunities, Evidence, Experiments, Sources, Jobs.
- Login page is a centred card without navigation chrome.

## Responsive behaviour

- CSS grid for dashboard stat cards (`auto-fit, minmax(200px, 1fr)`).
- Navigation wraps on narrow viewports; font sizes reduce below 600px.
- Tables scroll horizontally on mobile to prevent layout overflow.
- Form action buttons stack full-width on mobile.

## Pages

| Route | Template | Purpose |
|---|---|---|
| `/` | `dashboard.html` | Workspace summary and active experiment |
| `/brief/` | `brief.html` | Operating brief form |
| `/opportunities/` | `opportunity_list.html` | Candidate list |
| `/opportunities/<id>/` | `opportunity_detail.html` | Dossier, evidence, assessments, actions |
| `/evidence/` | `evidence_list.html` | Ledger with link action |
| `/experiments/` | `experiment_list.html` | Active and completed tests |
| `/sources/` | `source_list.html` | Monitor list with run/toggle |
| `/jobs/` | `job_list.html` | Research job status |
| `/events/` | `event_list.html` | Audit history |

## Progressive enhancement

All mutations use standard HTML forms with CSRF tokens. The JSON API mirrors the same validation for programmatic clients. No client-side routing or token storage.
