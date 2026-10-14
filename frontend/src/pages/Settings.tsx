import { ExternalLink } from "lucide-react";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Alert, Badge, Card, ErrorState, PageTitle, Skeleton } from "@/components/ui";
import { useSettings } from "@/hooks/queries";

const LINKS = [
  ["WCAG 2.2 (W3C Recommendation)", "https://www.w3.org/TR/WCAG22/"],
  ["How to Meet WCAG (Quick Reference)", "https://www.w3.org/WAI/WCAG22/quickref/"],
  ["WAI: Evaluating web accessibility", "https://www.w3.org/WAI/test-evaluate/"],
  ["axe-core rule descriptions", "https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md"],
];

export default function Settings() {
  const q = useSettings();
  const loc = useLocation();
  useEffect(() => { if (loc.pathname === "/methodology") document.getElementById("methodology")?.scrollIntoView(); }, [loc.pathname, q.data]);
  const s = q.data;
  return (
    <>
      <PageTitle title="Settings and methodology" subtitle="Configuration status (read-only, secrets are never shown), data handling and limitations." />
      <div className="space-y-6">
        <Card>
          <h2 className="mb-3 text-lg font-semibold">Configuration status</h2>
          {q.isLoading ? <Skeleton className="h-32" /> : q.isError ? <ErrorState error={q.error} onRetry={() => q.refetch()} /> : s && (
            <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
              <div><dt className="text-muted">Mode</dt><dd>{s.demo_mode ? <Badge tone="warn">Demo mode (mock AI)</Badge> : <Badge tone="ok">Live AI provider</Badge>}</dd></div>
              <div><dt className="text-muted">AI provider</dt><dd>{s.ai_provider} {s.ai_configured ? <Badge tone="ok">configured</Badge> : <Badge tone="danger">not configured</Badge>}</dd></div>
              <div><dt className="text-muted">Model</dt><dd>{s.ai_model}</dd></div>
              <div><dt className="text-muted">Prompt version</dt><dd>{s.prompt_version}</dd></div>
              <div><dt className="text-muted">WCAG scope</dt><dd>WCAG {s.wcag.version} Level {s.wcag.levels.join(" and ")}</dd></div>
              <div><dt className="text-muted">Bundled test pages</dt><dd>{s.local_fixtures_enabled ? "Enabled" : "Disabled"}</dd></div>
              <div><dt className="text-muted">Navigation timeout</dt><dd>{s.limits.navigation_timeout_ms / 1000}s</dd></div>
              <div><dt className="text-muted">Request budget per page</dt><dd>{s.limits.max_requests_per_page}</dd></div>
              <div><dt className="text-muted">Concurrent audits</dt><dd>{s.limits.max_concurrent_audits}</dd></div>
              <div><dt className="text-muted">Audit rate limit</dt><dd>{s.limits.audit_rate_limit}</dd></div>
            </dl>)}
          {s?.demo_mode && <div className="mt-4"><Alert tone="info">To use a real model, set <code>AI_PROVIDER</code>, <code>AI_MODEL</code> and <code>AI_API_KEY</code> in the backend <code>.env</code> and restart. Keys live only on the server.</Alert></div>}
        </Card>

        <Card><h2 id="methodology" className="mb-3 scroll-mt-20 text-lg font-semibold">How results are generated</h2>
          <ol className="list-decimal space-y-2 pl-5 text-sm">
            <li>The URL is validated (public http/https only; every resolved address, redirect and sub-request is checked against private and reserved ranges).</li>
            <li>A headless Chromium loads the page in an isolated context. A screenshot and a bounded DOM summary (headings, images and alt text, links, buttons, form controls, landmarks, computed styles) are captured.</li>
            <li><strong>Conventional:</strong> axe-core (WCAG 2.2 A/AA tags) plus three labelled heuristics: heading-level skips, generic link text, file-name-like alt text. axe results are <em>confirmed</em> violations; axe “incomplete” items need manual review; heuristics are <em>suspected</em>.</li>
            <li><strong>AI:</strong> the screenshot (top region) and DOM summary go to a vision model with a fixed prompt. Output must be strict JSON. The server drops invalid findings, rejects findings without evidence, removes unknown WCAG references, fills selectors/HTML from its own extraction (never from the model) and never lets the AI mark a finding “confirmed”.</li>
            <li>Findings from both methods are matched by element (selector equal or ancestor) <em>and</em> a shared category or WCAG criterion, then shown as conventional-only, AI-only or both. Originals are always kept.</li>
          </ol></Card>

        <Card><h2 className="mb-3 text-lg font-semibold">Limitations</h2>
          <ul className="list-disc space-y-2 pl-5 text-sm">
            <li>Automated tools cannot detect every accessibility problem. A clean report does not prove WCAG conformance.</li>
            <li>Screenshots cannot verify keyboard behaviour or screen-reader announcements; DOM-only analysis cannot judge every visual or contextual issue.</li>
            <li>AI observations require human verification. Model confidence is an uncalibrated self-assessment, not a probability.</li>
            <li>Only one viewport (1280px) and the initial page state are analysed; interactive states, authenticated pages and multi-step flows are out of scope.</li>
            <li>The evaluation dataset is small and synthetic; results are exploratory and do not generalise.</li>
            <li>This tool is an audit aid, not a certification service, and does not replace an audit by accessibility specialists and users with disabilities.</li>
          </ul></Card>

        <Card><h2 className="mb-3 text-lg font-semibold">Data handling</h2>
          <ul className="list-disc space-y-2 pl-5 text-sm">
            <li>Audit results, extracted DOM context and screenshots are stored on the server you run (PostgreSQL + local disk) until you delete the audit.</li>
            <li>In live mode, the screenshot and extracted page text are sent to the configured AI provider. In demo mode nothing is sent externally.</li>
            <li>There is no user authentication: deploy only on a trusted network or behind your own access control. Report links are unguessable audit IDs, not secrets.</li>
          </ul></Card>

        <Card><h2 className="mb-3 text-lg font-semibold">Official references</h2>
          <ul className="space-y-1 text-sm">{LINKS.map(([t, h]) => <li key={h}><a className="inline-flex items-center gap-1 text-brand underline" href={h} target="_blank" rel="noopener noreferrer">{t}<ExternalLink className="h-3.5 w-3.5" aria-hidden /><span className="sr-only">(opens in new tab)</span></a></li>)}</ul></Card>
      </div>
    </>
  );
}
