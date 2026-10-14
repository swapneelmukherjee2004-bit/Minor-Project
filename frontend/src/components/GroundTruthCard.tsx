import { Alert, Card } from "@/components/ui";
import type { GroundTruth } from "@/types/api";
import { fmtMetric } from "@/utils/format";

/** Per-page ground-truth metrics; shows "Not available" rather than inventing numbers. */
export function GroundTruthCard({ gt, demo }: { gt: GroundTruth; demo: boolean }) {
  if (!gt.available || !gt.methods) {
    return <Card><h2 className="mb-1 font-semibold">Ground-truth evaluation</h2><p className="text-sm text-muted">Not available. {gt.reason ?? "No ground-truth annotations exist for this page."} Precision, recall and F1 are only computed for annotated test pages.</p></Card>;
  }
  return (
    <Card>
      <h2 className="mb-1 font-semibold">Ground-truth evaluation: {gt.page_id}</h2>
      <p className="mb-3 text-sm text-muted">This page is an annotated fixture ({gt.condition}) with {gt.n_annotations} labelled issue(s). Single-page numbers are illustrative only.</p>
      {demo && <div className="mb-3"><Alert tone="warn">AI numbers below come from the demo mock provider.</Alert></div>}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Finding-level metrics for this page</caption>
          <thead className="text-muted"><tr>{["Method", "TP", "FP", "FN", "Precision", "Recall", "F1"].map((h) => <th key={h} scope="col" className="py-1 pr-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>{(["conventional", "ai", "combined"] as const).map((m) => { const x = gt.methods![m].finding; return (
            <tr key={m} className="border-t border-line"><th scope="row" className="py-1.5 pr-3 font-medium capitalize">{m}</th><td>{x.tp}</td><td>{x.fp}</td><td>{x.fn}</td><td>{fmtMetric(x.precision)}</td><td>{fmtMetric(x.recall)}</td><td>{fmtMetric(x.f1)}</td></tr>); })}</tbody>
        </table>
      </div>
    </Card>
  );
}
