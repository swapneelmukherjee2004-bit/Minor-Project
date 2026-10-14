import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { Alert, Button, Card, Field, PageTitle, inputCls, useToast } from "@/components/ui";
import { useEvalSummary, useSettings } from "@/hooks/queries";
import { ApiError, api } from "@/services/api";

export const schema = z.object({
  url: z.string().trim().min(1, "Enter a website URL.").max(2048, "URL is too long.")
    .refine((v) => { try { const u = new URL(v); return u.protocol === "http:" || u.protocol === "https:"; } catch { return false; } },
      "Enter a full URL starting with http:// or https://, for example https://example.com"),
  route: z.string().trim().max(500).refine((v) => v === "" || (v.startsWith("/") && !v.startsWith("//")), "A route must start with a single “/”, for example /pricing.").optional(),
  mode: z.enum(["conventional", "ai", "combined"]),
  capture_screenshot: z.boolean(),
});
type Form = z.infer<typeof schema>;

export const buildUrl = (base: string, route?: string) => {
  try { return route ? new URL(route, new URL(base).origin).toString() : base; } catch { return base; }
};

const MODES = [
  { v: "combined", t: "Combined", d: "axe-core plus AI analysis, with side-by-side comparison. Recommended." },
  { v: "conventional", t: "Conventional only", d: "axe-core rules and a few deterministic checks. No AI provider needed." },
  { v: "ai", t: "AI-powered only", d: "Screenshot and DOM context analysed by the AI model." },
] as const;

export default function NewAudit() {
  const nav = useNavigate();
  const toast = useToast();
  const settings = useSettings();
  const evalSum = useEvalSummary();
  const { register, handleSubmit, watch, setValue, setError, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema), defaultValues: { url: "", route: "", mode: "combined", capture_screenshot: true },
  });
  const m = useMutation({
    mutationFn: (f: Form) => api.createAudit({ url: buildUrl(f.url, f.route), mode: f.mode, capture_screenshot: f.capture_screenshot }),
    onSuccess: (a) => { toast("ok", "Audit started."); nav(`/audits/${a.id}`); },
    onError: (e) => {
      const msg = e instanceof ApiError ? e.message : "Could not start the audit.";
      if (e instanceof ApiError && e.code === "url_not_allowed") setError("url", { message: msg });
      else toast("danger", msg);
    },
  });
  const [mode, url, route, shot] = [watch("mode"), watch("url"), watch("route"), watch("capture_screenshot")];
  const target = buildUrl(url, route);
  const usesAi = mode !== "conventional";
  const fixtures = settings.data?.local_fixtures_enabled ? evalSum.data?.dataset?.pages ?? [] : [];

  return (
    <>
      <PageTitle title="New accessibility audit" subtitle="Submit a public web page. Private and internal network addresses are blocked." />
      <form onSubmit={handleSubmit((f) => m.mutate(f))} noValidate className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <Card className="space-y-5">
          <Field label="Website URL" htmlFor="url" error={errors.url?.message} hint="Only public http(s) pages that you are permitted to test.">
            <input id="url" type="url" inputMode="url" autoComplete="url" placeholder="https://example.com" className={inputCls}
              aria-invalid={!!errors.url} aria-describedby={`url-hint${errors.url ? " url-error" : ""}`} {...register("url")} />
          </Field>
          {fixtures.length > 0 && (
            <Field label="…or a bundled test page" htmlFor="fixture" hint="Controlled fixtures served by this backend, used for the evaluation dataset.">
              <select id="fixture" className={inputCls} defaultValue="" onChange={(e) => e.target.value && setValue("url", `${settings.data!.fixture_origin}/fixtures/${e.target.value}`, { shouldValidate: true })}>
                <option value="">Choose a fixture…</option>
                {fixtures.map((p) => <option key={p.page_id} value={p.fixture_file}>{p.page_id} ({p.condition})</option>)}
              </select>
            </Field>
          )}
          <Field label="Page or route (optional)" htmlFor="route" error={errors.route?.message} hint="A path within the same website, such as /pricing. Leave empty to audit the URL as entered.">
            <input id="route" placeholder="/pricing" className={inputCls} aria-invalid={!!errors.route} aria-describedby={`route-hint${errors.route ? " route-error" : ""}`} {...register("route")} />
          </Field>
          <fieldset>
            <legend className="mb-2 text-sm font-medium">Audit mode</legend>
            <div className="grid gap-2">
              {MODES.map((o) => (
                <label key={o.v} className="flex cursor-pointer items-start gap-3 rounded-lg border border-line p-3 has-[:checked]:border-brand has-[:checked]:bg-brand/5">
                  <input type="radio" value={o.v} className="mt-1" {...register("mode")} />
                  <span><span className="block text-sm font-medium">{o.t}</span><span className="block text-xs text-muted">{o.d}</span></span>
                </label>
              ))}
            </div>
          </fieldset>
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" className="mt-1" {...register("capture_screenshot")} />
            <span><span className="font-medium">Capture screenshot</span><span className="block text-xs text-muted">Needed for visual AI observations. Without it the AI sees only DOM context.</span></span>
          </label>
          <Button type="submit" loading={m.isPending}>Start audit</Button>
        </Card>

        <aside aria-labelledby="what" className="space-y-3">
          <Card>
            <h2 id="what" className="mb-2 font-semibold">What will be analyzed</h2>
            <ul className="list-disc space-y-1.5 pl-5 text-sm text-muted">
              <li>Target: <span className="break-all text-fg">{url ? target : "not set yet"}</span></li>
              <li>Rendered in an isolated headless browser (1280px wide, bounded time and request budget).</li>
              {mode !== "ai" && <li>axe-core rules for WCAG 2.2 A/AA plus a few labelled custom heuristics.</li>}
              {usesAi && <li>{shot ? "Screenshot (top region) and " : ""}extracted DOM context sent to the AI provider: {settings.data ? (settings.data.demo_mode ? "mock demo provider (nothing leaves this server)" : `${settings.data.ai_provider} / ${settings.data.ai_model}`) : "…"}.</li>}
            </ul>
          </Card>
          {usesAi && settings.data?.demo_mode && <Alert tone="warn" title="Demo mode">No AI credentials are configured. AI findings come from a clearly labelled mock, not a real model.</Alert>}
          {usesAi && settings.data && !settings.data.demo_mode && <Alert tone="info">The page text and a screenshot are sent to the configured AI provider. Do not audit pages containing confidential data.</Alert>}
        </aside>
      </form>
    </>
  );
}
