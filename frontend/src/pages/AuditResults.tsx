import { Download, Loader2 } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Alert, Badge, Card, ErrorState, PageTitle, Skeleton } from "@/components/ui";
import { FindingsPanel } from "@/components/Findings";
import { GroundTruthCard } from "@/components/GroundTruthCard";
import { useAudit, useComparison, useFindings } from "@/hooks/queries";
import { ApiError, api } from "@/services/api";
import { fmtDate } from "@/utils/format";

export default function AuditResults() {
  const { id = "" } = useParams();
  const audit = useAudit(id);
  const done = audit.data?.status === "completed" || (audit.data?.status === "failed" && (audit.data?.finding_count ?? 0) > 0);
  const findings = useFindings(id, {}, !!done);
  const cmp = useComparison(id, !!done);
  const [imgFailed, setImgFailed] = useState(false);

  if (audit.isLoading) return <div role="status" aria-label="Loading audit"><Skeleton className="mb-4 h-10 w-2/3" /><Skeleton className="h-64" /></div>;
  if (audit.isError) {
    const nf = audit.error instanceof ApiError && audit.error.status === 404;
    return <><PageTitle title={nf ? "Audit not found" : "Audit"} />{nf ? <ErrorState error={new Error("This audit does not exist or was deleted.")} /> : <ErrorState error={audit.error} onRetry={() => audit.refetch()} />}<Link className="mt-4 inline-block text-brand underline" to="/audits">Back to history</Link></>;
  }
  const a = audit.data!;
  const active = a.status === "queued" || a.status === "running";
  return (
    <>
      <PageTitle title="Audit results" subtitle={a.page_title ?? a.url}
        actions={a.status === "completed" && (
          <div className="flex flex-wrap gap-2" role="group" aria-label="Export report">
            {(["json", "csv", "pdf"] as const).map((f) => (
              <a key={f} href={api.reportUrl(a.id, f)} download className="inline-flex min-h-[40px] items-center gap-1.5 rounded-lg border border-line bg-surface px-3 text-sm font-medium hover:bg-subtle"><Download className="h-4 w-4" aria-hidden />{f.toUpperCase()}</a>
            ))}
          </div>)} />
      <dl className="mb-4 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div><dt className="text-muted">URL</dt><dd className="break-all">{a.final_url ?? a.url}</dd></div>
        <div><dt className="text-muted">Audited</dt><dd>{fmtDate(a.completed_at ?? a.created_at)}</dd></div>
        <div><dt className="text-muted">Mode</dt><dd>{a.mode}</dd></div>
        <div><dt className="text-muted">Status</dt><dd><Badge tone={a.status === "failed" ? "danger" : a.status === "completed" ? "ok" : "warn"}>{a.status}</Badge></dd></div>
      </dl>

      {active && (
        <div role="status" className="mb-4 flex items-center gap-3 rounded-xl border border-line bg-surface p-4">
          <Loader2 className="h-5 w-5 animate-spin text-brand" aria-hidden />
          <div><p className="font-medium">Audit in progress{a.status === "queued" ? " (queued)" : ""}</p><p className="text-sm text-muted">{a.stage ?? "Waiting to start"}. This page updates automatically.</p></div>
        </div>)}
      {a.status === "failed" && <div className="mb-4"><Alert tone="danger" title="Audit failed">{a.error ?? "The audit could not be completed."} <Link className="underline" to="/audits/new">Start a new audit</Link></Alert></div>}
      {a.demo_mode && <div className="mb-4"><Alert tone="warn" title="Demo mode">AI findings in this audit come from a mock provider ({a.ai_model}) that applies simple rules to the real DOM. They illustrate the pipeline and are not evidence of what a real model would find.</Alert></div>}
      {a.ai_error && a.status === "completed" && <div className="mb-4"><Alert tone="warn" title="AI analysis unavailable">{a.ai_error} Conventional results are still shown.</Alert></div>}
      {a.ai_rejected_count > 0 && <div className="mb-4"><Alert tone="info">{a.ai_rejected_count} AI finding(s) were discarded because they failed schema or evidence validation.</Alert></div>}

      {done && (
        <div className="grid gap-6 xl:grid-cols-[22rem_1fr]">
          <div className="space-y-4">
            <Card>
              <h2 className="mb-2 font-semibold">Screenshot</h2>
              {a.has_screenshot && !imgFailed ? (
                <div className="max-h-[32rem] overflow-auto rounded-md border border-line">
                  <img src={api.screenshotUrl(a.id)} onError={() => setImgFailed(true)} alt={`Screenshot of ${a.final_url ?? a.url} captured when the audit ran`} width={a.screenshot_width ?? undefined} className="w-full" />
                </div>
              ) : <p className="text-sm text-muted">{a.capture_screenshot ? "The screenshot could not be loaded." : "Screenshot capture was disabled for this audit."}</p>}
              {a.screenshot_height && a.screenshot_height >= 8000 && <p className="mt-2 text-xs text-muted">Tall pages are cropped to 8000px.</p>}
            </Card>
            <Card>
              <h2 className="mb-2 font-semibold">Tools</h2>
              <dl className="space-y-1 text-sm">
                {Object.entries(a.tool_versions ?? {}).filter(([k]) => k !== "notes").map(([k, v]) => <div key={k} className="flex justify-between gap-2"><dt className="text-muted">{k.replace(/_/g, " ")}</dt><dd className="break-all text-right">{String(v)}</dd></div>)}
                {a.prompt_version && <div className="flex justify-between gap-2"><dt className="text-muted">prompt</dt><dd>{a.prompt_version}</dd></div>}
              </dl>
            </Card>
          </div>
          <div className="min-w-0 space-y-6">
            {cmp.data && <Comparison cmp={cmp.data} />}
            {cmp.data && <GroundTruthCard gt={cmp.data.ground_truth} demo={cmp.data.demo_mode} />}
            <Card>
              <h2 className="mb-4 font-semibold">Findings</h2>
              {findings.isLoading ? <Skeleton className="h-40" /> : findings.isError ? <ErrorState error={findings.error} onRetry={() => findings.refetch()} /> : <FindingsPanel findings={findings.data!.items} />}
            </Card>
          </div>
        </div>
      )}
    </>
  );
}

function Comparison({ cmp }: { cmp: NonNullable<ReturnType<typeof useComparison>["data"]> }) {
  const c = cmp.counts;
  return (
    <Card>
      <h2 className="mb-1 font-semibold">Detection comparison</h2>
      <p className="mb-3 text-sm text-muted">Findings are grouped by element and category/WCAG criterion. Raw counts do not show which method is better; an AI-only group is a candidate, not a proven defect.</p>
      <dl className="grid grid-cols-3 gap-3 text-center">
        <div className="rounded-lg bg-conv/10 p-3"><dd className="text-2xl font-bold text-conv">{c.conventional_only}</dd><dt className="text-xs">Conventional only</dt></div>
        <div className="rounded-lg bg-brand/10 p-3"><dd className="text-2xl font-bold text-brand">{c.both}</dd><dt className="text-xs">Found by both</dt></div>
        <div className="rounded-lg bg-ai/10 p-3"><dd className="text-2xl font-bold text-ai">{c.ai_only}</dd><dt className="text-xs">AI only</dt></div>
      </dl>
    </Card>
  );
}
