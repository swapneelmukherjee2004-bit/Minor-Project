import { BarChart3 as BarChart3Icon, Eye, FileSearch, GitCompare, Layers, ScanSearch, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "@/components/ui";

const STEPS = [
  ["Render", "A sandboxed browser loads the page and captures a real screenshot."],
  ["Extract", "Headings, images, links, buttons and form controls are collected with their accessible names."],
  ["Audit", "axe-core runs rule-based checks; a multimodal model reviews screenshot + DOM context."],
  ["Validate", "AI output is schema-checked; selectors and HTML are filled in by the server, never the model."],
  ["Compare", "Findings are matched by element and criterion to show what each method found."],
];

export default function Landing() {
  return (
    <div className="space-y-14">
      <section className="py-8 text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">Minor project research tool</p>
        <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">Does multimodal AI see accessibility problems that rule-based tools miss?</h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted">
          AccessAudit audits a web page with axe-core <em>and</em> a vision-capable AI model, keeps the evidence for every finding, and
          compares the two methods side by side.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link to="/audits/new" className="inline-flex min-h-[44px] items-center rounded-lg bg-brand px-6 font-semibold text-brand-fg hover:opacity-90">Start Accessibility Audit</Link>
          <Link to="/methodology" className="inline-flex min-h-[44px] items-center rounded-lg border border-line px-6 font-medium hover:bg-subtle">Methodology and limitations</Link>
        </div>
      </section>

      <section aria-labelledby="cmp" className="grid gap-4 md:grid-cols-2">
        <h2 id="cmp" className="sr-only">Conventional versus AI-based auditing</h2>
        <Card>
          <ScanSearch className="mb-2 h-6 w-6 text-conv" aria-hidden />
          <h3 className="text-lg font-semibold">Conventional (rule-based)</h3>
          <p className="mt-2 text-sm text-muted">Deterministic and reproducible. Reliable for missing alt attributes, unlabeled fields, invalid ARIA and computable colour contrast. Cannot judge whether an existing label is <em>meaningful</em>.</p>
        </Card>
        <Card>
          <Eye className="mb-2 h-6 w-6 text-ai" aria-hidden />
          <h3 className="text-lg font-semibold">Multimodal AI</h3>
          <p className="mt-2 text-sm text-muted">Reads the screenshot together with the DOM to question context: vague alt text, ambiguous link labels, visual headings without semantics. Probabilistic, can be wrong, and every finding needs human verification.</p>
        </Card>
      </section>

      <section aria-labelledby="feat">
        <h2 id="feat" className="mb-4 text-2xl font-bold">What you get</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[
            [FileSearch, "Evidence for every finding", "Selector, HTML excerpt, DOM and screenshot observations, and WCAG criteria only where supported."],
            [GitCompare, "Honest comparison", "Conventional-only, AI-only and overlapping detections, with precision/recall only when ground truth exists."],
            [ShieldCheck, "Guarded browsing", "SSRF protection, redirect re-validation, request limits and an isolated browser context."],
            [Layers, "Confirmed vs suspected", "Technical violations are separated from AI observations and items needing manual review."],
            [Eye, "Demo mode", "Runs without paid credentials; clearly labelled mock AI output."],
            [BarChart3Icon, "Exports", "JSON, CSV and PDF reports including limitations and tool versions."],
          ].map(([Icon, t, d], i) => {
            const I = Icon as typeof Eye;
            return <Card key={i}><I className="mb-2 h-5 w-5 text-brand" aria-hidden /><h3 className="font-semibold">{t as string}</h3><p className="mt-1 text-sm text-muted">{d as string}</p></Card>;
          })}
        </div>
      </section>

      <section aria-labelledby="flow">
        <h2 id="flow" className="mb-4 text-2xl font-bold">How an audit works</h2>
        <ol className="grid gap-3 md:grid-cols-5">
          {STEPS.map(([t, d], i) => (
            <li key={t} className="rounded-xl border border-line bg-surface p-4">
              <span className="mb-2 flex h-7 w-7 items-center justify-center rounded-full bg-brand text-sm font-bold text-brand-fg">{i + 1}</span>
              <h3 className="font-semibold">{t}</h3><p className="mt-1 text-xs text-muted">{d}</p>
            </li>
          ))}
        </ol>
      </section>

      <p className="text-center text-sm text-muted">Results are an audit aid and do not prove WCAG conformance. <Link className="text-brand underline" to="/methodology">Read the limitations.</Link></p>
    </div>
  );
}
