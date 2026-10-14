import { Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card, EmptyState, ErrorState, Modal, PageTitle, SelectFilter, Skeleton, inputCls, useToast } from "@/components/ui";
import { useAudits, useDeleteAudit } from "@/hooks/queries";
import type { AuditSummary } from "@/types/api";
import { fmtDate } from "@/utils/format";

const PAGE_SIZE = 10;

export default function History() {
  const [page, setPage] = useState(1);
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [mode, setMode] = useState("");
  const [del, setDel] = useState<AuditSummary | null>(null);
  const toast = useToast();
  const opener = useRef<HTMLElement | null>(null);
  useEffect(() => { const t = setTimeout(() => { setQ(qInput); setPage(1); }, 300); return () => clearTimeout(t); }, [qInput]);
  const list = useAudits({ page, page_size: PAGE_SIZE, q: q || undefined, status: status || undefined, mode: mode || undefined });
  const remove = useDeleteAudit();
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / PAGE_SIZE)) : 1;
  const filtered = !!(q || status || mode);

  return (
    <>
      <PageTitle title="Audit history" subtitle="Reopen or delete previous audits." actions={<Link to="/audits/new" className="inline-flex min-h-[40px] items-center rounded-lg bg-brand px-4 text-sm font-medium text-brand-fg">New audit</Link>} />
      <Card>
        <form role="search" aria-label="Search audits" onSubmit={(e) => e.preventDefault()} className="mb-4 grid gap-3 sm:grid-cols-3">
          <div className="space-y-1"><label htmlFor="q" className="block text-xs font-medium text-muted">Search URL or title</label><input id="q" type="search" value={qInput} onChange={(e) => setQInput(e.target.value)} className={inputCls} /></div>
          <SelectFilter id="h-status" label="Status" value={status} onChange={(v) => { setStatus(v); setPage(1); }} options={[{ value: "", label: "All" }, ...["queued", "running", "completed", "failed"].map((s) => ({ value: s, label: s }))]} />
          <SelectFilter id="h-mode" label="Mode" value={mode} onChange={(v) => { setMode(v); setPage(1); }} options={[{ value: "", label: "All" }, ...["conventional", "ai", "combined"].map((s) => ({ value: s, label: s }))]} />
        </form>
        {list.isLoading ? <div role="status" aria-label="Loading audits" className="space-y-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-10" />)}</div>
          : list.isError ? <ErrorState error={list.error} onRetry={() => list.refetch()} />
          : list.data!.items.length === 0 ? <EmptyState title={filtered ? "No audits match your filters" : "No audits yet"} action={!filtered && <Link className="text-brand underline" to="/audits/new">Run your first audit</Link>}>{filtered ? "Try clearing the search or filters." : "Completed audits will be listed here."}</EmptyState>
          : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <caption className="sr-only">Audit history</caption>
                <thead className="text-muted"><tr><th scope="col" className="py-2 pr-4 font-medium">URL</th><th scope="col" className="pr-4 font-medium">Status</th><th scope="col" className="pr-4 font-medium">Mode</th><th scope="col" className="pr-4 font-medium">Findings</th><th scope="col" className="pr-4 font-medium">Date</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead>
                <tbody>{list.data!.items.map((a) => (
                  <tr key={a.id} className="border-t border-line">
                    <td className="max-w-xs truncate py-2 pr-4"><Link className="text-brand underline" to={`/audits/${a.id}`}>{a.url}</Link>{a.demo_mode && <Badge tone="warn" className="ml-2">demo</Badge>}</td>
                    <td className="pr-4"><Badge tone={a.status === "failed" ? "danger" : a.status === "completed" ? "ok" : "warn"}>{a.status}</Badge></td>
                    <td className="pr-4">{a.mode}</td><td className="pr-4">{a.finding_count}</td><td className="pr-4">{fmtDate(a.created_at)}</td>
                    <td><Button variant="ghost" aria-label={`Delete audit of ${a.url}`} onClick={(e) => { opener.current = e.currentTarget; setDel(a); }}><Trash2 className="h-4 w-4" aria-hidden /></Button></td>
                  </tr>))}</tbody>
              </table>
            </div>)}
        {list.data && list.data.total > 0 && (
          <nav aria-label="Pagination" className="mt-4 flex items-center justify-between text-sm">
            <span aria-live="polite">Page {page} of {pages} ({list.data.total} audits)</span>
            <div className="flex gap-2"><Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button><Button variant="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button></div>
          </nav>)}
      </Card>
      {del && (
        <Modal open returnFocus={opener} onOpenChange={(o) => !o && setDel(null)} title="Delete this audit?" description="The audit, its findings and its screenshot will be permanently removed.">
          <p className="mb-4 break-all text-sm">{del.url}</p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDel(null)}>Cancel</Button>
            <Button variant="danger" loading={remove.isPending} onClick={() => remove.mutate(del.id, {
              onSuccess: () => { toast("ok", "Audit deleted."); setDel(null); },
              onError: (e) => { toast("danger", e instanceof Error ? e.message : "Delete failed."); setDel(null); } })}>Delete</Button>
          </div>
        </Modal>)}
    </>
  );
}
