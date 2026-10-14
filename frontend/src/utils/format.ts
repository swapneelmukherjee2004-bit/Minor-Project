export const fmtDate = (s: string | null | undefined) =>
  s ? new Date(s).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—";
/** Ground-truth-dependent numbers: null means "not computable", never 0. */
export const fmtMetric = (v: number | null | undefined) => (v === null || v === undefined ? "Not available" : v.toFixed(2));
export const pct = (v: number | null | undefined) => (v === null || v === undefined ? "Not available" : `${Math.round(v * 100)}%`);
export const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"] as const;
export const CATEGORIES = ["images", "navigation", "forms", "contrast", "semantics", "readability", "other"] as const;
export const methodLabel = (m: string) => (m === "ai" ? "AI (multimodal)" : m === "axe" ? "axe-core" : "Custom heuristic");
export const detectedLabel = (d: string | null) =>
  d === "both" ? "Found by both" : d === "ai_only" ? "AI only" : d === "conventional_only" ? "Conventional only" : "—";
export const statusLabel = (s: string) => (s === "needs_manual_review" ? "Needs manual review" : s[0].toUpperCase() + s.slice(1));
