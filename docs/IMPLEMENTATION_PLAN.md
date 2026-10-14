# Implementation plan

Phases follow the project brief. Status is tracked in `tasks/todo.md`.

1. **Inspection & planning** – environment: Python 3.13, Node 22, PostgreSQL 16, Chromium (Playwright 1.49 driver with an executable-path override). Docker daemon unavailable in the dev sandbox, so container builds are documented but not executed there.
2. **Contracts** – DB schema, REST API, AI output schema (`AIFinding`), matching and metric definitions (`docs/ARCHITECTURE.md`, `evaluation_service.py` docstring).
3. **Backend** – config/security, models + Alembic, browser service, axe + heuristics, AI providers, validation, normaliser, runner, evaluation, reports, API.
4. **Frontend** – seven areas (landing, dashboard, new audit, results, evaluation, history, settings/methodology) wired to the real API.
5. **Integration** – full audit lifecycle with Chromium + PostgreSQL + mock provider (pytest), live UI run with Playwright.
6. **Security/accessibility review** – SSRF tests; axe-core run against the app's own UI in light/dark themes (fixed 3 issue classes found).
7. **Documentation** – academic report, API, viva, results/test templates.

## Risks and mitigations
| Risk | Mitigation |
|---|---|
| Paid AI unavailable | Mock provider; conventional audit needs no credentials |
| SSRF via redirects/sub-requests | Manual redirect validation + guarded routing; tested |
| LLM fabricates evidence | Server-side evidence, strict schema, WCAG whitelist |
| Small synthetic dataset | Labelled exploratory; no generalisation claims |
| Annotator bias (single annotator) | Labels by construction before running tools; second-reviewer field and agreement computation ready |

## Information genuinely needed from the project owner
- An AI API key (optional) to produce real research numbers; until then all AI results are labelled demo.
- A second reviewer for the annotations (inter-annotator agreement).
- Permission/URLs for any real, naturalistic pages you want added to the dataset.
