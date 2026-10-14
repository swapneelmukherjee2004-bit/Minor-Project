# AccessAudit — multimodal AI vs rule-based website accessibility auditing

Minor project: *Using Multimodal AI to Evaluate Website Accessibility: A Comparative Study Against Rule-Based Automated Auditing Tools.*

AccessAudit renders a page in a guarded headless browser, runs **axe-core** (plus three labelled heuristics) and a **multimodal AI** analysis of the screenshot + DOM, stores every finding with its evidence, separates *confirmed* violations from *AI observations*, and evaluates both methods against ground-truth annotations. It is an **audit aid, not a WCAG conformance certification**; AI findings need human verification.

- Frontend: React, TypeScript, Vite, Tailwind, Radix Dialog, Recharts, React Router, TanStack Query, React Hook Form + Zod, Lucide
- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL, Playwright, axe-core 4.10.2, scikit-learn, ReportLab
- AI: provider adapters `mock` (demo, default, no credentials), `anthropic`, `openai_compatible`; keys stay on the backend

Docs: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/API.md`](docs/API.md) · [`docs/ACADEMIC_REPORT.md`](docs/ACADEMIC_REPORT.md) · [`docs/VIVA.md`](docs/VIVA.md) · [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md) · [`docs/RESULTS_TEMPLATE.md`](docs/RESULTS_TEMPLATE.md) · [`tasks/todo.md`](tasks/todo.md)

## Status (honest summary)
Verified in the dev sandbox: backend 94 tests and frontend 14 tests pass; frontend builds; migrations work on PostgreSQL 16; a full audit works end-to-end in the UI with real Chromium and axe-core. **Not verified:** Docker image builds (no Docker daemon there), Windows instructions, any real AI provider. All AI results are demo output until you configure a provider. See `docs/TEST_REPORT.md`.

## Quick start with Docker (Windows PowerShell + Docker Desktop, or Linux/macOS)
```powershell
Copy-Item .env.example .env          # edit POSTGRES_PASSWORD; optionally AI_* settings
docker compose up --build
```
Open http://localhost:8080 (UI) · http://localhost:8000/docs (API docs). Migrations run automatically on backend start. Data persists in the `pgdata` and `screenshots` volumes. Stop: `docker compose down` (add `-v` to delete data).

## Run without Docker
Prerequisites: Python 3.11+, Node 20+, PostgreSQL 14+.
```powershell
# 1. database (psql as an admin user)
#   CREATE USER auditor WITH PASSWORD 'auditor'; CREATE DATABASE auditor OWNER auditor;

# 2. backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env           # set DATABASE_URL if different
alembic upgrade head
uvicorn app.main:app --port 8000

# 3. frontend (second terminal)
cd frontend
npm install
npm run dev                           # http://localhost:5173 (proxies /api to :8000)
```
`LOCAL_FIXTURE_ORIGINS=http://127.0.0.1:8000` (in `.env.example`) lets you audit the bundled test pages at `http://127.0.0.1:8000/fixtures/<page>.html`; those URLs are the only private-network exception, and only under `/fixtures/`.

If Playwright's bundled browser version doesn't match a preinstalled Chromium, set `BROWSER_EXECUTABLE_PATH`.

## Using a real AI model
In `.env`: `AI_PROVIDER=anthropic` (or `openai_compatible` + `AI_BASE_URL`), `AI_MODEL=<vision-capable model id>`, `AI_API_KEY=...`, then restart the backend. The Settings page shows provider status without exposing the key. The screenshot (top region) and extracted page text are sent to the provider; don't audit confidential pages.

## Evaluation
```bash
cd backend && python run_evaluation.py --json out.json     # or the "Run evaluation" button
```
Regenerate the dataset with `python dataset/build_dataset.py`. With the mock provider the numbers verify the pipeline only and are flagged "demo". See the methodology on the Evaluation page and `docs/ACADEMIC_REPORT.md` §14–17.

## Tests
```bash
cd backend && python -m pytest          # needs PostgreSQL database auditor_test and Chromium
cd frontend && npm test && npm run build
```
Create the test DB once: `CREATE DATABASE auditor_test OWNER auditor;` (override with `TEST_DATABASE_URL`).

## Authentication and deployment assumptions
There is deliberately **no login system** (academic prototype). Audit IDs are unguessable UUIDs but not secrets. Run on localhost or behind your own access control (VPN, reverse-proxy auth). Docker compose publishes ports on `127.0.0.1` only. Add a real auth layer (e.g. OIDC at a reverse proxy) before exposing it. For production also add an egress firewall for the backend container (defence in depth against DNS rebinding).

## Official references
[WCAG 2.2](https://www.w3.org/TR/WCAG22/) · [Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/) · [WAI evaluation overview](https://www.w3.org/WAI/test-evaluate/) · [axe-core](https://github.com/dequelabs/axe-core) · axe-core is MPL-2.0 (`backend/app/assets/AXE_LICENSE.txt`).
