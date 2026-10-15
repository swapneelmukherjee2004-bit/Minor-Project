import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { ToastProvider } from "@/components/ui";
import { ThemeProvider } from "@/hooks/useTheme";

export function renderApp(ui: ReactElement, route = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><ThemeProvider><ToastProvider><MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter></ToastProvider></ThemeProvider></QueryClientProvider>);
}

type Handler = (url: string, init?: RequestInit) => { status?: number; body?: unknown } | undefined;
/** Stub fetch with route handlers; unknown routes fail the test loudly. */
export function mockApi(handler: Handler) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input).replace("/api/v1", "");
    const r = handler(url, init);
    if (!r) throw new Error(`Unexpected fetch ${url}`);
    return new Response(r.status === 204 ? null : JSON.stringify(r.body), { status: r.status ?? 200, headers: { "content-type": "application/json" } });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

export const SETTINGS = { app_name: "AccessAudit", demo_mode: true, ai_provider: "mock", ai_model: "demo-heuristic-v1", ai_configured: true, prompt_version: "audit-v1",
  wcag: { version: "2.2", levels: ["A", "AA"] }, limits: { navigation_timeout_ms: 30000, max_requests_per_page: 400, max_screenshot_height_px: 8000, max_concurrent_audits: 2, audit_rate_limit: "10/minute" },
  local_fixtures_enabled: false, fixture_origin: null };
