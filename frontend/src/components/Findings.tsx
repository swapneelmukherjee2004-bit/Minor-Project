import { ExternalLink } from "lucide-react";
import { useMemo, useRef, useState, type RefObject } from "react";
import { Alert, Badge, EmptyState, Modal, SelectFilter, severityTone } from "@/components/ui";
import type { Finding } from "@/types/api";
import { CATEGORIES, SEVERITY_ORDER, detectedLabel, methodLabel, statusLabel } from "@/utils/format";

const ALL = [{ value: "", label: "All" }];
const opts = (xs: readonly string[]) => [...ALL, ...xs.map((x) => ({ value: x, label: x[0].toUpperCase() + x.slice(1).replace("_", " ") }))];

export function MethodBadge({ method }: { method: Finding["method"] }) {
  return <Badge tone={method === "ai" ? "ai" : "conv"}>{methodLabel(method)}</Badge>;
}

export function FindingsPanel({ findings }: { findings: Finding[] }) {
  const [f, setF] = useState({ severity: "", category: "", method: "", status: "", detected_by: "" });
  const [sel, setSel] = useState<Finding | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  const set = (k: keyof typeof f) => (v: string) => setF((p) => ({ ...p, [k]: v }));
  const shown = useMemo(() => findings.filter((x) =>
    (!f.severity || x.severity === f.severity) && (!f.category || x.category === f.category) && (!f.status || x.status === f.status) &&
    (!f.detected_by || x.detected_by === f.detected_by) &&
    (!f.method || (f.method === "conventional" ? x.method !== "ai" : x.method === "ai"))), [findings, f]);
  return (
    <div>
      <form role="search" aria-label="Filter findings" className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5" onSubmit={(e) => e.preventDefault()}>
        <SelectFilter id="f-method" label="Method" value={f.method} onChange={set("method")} options={[...ALL, { value: "conventional", label: "Conventional (axe + heuristics)" }, { value: "ai", label: "AI" }]} />
        <SelectFilter id="f-severity" label="Severity" value={f.severity} onChange={set("severity")} options={opts(SEVERITY_ORDER)} />
        <SelectFilter id="f-category" label="Category" value={f.category} onChange={set("category")} options={opts(CATEGORIES)} />
        <SelectFilter id="f-status" label="Status" value={f.status} onChange={set("status")} options={opts(["confirmed", "suspected", "needs_manual_review"])} />
        <SelectFilter id="f-detected" label="Detected by" value={f.detected_by} onChange={set("detected_by")} options={[...ALL, { value: "conventional_only", label: "Conventional only" }, { value: "ai_only", label: "AI only" }, { value: "both", label: "Both" }]} />
      </form>
      <p role="status" className="mb-3 text-sm text-muted">Showing {shown.length} of {findings.length} findings</p>
      {shown.length === 0 ? (
        <EmptyState title={findings.length ? "No findings match these filters" : "No findings"}>
          {findings.length ? "Clear a filter to see more." : "No issues were reported by the selected methods. This does not prove the page is accessible: automated tools cannot detect every problem."}
        </EmptyState>
      ) : (
        <ul className="space-y-3">
          {shown.map((x) => (
            <li key={x.id}>
              <button type="button" onClick={(e) => { opener.current = e.currentTarget; setSel(x); }} aria-label={`Open details: ${x.title}`}
                className="w-full rounded-xl border border-line bg-surface p-4 text-left shadow-card hover:border-brand">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={severityTone(x.severity)}>{x.severity}</Badge><MethodBadge method={x.method} />
                  <Badge tone={x.status === "confirmed" ? "ok" : x.status === "suspected" ? "warn" : "neutral"}>{statusLabel(x.status)}</Badge>
                  <Badge>{x.category}</Badge>
                  {x.wcag_criteria.length > 0 && <Badge>WCAG {x.wcag_criteria.join(", ")}</Badge>}
                </div>
                <p className="mt-2 font-medium">{x.title}</p>
                <p className="mt-1 line-clamp-2 text-sm text-muted">{x.description}</p>
                <p className="mt-2 text-xs text-muted">{detectedLabel(x.detected_by)}{x.selector ? ` · ${x.selector}` : ""}</p>
              </button>
            </li>
          ))}
        </ul>
      )}
      {sel && <FindingDetail finding={sel} onClose={() => setSel(null)} returnFocus={opener} />}
    </div>
  );
}

const Row = ({ label, children }: { label: string; children: React.ReactNode }) =>
  children ? <div><dt className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</dt><dd className="mt-1 whitespace-pre-wrap break-words text-sm">{children}</dd></div> : null;

export function FindingDetail({ finding: x, onClose, returnFocus }: { finding: Finding; onClose: () => void; returnFocus?: RefObject<HTMLElement | null> }) {
  const ev = x.evidence ?? {};
  const extra = ev.extra && Object.keys(ev.extra).length ? ev.extra : null;
  return (
    <Modal open returnFocus={returnFocus} onOpenChange={(o) => !o && onClose()} title={x.title} description={`${methodLabel(x.method)} finding, rule ${x.rule_id}`}>
      <div className="mb-4 flex flex-wrap gap-2">
        <Badge tone={severityTone(x.severity)}>{x.severity}</Badge><MethodBadge method={x.method} />
        <Badge tone={x.status === "confirmed" ? "ok" : "warn"}>{statusLabel(x.status)}</Badge><Badge>{x.category}</Badge><Badge>{detectedLabel(x.detected_by)}</Badge>
      </div>
      {x.method === "ai" && (
        <div className="mb-4"><Alert tone="warn" title="AI observation, not a verified defect">It may be a valid contextual finding, a false positive, or a candidate for human review. Confirm it manually before acting.</Alert></div>
      )}
      <dl className="space-y-4">
        <Row label="Description">{x.description}</Row>
        <Row label="Why it matters">{x.user_impact}</Row>
        <Row label="Suggested remediation">{x.recommendation}</Row>
        <Row label="WCAG 2.2 criteria">{x.wcag_criteria.length ? x.wcag_criteria.join(", ") : "No criterion mapped (evidence did not support a specific mapping)."}</Row>
        {x.confidence !== null && <Row label="Model confidence (uncalibrated)">{(x.confidence * 100).toFixed(0)}%. This is the model's self-assessment, not the probability that the issue exists.</Row>}
        <Row label="Verification">{x.verification_method.replace("_", " ")}</Row>
        <Row label="Selector">{ev.selector ? <code className="break-all">{ev.selector}</code> : "Page-level or not resolved to an element."}</Row>
        <Row label="DOM observation">{ev.dom_observation}</Row>
        <Row label="Screenshot observation">{ev.screenshot_observation}</Row>
        <Row label="HTML excerpt">{ev.html_excerpt ? <pre tabIndex={0} aria-label="HTML excerpt" className="overflow-x-auto rounded-md bg-subtle p-3 text-xs"><code>{ev.html_excerpt}</code></pre> : null}</Row>
        {extra && <Row label="Validation notes">{Object.values(extra).map(String).join(" ")}</Row>}
      </dl>
      {x.help_url && <a className="mt-4 inline-flex items-center gap-1 text-sm text-brand underline" href={x.help_url} target="_blank" rel="noopener noreferrer">Rule documentation <ExternalLink className="h-3.5 w-3.5" aria-hidden /><span className="sr-only">(opens in new tab)</span></a>}
    </Modal>
  );
}
