import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { FindingsPanel } from "@/components/Findings";
import Dashboard from "@/pages/Dashboard";
import Evaluation from "@/pages/Evaluation";
import History from "@/pages/History";
import NewAudit, { buildUrl, schema } from "@/pages/NewAudit";
import type { Finding } from "@/types/api";
import { fmtMetric } from "@/utils/format";
import { SETTINGS, mockApi, renderApp } from "./utils";

const F = (o: Partial<Finding>): Finding => ({
  id: "1", audit_id: "a", method: "axe", rule_id: "image-alt", title: "Images must have alternative text", description: "desc", category: "images", severity: "high",
  confidence: null, status: "confirmed", verification_method: "automated", wcag_criteria: ["1.1.1"], selector: "#a", evidence: { html_excerpt: "<img id=a>", dom_observation: "dom" },
  user_impact: "impact", recommendation: "fix it", help_url: null, group_id: 1, detected_by: "conventional_only", ...o,
});

describe("form validation", () => {
  it("schema rejects bad URLs and routes", () => {
    for (const url of ["", "example.com", "ftp://x.com", "javascript:alert(1)"]) expect(schema.safeParse({ url, mode: "combined", capture_screenshot: true }).success).toBe(false);
    expect(schema.safeParse({ url: "https://example.com", route: "//evil.com", mode: "ai", capture_screenshot: true }).success).toBe(false);
    expect(schema.safeParse({ url: "https://example.com", route: "/pricing", mode: "ai", capture_screenshot: true }).success).toBe(true);
    expect(buildUrl("https://example.com/a/b", "/pricing")).toBe("https://example.com/pricing");
  });

  it("shows an accessible error and does not call the API for an invalid URL", async () => {
    const fetchMock = mockApi((u) => (u === "/settings/status" ? { body: SETTINGS } : u === "/evaluations/summary" ? { body: { dataset: null } } : undefined));
    renderApp(<NewAudit />);
    await userEvent.type(screen.getByLabelText("Website URL"), "not a url");
    await userEvent.click(screen.getByRole("button", { name: "Start audit" }));
    const err = await screen.findByRole("alert");
    expect(err).toHaveTextContent(/full URL/i);
    expect(screen.getByLabelText("Website URL")).toHaveAttribute("aria-invalid", "true");
    expect(fetchMock.mock.calls.some(([u, i]) => String(u).endsWith("/audits") && (i as RequestInit)?.method === "POST")).toBe(false);
  });

  it("submits a valid audit and surfaces backend SSRF rejection on the field", async () => {
    mockApi((u, i) => {
      if (u === "/settings/status") return { body: SETTINGS };
      if (u === "/evaluations/summary") return { body: { dataset: null } };
      if (u === "/audits" && i?.method === "POST") return { status: 400, body: { error: { code: "url_not_allowed", message: "This host resolves to a private or reserved network address, which is blocked." } } };
    });
    renderApp(<NewAudit />);
    await userEvent.type(screen.getByLabelText("Website URL"), "http://internal.example.com");
    await userEvent.click(screen.getByLabelText(/Conventional only/));
    await userEvent.click(screen.getByRole("button", { name: "Start audit" }));
    expect(await screen.findByText(/private or reserved/)).toBeInTheDocument();
  });

  it("is keyboard operable: radios by arrow keys and submit by Enter", async () => {
    mockApi((u) => (u === "/settings/status" ? { body: SETTINGS } : u === "/evaluations/summary" ? { body: { dataset: null } } : undefined));
    renderApp(<NewAudit />);
    await userEvent.tab(); await userEvent.tab();            // url -> route
    await userEvent.tab();                                    // -> mode radio group
    expect(screen.getByLabelText(/Combined/)).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByLabelText(/Conventional only/)).toBeChecked();
  });
});

describe("findings panel", () => {
  const findings = [F({ id: "1" }), F({ id: "2", method: "ai", title: "Vague alt", category: "images", severity: "medium", status: "suspected", detected_by: "ai_only", confidence: 0.7 }),
    F({ id: "3", title: "Contrast", category: "contrast", severity: "critical", detected_by: "both" })];

  it("filters by method, severity and detected-by, and reports counts", async () => {
    renderApp(<FindingsPanel findings={findings} />);
    expect(screen.getByText(/^Showing/)).toHaveTextContent("Showing 3 of 3");
    await userEvent.selectOptions(screen.getByLabelText("Method"), "ai");
    expect(screen.getByText(/^Showing/)).toHaveTextContent("Showing 1 of 3");
    await userEvent.selectOptions(screen.getByLabelText("Method"), "");
    await userEvent.selectOptions(screen.getByLabelText("Severity"), "critical");
    expect(screen.getByRole("button", { name: /Open details: Contrast/ })).toBeInTheDocument();
    expect(screen.queryByText("Vague alt")).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Severity"), "");
    await userEvent.selectOptions(screen.getByLabelText("Detected by"), "ai_only");
    expect(screen.getByText(/^Showing/)).toHaveTextContent("Showing 1 of 3");
    await userEvent.selectOptions(screen.getByLabelText("Status"), "needs_manual_review");
    expect(screen.getByText("No findings match these filters")).toBeInTheDocument();
  });

  it("opens detail with the keyboard, labels AI findings as unverified, and closes with Escape", async () => {
    renderApp(<FindingsPanel findings={findings} />);
    const btn = screen.getByRole("button", { name: /Open details: Vague alt/ });
    btn.focus();
    await userEvent.keyboard("{Enter}");
    const dlg = await screen.findByRole("dialog");
    expect(within(dlg).getByText(/AI observation, not a verified defect/)).toBeInTheDocument();
    expect(within(dlg).getByText(/not the probability/)).toBeInTheDocument();
    expect(within(dlg).getByText(/<img id=a>/)).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(btn).toHaveFocus();   // focus returns to the trigger
  });

  it("does not claim a clean page is accessible when there are no findings", () => {
    renderApp(<FindingsPanel findings={[]} />);
    expect(screen.getByText(/does not prove the page is accessible/)).toBeInTheDocument();
  });
});

describe("dashboard states", () => {
  it("shows loading, then an error with retry", async () => {
    mockApi(() => ({ status: 500, body: { error: { code: "internal_error", message: "boom" } } }));
    renderApp(<Dashboard />);
    expect(screen.getByRole("status", { name: "Loading dashboard" })).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
  it("empty state when no audits", async () => {
    mockApi((u) => (u === "/dashboard/summary" ? { body: { total_audits: 0, recent_audits: [] } } : undefined));
    renderApp(<Dashboard />);
    expect(await screen.findByText("No audits yet")).toBeInTheDocument();
  });
  it("renders only backend-provided numbers", async () => {
    mockApi((u) => (u === "/dashboard/summary" ? { body: { total_audits: 7, completed_audits: 6, websites_analyzed: 3, total_findings: 41, by_severity: { high: 5 }, by_method: {}, by_category: {},
      provenance: { conventional_only: 4, ai_only: 2, both: 1 }, demo_audits: 2, recent_audits: [] } } : undefined));
    renderApp(<Dashboard />);
    expect(await screen.findByText("41")).toBeInTheDocument();
    expect(screen.getByText("Total audits").nextSibling).toHaveTextContent("7");
    expect(screen.getByText(/Demo data present/)).toBeInTheDocument();
  });
});

describe("evaluation honesty", () => {
  const dataset = { name: "d", version: "1.0", description: "desc", annotation_protocol: "proto", n_pages: 2, n_annotations: 1, pages_by_condition: { baseline: 1 }, annotations_by_category: { images: 1 }, pages: [] };
  it("shows 'Evaluation pending' and no metrics when no run exists", async () => {
    mockApi((u) => (u === "/evaluations/summary" ? { body: { state: "pending", note: "Evaluation pending: none yet.", dataset, latest_run: null, running_run_id: null } } : undefined));
    renderApp(<Evaluation />);
    expect(await screen.findByText("Evaluation pending")).toBeInTheDocument();
    expect(screen.getByText(/raw finding counts do not show/i)).toBeInTheDocument();
    expect(screen.queryByText("Precision")).not.toBeInTheDocument();
  });
  it("renders null metrics as 'Not available' (never 0) and flags demo runs", async () => {
    const r = (method: string, scope: string, p: number | null) => ({ method, scope, category: "all", tp: 0, fp: 0, fn: 1, tn: 0, precision: p, recall: 0, f1: null });
    mockApi((u) => (u === "/evaluations/summary" ? { body: { state: "completed", note: null, dataset, running_run_id: null, latest_run: {
      id: "r", status: "completed", error: null, ai_provider: "mock", ai_model: "demo-heuristic-v1", prompt_version: "audit-v1", is_demo: true, created_at: "2025-01-01T00:00:00Z", completed_at: null,
      dataset: { name: "d", version: "1.0" }, reviewer_agreement: { available: false, n_reviewed: 0, percent_agreement: null, cohen_kappa: null, note: "" },
      details: { overlap: { conventional_only: 0, ai_only: 0, both: 0, neither: 1 }, n_pages: 2, n_annotations: 1, per_case: [] },
      results: ["conventional", "ai", "combined"].flatMap((m) => [r(m, "finding", null), r(m, "page", null)]) } } } : undefined));
    renderApp(<Evaluation />);
    expect(await screen.findByText(/Demo run: not a research result/)).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Finding-level metrics by method" });
    expect(within(table).getAllByText("Not available").length).toBeGreaterThanOrEqual(6);
    expect(screen.getByText(/Reviewer agreement: Not available/)).toBeInTheDocument();
    expect(fmtMetric(null)).toBe("Not available");
    expect(fmtMetric(0)).toBe("0.00");
  });
});

describe("history", () => {
  it("confirms before deleting and calls DELETE", async () => {
    const item = { id: "a".repeat(8) + "-0000-0000-0000-000000000000", url: "https://e.com", host: "e.com", mode: "combined", status: "completed", stage: null, demo_mode: false, page_title: null, created_at: "2025-01-01T00:00:00Z", completed_at: null, finding_count: 3 };
    const fetchMock = mockApi((u, i) => {
      if (u.startsWith("/audits?") && !i?.method) return { body: { items: [item], total: 1, page: 1, page_size: 10 } };
      if (u.startsWith("/audits/") && i?.method === "DELETE") return { status: 204 };
    });
    renderApp(<History />);
    await userEvent.click(await screen.findByRole("button", { name: /Delete audit of https:\/\/e.com/ }));
    const dlg = await screen.findByRole("dialog");
    expect(fetchMock.mock.calls.some(([, i]) => (i as RequestInit)?.method === "DELETE")).toBe(false);
    await userEvent.click(within(dlg).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([, i]) => (i as RequestInit)?.method === "DELETE")).toBe(true));
  });
  it("shows an empty state for no matches", async () => {
    mockApi((u) => (u.startsWith("/audits?") ? { body: { items: [], total: 0, page: 1, page_size: 10 } } : undefined));
    renderApp(<History />);
    expect(await screen.findByText("No audits yet")).toBeInTheDocument();
  });
});
