import { Link } from "react-router-dom";
import { COLORS, SimpleBar } from "@/charts/charts";
import { Alert, Badge, Button, Card, EmptyState, ErrorState, PageTitle, Skeleton, severityTone } from "@/components/ui";
import { useDashboard } from "@/hooks/queries";
import { SEVERITY_ORDER, fmtDate } from "@/utils/format";

const Stat = ({ label, value }: { label: string; value: number }) => (
  <div className="rounded-xl border border-line bg-surface p-5 shadow-card"><dt className="text-sm text-muted">{label}</dt><dd className="mt-1 text-3xl font-bold">{value}</dd></div>
);

export default function Dashboard() {
  const q = useDashboard();
  const action = <Link to="/audits/new" className="inline-flex min-h-[40px] items-center rounded-lg bg-brand px-4 text-sm font-medium text-brand-fg">New audit</Link>;
  if (q.isLoading) return (<><PageTitle title="Dashboard" /><div role="status" aria-label="Loading dashboard" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div></>);
  if (q.isError) return (<><PageTitle title="Dashboard" /><ErrorState error={q.error} onRetry={() => q.refetch()} /></>);
  const d = q.data!;
  if (d.total_audits === 0) return (
    <><PageTitle title="Dashboard" />
      <EmptyState title="No audits yet" action={action}>Run your first audit to see findings, severity breakdowns and the conventional-versus-AI comparison here.</EmptyState></>
  );
  const sev = SEVERITY_ORDER.map((s) => ({ name: s, count: d.by_severity[s] ?? 0 }));
  const prov = [
    { name: "Conventional only", count: d.provenance.conventional_only }, { name: "Found by both", count: d.provenance.both }, { name: "AI only", count: d.provenance.ai_only },
  ];
  return (
    <>
      <PageTitle title="Dashboard" subtitle="Live statistics from your stored audits (evaluation fixtures are excluded)." actions={action} />
      {d.demo_audits > 0 && <div className="mb-4"><Alert tone="warn" title="Demo data present">{d.demo_audits} audit(s) used the mock AI provider, so their AI findings are demonstration output, not model results.</Alert></div>}
      <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Total audits" value={d.total_audits} /><Stat label="Websites analyzed" value={d.websites_analyzed} />
        <Stat label="Completed audits" value={d.completed_audits} /><Stat label="Findings" value={d.total_findings} />
      </dl>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card><h2 className="mb-3 font-semibold">Findings by severity</h2>
          <SimpleBar title="Findings by severity" data={sev} series={[{ key: "count", label: "Findings", color: COLORS.neutral }]} colorByName={COLORS as Record<string, string>} /></Card>
        <Card><h2 className="mb-1 font-semibold">Conventional vs AI detections</h2>
          <p className="mb-3 text-xs text-muted">Matched issue groups by who detected them. An AI-only group is a candidate, not a proven defect.</p>
          <SimpleBar title="Detections by method" data={prov} series={[{ key: "count", label: "Groups", color: COLORS.neutral }]} colorByName={{ "Conventional only": COLORS.conv, "Found by both": COLORS.both, "AI only": COLORS.ai }} /></Card>
      </div>
      <Card className="mt-6">
        <h2 className="mb-3 font-semibold">Recent audits</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-muted"><tr><th className="py-2 pr-4 font-medium">URL</th><th className="pr-4 font-medium">Mode</th><th className="pr-4 font-medium">Status</th><th className="pr-4 font-medium">Findings</th><th className="font-medium">Date</th></tr></thead>
            <tbody>{d.recent_audits.map((a) => (
              <tr key={a.id} className="border-t border-line">
                <td className="max-w-xs truncate py-2 pr-4"><Link className="text-brand underline" to={`/audits/${a.id}`}>{a.url}</Link></td>
                <td className="pr-4">{a.mode}</td>
                <td className="pr-4"><Badge tone={a.status === "failed" ? "danger" : a.status === "completed" ? "ok" : severityTone("low")}>{a.status}</Badge></td>
                <td className="pr-4">{a.finding_count}</td><td>{fmtDate(a.created_at)}</td>
              </tr>))}</tbody>
          </table>
        </div>
        <div className="mt-3"><Link to="/audits"><Button variant="secondary">View all audits</Button></Link></div>
      </Card>
    </>
  );
}
