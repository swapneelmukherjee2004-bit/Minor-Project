# Using Multimodal AI to Evaluate Website Accessibility: A Comparative Study Against Rule-Based Automated Auditing Tools

> Items marked **[TO BE COLLECTED]** require real experimental data that does not yet exist. No result in this document is invented. The bundled demo run uses a mock AI and verifies the pipeline only.

## 1. Abstract
Rule-based accessibility checkers such as axe-core reliably find technical violations (missing alternative text, unlabeled controls, computable contrast failures) but cannot judge whether existing text is *meaningful* in context. This project builds AccessAudit, a full-stack system that audits one rendered page with both axe-core and a multimodal model that receives a screenshot plus a bounded DOM summary, keeps evidence for each finding, separates confirmed technical violations from AI observations, and evaluates both methods against manually established ground truth on a documented fixture dataset. The evaluation is exploratory (16 pages, 18 annotated issues, single annotator); **[TO BE COLLECTED]**: results with a real vision model.

## 2. Problem statement
Automated tools cover only a fraction of WCAG criteria and say nothing about semantic adequacy (e.g. `alt="graphic"` passes a presence check). It is unclear how much a multimodal model adds, at what false-positive cost, and how to present its uncertain output responsibly.

## 3. Motivation
Large-scale surveys of home pages (WebAIM Million) repeatedly find automatically detectable failures on the great majority of sites, so tooling matters; but studies of evaluation tools (Vigo et al., 2013) show the harm of relying solely on automated tests. Multimodal LLMs can read pages visually and semantically, creating an opportunity — and a verification burden.

## 4. Objectives
1. Build an integrated audit pipeline (browser, axe-core, AI, normalisation, storage, reports).
2. Distinguish confirmed violations from AI inferences and never present AI output as verified.
3. Create a reproducible, ground-truth-annotated dataset format and evaluation command.
4. Measure precision/recall/F1 per method and per category; report overlap.
5. Harden the system against SSRF and prompt injection.

## 5. Literature review outline (real sources; verify details before formal citation)
- W3C. *Web Content Accessibility Guidelines (WCAG) 2.2*, W3C Recommendation, 5 Oct 2023. https://www.w3.org/TR/WCAG22/
- Deque Systems. *axe-core* (open-source accessibility engine). https://github.com/dequelabs/axe-core
- WebAIM. *The WebAIM Million* (annual accessibility analysis of top one million home pages). https://webaim.org/projects/million/
- Vigo, M., Brown, J., Conway, V. (2013). Benchmarking web accessibility evaluation tools: measuring the harm of sole reliance on automated tests. *W4A '13*, ACM.
- Brajnik, G., Yesilada, Y., Harper, S. (2011). The expertise effect on web accessibility evaluation methods. *Human–Computer Interaction* 26(3).
- Abou-Zahra, S. (2008). Web accessibility evaluation. In *Web Accessibility: A Foundation for Research*, Springer.
- Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement* 20(1), 37–46.
- Greshake, K. et al. (2023). Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection. arXiv:2302.12173.
- OWASP. *Server-Side Request Forgery Prevention Cheat Sheet*. https://cheatsheetseries.owasp.org/
- W3C WAI. *Evaluating Web Accessibility Overview*. https://www.w3.org/WAI/test-evaluate/
Suggested review themes: automated vs manual evaluation; expert effect; LLM/vision-language models for UI understanding; prompt injection in LLM-integrated apps.

## 6. Existing systems and limitations
axe-core/Lighthouse/WAVE: deterministic, fast, but presence-based; limited contextual judgement; cover a subset of WCAG. Manual audits: thorough but costly. Existing LLM add-ons: typically unlabeled confidence, no evidence discipline, no ground-truth evaluation.

## 7. Proposed system
Combined pipeline: Playwright render → screenshot + DOM extraction → axe-core + heuristics → multimodal model with strict JSON schema → server-side evidence resolution → normalisation/matching → PostgreSQL → dashboard, comparison, exports, evaluation harness.

## 8. System architecture
See `docs/ARCHITECTURE.md` (component, sequence and ER diagrams).

## 9. Technology justification
React/TypeScript/Vite/Tailwind: typed, fast SPA; Radix Dialog for accessible modals; TanStack Query for polling server state; FastAPI+Pydantic: typed contracts and OpenAPI; SQLAlchemy 2 + Alembic + PostgreSQL: relational integrity and migrations; Playwright: modern browser automation with request interception; axe-core: industry-standard rules; scikit-learn: reference metrics (Cohen's kappa, test cross-checks); ReportLab: dependency-light PDF. No Redis/Kafka: asyncio jobs suffice.

## 10. Use cases
UC1 Audit a page (actor: auditor) · UC2 Review findings with evidence and filters · UC3 Compare methods · UC4 Export report · UC5 Reopen/delete history · UC6 Run evaluation on the dataset · UC7 Inspect configuration/limitations. Alternate flows: URL blocked (400), page unreachable (failed with reason), AI unavailable (conventional results kept).

## 11. Database schema
ER diagram in `docs/ARCHITECTURE.md`. Tables: `audits`, `findings`, `eval_datasets`, `eval_cases`, `ground_truth`, `eval_runs`, `eval_results`. Migration: `backend/alembic/versions/0001_initial_schema.py` (tested up/down on PostgreSQL 16).

## 12. API
See `docs/API.md`.

## 13. AI pipeline
Inputs: JPEG of the top ≤1600px (≤1568px long edge); JSON context (≤60 KB) of headings, images (alt, nearby text), links, buttons (visible text vs accessible name), form controls, landmarks, messages, visually-heading-like text, computed styles; WCAG 2.2 A/AA reference list. System prompt `backend/app/prompts/audit_v1.md`. Output validated by `AIFinding`; invalid items rejected individually; evidence mandatory; unknown WCAG dropped; `confirmed` downgraded; selector/HTML from server by `element_ref`. Retries: exponential backoff (bounded) on 429/5xx/timeouts; error text sanitised.

## 14. Algorithms
```
AUDIT(url, mode):
  assert_allowed(url)                                  # syntax, ports, DNS -> all IPs public
  page <- open_isolated_context(url) with ROUTE(req):
        if req is not http(s)/data/blob: abort
        if budget exceeded or websocket/media: abort
        assert_allowed(req.url) else abort
        resp <- fetch(req, max_redirects=0)
        if resp is 3xx: assert_allowed(resolve(Location)) else abort
        fulfill(resp)
  shot <- screenshot(clip height<=8000); ctx <- extract_dom(page)
  if conventional: F += axe(page) + custom_checks(ctx); canonicalise selectors
  if ai: F += validate(provider(prompt, shot', ctx), ctx)
  assign_groups(F); persist(F)

ASSIGN_GROUPS(F):
  conventional findings on same (selector, category) share a group
  for each AI finding a: g <- first conventional c with related(c.sel, a.sel) and
        (c.category == a.category or c.wcag ∩ a.wcag ≠ ∅); a.group <- g or new group

EVALUATE(case): preds <- dedupe(status in {confirmed,suspected}, severity != info) by (selector, category)
  TP <- #annotations matched by >=1 pred;  FN <- #annotations with none;  FP <- #preds matching none
  match(a, p) <=> p.category == a.category and (a.target in segments(p.selector) or html(p) has id=a.target)
  P = TP/(TP+FP); R = TP/(TP+FN); F1 = 2PR/(P+R)      (undefined -> null, shown "Not available")
```

## 15. Dataset construction and annotation
`dataset/build_dataset.py` generates the fixtures and `dataset.json` from one spec. v1.0: 3 accessible baselines, 12 single-defect injected pages, 1 hand-written *naturalistic-style* page (not scraped). Categories: images (5), navigation (3), forms (3), contrast (2), semantics (5). Each annotation records page, element selector, category, issue type, WCAG criterion, rationale, provenance, optional second-reviewer label. Labels are established by construction, before any tool is run. **Limitations:** one annotator; synthetic pages; one defect per page mostly; no real-world pages yet. Adding real pages requires permission or permissive automated-access terms.

## 16. Evaluation methodology and metrics
Finding-level and page-level definitions are in §14 and the Evaluation page. Metrics: TP/FP/FN, precision, recall, F1, per-category, annotation-level overlap (conventional-only / AI-only / both / neither), page-level confusion matrix, reviewer agreement (percent agreement; Cohen's κ when defined). Reproducibility metadata stored per run: provider, model, prompt version, dataset version, WCAG scope, timestamps. Caveats: unlabeled-but-valid findings count as FP; `needs_manual_review` findings are excluded from P/R; tiny sample ⇒ no significance claims.

## 17. Results
Use `docs/RESULTS_TEMPLATE.md`. **[TO BE COLLECTED]** with a real provider. *Pipeline verification only* (mock AI, not a research result): the conventional method matched 13/18 annotations, the mock 8/18, union 17/18, all with 0 unmatched findings on this synthetic set — numbers that mostly reflect that the mock is built from the same defect types as the fixtures.

## 18. Limitations and ethics
Audit aid, not certification; screenshots cannot verify keyboard/screen-reader behaviour; DOM-only cannot judge all visual issues; AI confidence is uncalibrated; dynamic/authenticated flows out of scope; AI providers receive page content (privacy); only audit pages you are allowed to test; rate-limits and robots/ToS should be respected; AI findings must not be used to certify or to blame site owners without verification.

## 19. Future work
Real annotated pages with ≥2 reviewers; multi-viewport and interaction states (keyboard focus, hover); tiling long screenshots; calibrating confidence; comparison of several models; authentication; pinned-IP egress proxy; human-in-the-loop verification workflow that feeds ground truth.

## 20. Conclusion
The system delivers a working, tested, security-conscious pipeline and a transparent evaluation harness. Whether multimodal AI adds value beyond conventional tools remains an empirical question to be answered by running the harness with a real model on a larger, doubly-annotated dataset.

## 21. Installation and user manual
See `README.md`. User flow: New audit → pick mode → watch progress → open a finding → export → Evaluation page → Run evaluation.

## 22. Test cases
See `docs/TEST_REPORT.md` (executed results and template for manual cases).

## 23. Viva questions
See `docs/VIVA.md`.
