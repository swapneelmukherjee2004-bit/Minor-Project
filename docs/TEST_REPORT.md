# Test report

Executed in the development sandbox (Linux, Python 3.13, Node 22, PostgreSQL 16, Chromium 141 via Playwright 1.49 with `BROWSER_EXECUTABLE_PATH`).

| Suite | Command | Result |
|---|---|---|
| Backend (unit + API + integration, real PostgreSQL + real Chromium + axe-core 4.10.2 + mock AI) | `cd backend && python -m pytest` | **94 passed** |
| Frontend (Vitest + Testing Library) | `cd frontend && npm test` | **14 passed** |
| Frontend type-check + production build | `npm run build` | succeeded |
| Alembic | `alembic upgrade head` / `downgrade base` / `upgrade head` | succeeded on PostgreSQL 16 |
| Evaluation CLI | `python run_evaluation.py` | completed (mock AI ⇒ pipeline verification only) |
| Live UI run (Playwright drives the Vite UI against the live API) | scripted | audit lifecycle OK; axe-core on landing, results, dialog, dashboard, evaluation, history, settings in light and dark themes: **0 violations** after fixes; no console errors; no horizontal overflow at 390px |

## Coverage map
Backend: SSRF/URL policy (`test_security`), schemas/errors/pagination/CORS (`test_api`), normalisation & dedup (`test_normalizer`), AI output validation & hardening (`test_ai_validation`), provider retry/failure/redaction (`test_providers`), metrics incl. sklearn cross-check (`test_metrics`), reports & escaping (`test_reports`), full lifecycle, persistence, filters, comparison, exports, AI failure degradation, garbage AI output, restart recovery, browser-level SSRF (sub-request + redirect) (`test_integration`).
Frontend: form validation + keyboard radios, findings filtering, dialog keyboard/focus return, dashboard loading/error/empty/data, evaluation pending + "Not available" + demo banner, history delete confirmation.

## Not executed / not verified
- `docker compose build/up` (no Docker daemon in the sandbox; `docker compose config` validates).
- Windows/PowerShell setup (instructions provided, not run on Windows).
- Any real AI provider (Anthropic/OpenAI-compatible adapters are unit-tested with mocked HTTP only).
- Public-internet audits (sandbox egress is restricted).
- Manual screen-reader/keyboard testing of the UI beyond automated tests.

## Manual test template
| ID | Step | Expected | Result | Date/Tester |
|---|---|---|---|---|
| M1 | Audit a public page in combined mode (real provider) | Completes; findings with evidence | | |
| M2 | Tab through New audit form with keyboard only | All controls reachable, focus visible | | |
| M3 | Screen reader (NVDA/VoiceOver) on results page | Headings, filters, dialog announced | | |
| M4 | docker compose up on Windows | UI at :8080, audit works | | |
