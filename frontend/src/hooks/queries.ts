import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type FindingFilters } from "@/services/api";

export const useSettings = () => useQuery({ queryKey: ["settings"], queryFn: api.settings, staleTime: 60_000 });
export const useDashboard = () => useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
export const useAudits = (p: { page: number; page_size: number; q?: string; status?: string; mode?: string }) =>
  useQuery({ queryKey: ["audits", p], queryFn: () => api.listAudits(p), placeholderData: (prev) => prev });
export const useAudit = (id: string) =>
  useQuery({
    queryKey: ["audit", id], queryFn: () => api.audit(id),
    refetchInterval: (q) => (q.state.data && (q.state.data.status === "queued" || q.state.data.status === "running") ? 1500 : false),
  });
export const useFindings = (id: string, f: FindingFilters, enabled: boolean) =>
  useQuery({ queryKey: ["findings", id, f], queryFn: () => api.findings(id, f), enabled, placeholderData: (p) => p });
export const useComparison = (id: string, enabled: boolean) => useQuery({ queryKey: ["comparison", id], queryFn: () => api.comparison(id), enabled });
export const useEvalSummary = () =>
  useQuery({
    queryKey: ["eval-summary"], queryFn: api.evalSummary,
    refetchInterval: (q) => (q.state.data?.running_run_id ? 2000 : false),
  });
export const useStartEval = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.startEval, onSuccess: () => qc.invalidateQueries({ queryKey: ["eval-summary"] }) });
};
export const useDeleteAudit = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteAudit,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["audits"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); },
  });
};
