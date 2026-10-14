# REST API (`/api/v1`)

Interactive docs: `http://127.0.0.1:8000/docs` (OpenAPI at `/openapi.json`).

| Method & path | Purpose | Notes |
|---|---|---|
| `POST /audits` | Start an audit | Body `{url, mode: conventional\|ai\|combined, capture_screenshot}`. **202** with the queued audit; **400** `url_not_allowed`; **422** validation; **429** rate limit / queue full |
| `GET /audits` | History | `page, page_size(≤100), q, status, mode`; evaluation fixtures excluded |
| `GET /audits/{id}` | Detail + status/stage | Poll until `completed`/`failed` |
| `DELETE /audits/{id}` | Delete | 204; 409 while running |
| `GET /audits/{id}/findings` | Findings | filters `severity, category, method (axe\|custom\|ai\|conventional), status, detected_by`; includes `detected_by` |
| `GET /audits/{id}/comparison` | Provenance counts + per-page ground truth | `ground_truth.available=false` unless the URL is an annotated fixture |
| `GET /audits/{id}/screenshot` | PNG | |
| `GET /reports/{id}?format=json\|csv\|pdf` | Export | Completed audits only |
| `GET /dashboard/summary` | Aggregates | Real DB values only |
| `GET /evaluations/summary` | Dataset + latest completed run | `state: pending` when none |
| `POST /evaluations` | Start evaluation of the bundled dataset | 202; 409 if one is running |
| `GET /evaluations`, `GET /evaluations/{id}` | Runs | |
| `GET /settings/status` | Non-secret configuration | |
| `GET /health` | Liveness + DB check | |

Errors always look like `{"error": {"code": "...", "message": "...", "details": null | [{"field","message"}]}}`.

Finding schema (AI and conventional share it): `method (axe|custom|ai)`, `rule_id`, `title`, `description`, `category`, `severity`, `confidence` (AI only, uncalibrated), `status (confirmed|suspected|needs_manual_review)`, `verification_method`, `wcag_criteria[]`, `selector`, `evidence{screenshot_observation,dom_observation,html_excerpt,selector,extra}`, `user_impact`, `recommendation`, `help_url`, `group_id`.
