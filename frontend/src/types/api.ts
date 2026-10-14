export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type Category = "images" | "navigation" | "forms" | "contrast" | "semantics" | "readability" | "other";
export type FindingStatus = "confirmed" | "suspected" | "needs_manual_review";
export type Method = "axe" | "custom" | "ai";
export type AuditMode = "conventional" | "ai" | "combined";
export type AuditStatus = "queued" | "running" | "completed" | "failed";
export type DetectedBy = "conventional_only" | "ai_only" | "both";

export interface AuditSummary {
  id: string; url: string; host: string; mode: AuditMode; status: AuditStatus; stage: string | null; demo_mode: boolean;
  page_title: string | null; created_at: string; completed_at: string | null; finding_count: number;
}
export interface AuditDetail extends AuditSummary {
  final_url: string | null; error: string | null; ai_error: string | null; capture_screenshot: boolean; has_screenshot: boolean;
  screenshot_width: number | null; screenshot_height: number | null; ai_provider: string | null; ai_model: string | null;
  prompt_version: string | null; http_status: number | null; tool_versions: Record<string, unknown> | null;
  config: Record<string, unknown> | null; ai_rejected_count: number; started_at: string | null;
}
export interface Evidence {
  screenshot_observation?: string; dom_observation?: string; html_excerpt?: string; selector?: string; extra?: Record<string, unknown>;
}
export interface Finding {
  id: string; audit_id: string; method: Method; rule_id: string; title: string; description: string; category: Category;
  severity: Severity; confidence: number | null; status: FindingStatus; verification_method: string; wcag_criteria: string[];
  selector: string | null; evidence: Evidence; user_impact: string; recommendation: string; help_url: string | null;
  group_id: number | null; detected_by: DetectedBy | null;
}
export interface Paged<T> { items: T[]; total: number; page: number; page_size: number }

export interface Prf { tp: number; fp: number; fn: number; tn?: number | null; precision: number | null; recall: number | null; f1: number | null }
export interface MethodMetrics { finding: Prf; page: Prf; per_category: Record<string, Prf> }
export type Overlap = { conventional_only: number; ai_only: number; both: number; neither: number };
export interface GroundTruth {
  available: boolean; reason?: string; page_id?: string; condition?: string; n_annotations?: number;
  methods?: Record<"conventional" | "ai" | "combined", MethodMetrics>; overlap?: Overlap;
}
export interface Comparison {
  counts: Record<DetectedBy, number>; total_groups: number; by_method: Record<Method, number>;
  ground_truth: GroundTruth; demo_mode: boolean;
}
export interface DashboardSummary {
  total_audits: number; completed_audits: number; websites_analyzed: number; total_findings: number;
  by_severity: Record<string, number>; by_method: Record<string, number>; by_category: Record<string, number>;
  provenance: Record<DetectedBy, number>; demo_audits: number; recent_audits: AuditSummary[];
}
export interface EvalResultRow extends Prf { method: "conventional" | "ai" | "combined"; scope: "finding" | "page"; category: string }
export interface EvalRun {
  id: string; status: string; error: string | null; ai_provider: string; ai_model: string; prompt_version: string; is_demo: boolean;
  created_at: string; completed_at: string | null; dataset: { name: string; version: string };
  details: { overlap: Overlap; n_pages: number; n_annotations: number; per_case: unknown[] } | null;
  reviewer_agreement: { available: boolean; n_reviewed: number; percent_agreement: number | null; cohen_kappa: number | null; note: string } | null;
  results: EvalResultRow[];
}
export interface EvalSummary {
  state: "pending" | "completed"; note: string | null; running_run_id: string | null; latest_run: EvalRun | null;
  dataset: null | {
    name: string; version: string; description: string; annotation_protocol: string; n_pages: number; n_annotations: number;
    pages_by_condition: Record<string, number>; annotations_by_category: Record<string, number>;
    pages: { page_id: string; fixture_file: string; condition: string; description: string; n_annotations: number }[];
  };
}
export interface SettingsStatus {
  app_name: string; demo_mode: boolean; ai_provider: string; ai_model: string; ai_configured: boolean; prompt_version: string;
  wcag: { version: string; levels: string[] };
  limits: { navigation_timeout_ms: number; max_requests_per_page: number; max_screenshot_height_px: number; max_concurrent_audits: number; audit_rate_limit: string };
  local_fixtures_enabled: boolean; fixture_origin: string | null;
}
