# Task list (updated after verification, not after code generation)

## Done and verified
- [x] Repo inspection, plan, architecture docs
- [x] DB schema + Alembic migration (up/down on PostgreSQL 16)
- [x] SSRF policy + guarded browser (incl. redirect validation) — tests
- [x] Browser service, DOM extraction, screenshots (real Chromium)
- [x] axe-core integration + 3 labelled heuristics (real findings)
- [x] AI provider adapters (mock / anthropic / openai-compatible), strict validation, server-side evidence
- [x] Normalisation + matching + provenance
- [x] Evaluation engine, dataset (16 pages/18 annotations), CLI, API
- [x] Reports JSON/CSV/PDF
- [x] REST API with rate limiting, consistent errors, pagination
- [x] Frontend: landing, dashboard, new audit, results, evaluation, history, settings/methodology
- [x] Backend tests (94) and frontend tests (14), production build
- [x] Live UI run + self accessibility audit (0 axe violations)
- [x] Academic docs, API doc, viva, results/test templates, README

## Not done / needs the project owner
- [ ] Run `docker compose up --build` on a machine with Docker (not possible in the dev sandbox)
- [ ] Verify Windows/PowerShell instructions on Windows
- [ ] Real AI provider run + record real results in `docs/RESULTS_TEMPLATE.md`
- [ ] Second annotator for reviewer agreement
- [ ] Add real, permitted, naturalistic pages to the dataset
- [ ] Manual keyboard/screen-reader testing of the UI
- [ ] Authentication if deployed beyond a trusted network
