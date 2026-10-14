# Viva preparation

1. **What is the research question?** Does multimodal AI detect meaningful accessibility issues that rule-based tools miss, and at what false-positive cost, measured against independent ground truth?
2. **Why not just trust the LLM's confidence?** It is a self-report, uncalibrated, not a probability. We store and label it that way and never use it as a metric.
3. **How do you stop the model inventing selectors/HTML?** It only returns `element_ref`; the server resolves selector and HTML from its own extraction. Unknown refs ⇒ `needs_manual_review`, confidence ≤ 0.3.
4. **Can AI findings be "confirmed"?** No. Only axe-core's deterministic violations are `confirmed`. Anything else is suspected / manual review.
5. **How is ground truth independent?** Defects are injected by the author before running any tool; labels are written in `build_dataset.py`. Limitation: one annotator, so agreement is "Not available" until a second reviewer labels a subset.
6. **Define precision, recall, F1 here.** TP = annotations matched; FN = unmatched; FP = counted findings matching no annotation. P=TP/(TP+FP), R=TP/(TP+FN), F1=2PR/(P+R); undefined values are null, displayed "Not available".
7. **Why can F1 be misleading here?** Unlabeled-but-valid findings count as false positives; tiny synthetic dataset; mock vs real model.
8. **What does the page-level confusion matrix show and why is it weak?** Whether a page was flagged at all; it ignores *where*. Finding-level metrics are primary.
9. **Explain the matching of conventional vs AI findings.** Same element (selector equal/ancestor) and shared category or WCAG criterion; category alone never merges.
10. **How do you prevent SSRF?** Scheme/port/credential rules; DNS resolution with every answer checked; per-request guard in the browser; manual redirect validation; request budget; isolated context. Residual risk: DNS rebinding TOCTOU — mitigate with an egress firewall.
11. **Why did you validate redirects manually?** Our integration test showed Chromium followed a redirect to 127.0.0.1 without re-entering the Playwright route handler; the test failed, so we fetch with `max_redirects=0` and re-check each `Location`.
12. **What about prompt injection from the page?** Page data is framed as untrusted, delimiters are stripped, output is schema-validated, evidence is server-resolved, the model has no tools or secrets to leak; detection of injection phrases is noted in the audit.
13. **What if there are no AI credentials?** Mock provider ("demo mode") produces labelled demo output; conventional audit needs nothing.
14. **Why PostgreSQL and asyncio jobs, not Redis/Celery?** Relational integrity and migrations matter; load is a few concurrent audits; fewer moving parts. The `submit` abstraction allows replacement.
15. **How are audits kept from hanging?** Navigation timeout, bounded networkidle wait, request budget, screenshot height cap, AI timeout + bounded retries, semaphore, restart recovery.
16. **What can't this tool tell you?** Keyboard operability, screen-reader announcements, multi-step flows, anything behind login, full WCAG conformance.
17. **Why axe tags restricted to WCAG A/AA?** To avoid presenting best-practice rules as WCAG failures; custom heuristics are labelled `custom` and *suspected*.
18. **How do you handle the CSV/PDF export of untrusted text?** CSV: leading `= + - @` neutralised; PDF: all text XML-escaped; no server paths included.
19. **How would you extend it scientifically?** Real pages with permission, ≥2 annotators with κ, several models, repeated runs for variance, confidence calibration.
20. **What did your own self-audit find?** axe on our UI found low-contrast badges, invalid `<dl>` structure and a non-focusable scrollable `<pre>`; all fixed, and a dialog focus-return bug found by a keyboard test.
