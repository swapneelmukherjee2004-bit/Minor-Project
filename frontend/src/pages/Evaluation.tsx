import { COLORS, SimpleBar } from "@/charts/charts";
import { Alert, Badge, Button, Card, EmptyState, ErrorState, PageTitle, Skeleton, useToast } from "@/components/ui";
import { useEvalSummary, useStartEval } from "@/hooks/queries";
import type { EvalResultRow, EvalRun, MethodMetrics } from "@/types/api";
import { fmtDate, fmtMetric } from "@/utils/format";

type M = "conventional" | "ai" | "combined";
const METHODS: M[] = ["conventional", "ai", "combined"];

export default function Evaluation() {
  const q = useEvalSummary();
  const start = useStartEval();
  const toast = useToast();
  if (q.isLoading) return <><PageTitle title="Comparison and evaluation" /><Skeleton className="h-64" /></>;
  if (q.isError) return <><PageTitle title="Comparison and evaluation" /><ErrorState error={q.error} onRetry={() => q.refetch()} /></>;
  const s = q.data!;
  const run = s.latest_run;
  const running = !!s.running_run_id;
  return (
    <>
      <PageTitle title="Comparison and evaluation" subtitle="Do AI findings add value over conventional tools, measured against manually established ground truth?"
        actions={<Button loading={start.isPending || running} disabled={!s.dataset} onClick={() => start.mutate(undefined, { onSuccess: () => toast("info", "Evaluation started. This takes about a minute."), onError: (e) => toast("danger", e instanceof Error ? e.message : "Could not start.") })}>{running ? "Evaluation running…" : run ? "Re-run evaluation" : "Run evaluation"}</Button>} />
      <div className="mb-4"><Alert tone="info" title="Raw finding counts do not show that one method is better">A method that reports more findings may simply be noisier. Compare precision, recall and F1 against ground truth, and note that the dataset is small and synthetic, so results are exploratory and do not generalise to real websites.</Alert></div>
      {!run ? (
        <Card><EmptyState title="Evaluation pending">{s.note ?? "No evaluation has been run."} Ground-truth-dependent metrics (precision, recall, F1, confusion matrix) show “Not available” until a run completes.</EmptyState></Card>
      ) : <Results run={run} />}
      {s.dataset && (
        <Card className="mt-6">
          <h2 className="mb-2 text-lg font-semibold">Evaluation dataset: {s.dataset.name} v{s.dataset.version}</h2>
          <p className="text-sm text-muted">{s.dataset.description}</p>
          <p className="mt-3 text-sm"><strong>{s.dataset.n_pages}</strong> pages, <strong>{s.dataset.n_annotations}</strong> annotated issues. Conditions: {Object.entries(s.dataset.pages_by_condition).map(([k, v]) => `${k.replace("_", " ")} (${v})`).join(", ")}. Issues by category: {Object.entries(s.dataset.annotations_by_category).map(([k, v]) => `${k} (${v})`).join(", ")}.</p>
          <h3 className="mt-4 text-sm font-semibold">Annotation protocol</h3><p className="text-sm text-muted">{s.dataset.annotation_protocol}</p>
          <details className="mt-3"><summary className="cursor-pointer text-sm font-medium">Pages in the dataset</summary>
            <ul className="mt-2 space-y-1 text-sm">{s.dataset.pages.map((p) => <li key={p.page_id}><code>{p.page_id}</code> <Badge>{p.condition.replace("_", " ")}</Badge> {p.n_annotations} annotation(s): <span className="text-muted">{p.description}</span></li>)}</ul></details>
        </Card>)}
      <Card className="mt-6"><h2 className="mb-2 text-lg font-semibold">Methodology</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
          <li><strong>Matching:</strong> a finding matches an annotation if it is on the annotated element (or a descendant) and has the same category.</li>
          <li><strong>Counted predictions:</strong> only confirmed/suspected findings (not “needs manual review”, not info severity), one per element and category.</li>
          <li><strong>TP / FN:</strong> annotations matched / not matched. <strong>FP:</strong> findings matching no annotation (so unlabelled but valid findings count as FP).</li>
          <li><strong>Page-level:</strong> a page is positive if it has any annotation; a method predicts positive if it reports any counted finding.</li>
          <li>Metrics that cannot be computed (for example precision with zero predictions) are shown as “Not available”, never as 0.</li>
        </ul></Card>
    </>
  );
}

function Results({ run }: { run: EvalRun }) {
  const rows = (m: M, scope: "finding" | "page", cat = "all") => run.results.find((r) => r.method === m && r.scope === scope && r.category === cat);
  const cats = Array.from(new Set(run.results.filter((r) => r.category !== "all").map((r) => r.category)));
  const ov = run.details?.overlap;
  return (
    <div className="space-y-6">
      {run.is_demo && <Alert tone="warn" title="Demo run: not a research result">This run used the mock AI provider ({run.ai_model}). It verifies the pipeline and matching logic only. Configure a real multimodal provider and re-run to obtain results about AI performance.</Alert>}
      <Card>
        <h2 className="mb-1 text-lg font-semibold">Finding-level metrics</h2>
        <p className="mb-3 text-xs text-muted">Run {fmtDate(run.created_at)} · {run.ai_provider} / {run.ai_model} · prompt {run.prompt_version} · dataset v{run.dataset.version}</p>
        <MetricTable run={run} get={(m) => rows(m, "finding")} caption="Finding-level metrics by method" />
        <p className="mt-3 text-xs text-muted">Reviewer agreement: {run.reviewer_agreement?.available ? `${run.reviewer_agreement.n_reviewed} annotations double-reviewed, ${Math.round((run.reviewer_agreement.percent_agreement ?? 0) * 100)}% agreement, kappa ${fmtMetric(run.reviewer_agreement.cohen_kappa)}` : "Not available (no second reviewer has labelled the annotations yet)."}</p>
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
        {ov && <Card><h2 className="mb-1 font-semibold">Which method found each labelled issue</h2><p className="mb-3 text-xs text-muted">Annotation-level overlap ({run.details?.n_annotations} annotations).</p>
          <SimpleBar title="Annotation-level detection overlap" data={[{ name: "Conventional only", n: ov.conventional_only }, { name: "Both", n: ov.both }, { name: "AI only", n: ov.ai_only }, { name: "Neither", n: ov.neither }]} series={[{ key: "n", label: "Annotations", color: COLORS.neutral }]} colorByName={{ "Conventional only": COLORS.conv, Both: COLORS.both, "AI only": COLORS.ai, Neither: COLORS.neutral }} /></Card>}
        <Card><h2 className="mb-1 font-semibold">Recall by category</h2><p className="mb-3 text-xs text-muted">Categories with no annotations are omitted.</p>
          <SimpleBar title="Recall by category and method" data={cats.map((c) => ({ name: c, conventional: rows("conventional", "finding", c)?.recall ?? null, ai: rows("ai", "finding", c)?.recall ?? null }))}
            series={[{ key: "conventional", label: "Conventional", color: COLORS.conv }, { key: "ai", label: "AI", color: COLORS.ai }]} /></Card>
      </div>
      <Card>
        <h2 className="mb-1 font-semibold">Category-level performance</h2>
        <div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="sr-only">Per-category precision, recall and F1</caption>
          <thead className="text-muted"><tr><th scope="col" className="py-1 pr-3 font-medium">Category</th>{METHODS.map((m) => <th key={m} scope="col" className="pr-3 font-medium capitalize">{m} P / R / F1</th>)}</tr></thead>
          <tbody>{cats.map((c) => <tr key={c} className="border-t border-line"><th scope="row" className="py-1.5 pr-3 font-medium capitalize">{c}</th>{METHODS.map((m) => { const r = rows(m, "finding", c); return <td key={m} className="pr-3">{r ? `${fmtMetric(r.precision)} / ${fmtMetric(r.recall)} / ${fmtMetric(r.f1)}` : "Not available"}</td>; })}</tr>)}</tbody></table></div>
      </Card>
      <Card>
        <h2 className="mb-1 font-semibold">Page-level confusion matrix</h2>
        <p className="mb-3 text-xs text-muted">Rows: ground truth (page has a labelled issue or not). Columns: method reported any counted finding. Page-level is coarse and lenient: it ignores whether the right element was flagged.</p>
        <div className="grid gap-4 md:grid-cols-3">{METHODS.map((m) => <Confusion key={m} method={m} r={rows(m, "page")} />)}</div>
      </Card>
    </div>
  );
}

function MetricTable({ get, caption }: { run: EvalRun; get: (m: M) => EvalResultRow | undefined; caption: string }) {
  return (
    <div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="sr-only">{caption}</caption>
      <thead className="text-muted"><tr>{["Method", "TP", "FP", "FN", "Precision", "Recall", "F1"].map((h) => <th key={h} scope="col" className="py-1 pr-3 font-medium">{h}</th>)}</tr></thead>
      <tbody>{METHODS.map((m) => { const r = get(m); return r ? (
        <tr key={m} className="border-t border-line"><th scope="row" className="py-1.5 pr-3 font-medium capitalize">{m}</th><td>{r.tp}</td><td>{r.fp}</td><td>{r.fn}</td><td>{fmtMetric(r.precision)}</td><td>{fmtMetric(r.recall)}</td><td>{fmtMetric(r.f1)}</td></tr>) : null; })}</tbody></table></div>
  );
}

function Confusion({ method, r }: { method: M; r?: EvalResultRow }) {
  if (!r) return null;
  const cell = "border border-line p-2 text-center";
  return (
    <table className="w-full text-sm"><caption className="mb-1 text-left font-medium capitalize">{method}</caption>
      <thead><tr><td className={cell}></td><th scope="col" className={cell}>Predicted issue</th><th scope="col" className={cell}>Predicted none</th></tr></thead>
      <tbody><tr><th scope="row" className={cell}>Has issue</th><td className={cell}>{r.tp} TP</td><td className={cell}>{r.fn} FN</td></tr>
        <tr><th scope="row" className={cell}>No issue</th><td className={cell}>{r.fp} FP</td><td className={cell}>{r.tn ?? 0} TN</td></tr></tbody></table>
  );
}

export type { MethodMetrics };
