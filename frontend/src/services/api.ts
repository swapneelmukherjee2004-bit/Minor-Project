import type { AuditDetail, AuditMode, AuditSummary, Comparison, DashboardSummary, EvalRun, EvalSummary, Finding, Paged, SettingsStatus } from "@/types/api";

const rawBase = import.meta.env.VITE_API_BASE as string | undefined;
const BASE = import.meta.env.MODE === "test"
  ? "/api/v1"
  : (rawBase && !rawBase.includes("YOUR-RENDER-BACKEND-URL"))
    ? rawBase
    : "https://minor-project-v28q.onrender.com/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: { field: string; message: string }[]) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
  } catch {
    throw new ApiError(0, "network_error", "Cannot reach the AccessAudit backend. Is it running?");
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const e = body?.error;
    throw new ApiError(res.status, e?.code ?? "http_error", e?.message ?? `Request failed (${res.status}).`, e?.details ?? undefined);
  }
  return body as T;
}

export interface FindingFilters { severity?: string; category?: string; method?: string; status?: string; detected_by?: string }
const qs = (o: Record<string, string | number | undefined>) => {
  const p = new URLSearchParams();
  Object.entries(o).forEach(([k, v]) => v !== undefined && v !== "" && p.set(k, String(v)));
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const api = {
  settings: () => request<SettingsStatus>("/settings/status"),
  dashboard: () => request<DashboardSummary>("/dashboard/summary"),
  createAudit: (b: { url: string; mode: AuditMode; capture_screenshot: boolean }) =>
    request<AuditSummary>("/audits", { method: "POST", body: JSON.stringify(b) }),
  listAudits: (p: { page: number; page_size: number; q?: string; status?: string; mode?: string }) =>
    request<Paged<AuditSummary>>(`/audits${qs(p)}`),
  audit: (id: string) => request<AuditDetail>(`/audits/${id}`),
  findings: (id: string, f: FindingFilters) => request<{ items: Finding[]; total: number }>(`/audits/${id}/findings${qs({ ...f })}`),
  comparison: (id: string) => request<Comparison>(`/audits/${id}/comparison`),
  deleteAudit: (id: string) => request<void>(`/audits/${id}`, { method: "DELETE" }),
  evalSummary: () => request<EvalSummary>("/evaluations/summary"),
  evalRun: (id: string) => request<EvalRun>(`/evaluations/${id}`),
  startEval: () => request<{ id: string; status: string }>("/evaluations", { method: "POST", body: "{}" }),
  screenshotUrl: (id: string) => `${BASE}/audits/${id}/screenshot`,
  reportUrl: (id: string, format: "json" | "csv" | "pdf") => `${BASE}/reports/${id}?format=${format}`,
};
