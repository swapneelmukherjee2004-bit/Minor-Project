import * as RDialog from "@radix-ui/react-dialog";
import clsx from "clsx";
import { AlertTriangle, CheckCircle2, Info, Loader2, X } from "lucide-react";
import { createContext, useCallback, useContext, useState, type ButtonHTMLAttributes, type ReactNode, type RefObject, type SelectHTMLAttributes } from "react";

export function Button({ variant = "primary", className, loading, children, ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost"; loading?: boolean }) {
  const v = {
    primary: "bg-brand text-brand-fg hover:opacity-90", secondary: "border border-line bg-surface hover:bg-subtle",
    danger: "bg-danger text-white hover:opacity-90", ghost: "hover:bg-subtle",
  }[variant];
  return (
    <button {...p} disabled={p.disabled || loading}
      className={clsx("inline-flex min-h-[40px] items-center justify-center gap-2 rounded-lg px-4 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50", v, className)}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
}

export const Card = ({ className, children }: { className?: string; children: ReactNode }) => (
  <section className={clsx("rounded-xl border border-line bg-surface p-5 shadow-card", className)}>{children}</section>
);

const TONES: Record<string, string> = {
  neutral: "bg-subtle text-fg border-line", conv: "bg-conv/10 text-conv border-conv/30", ai: "bg-ai/10 text-ai border-ai/30",
  danger: "bg-danger/10 text-danger border-danger/30", warn: "bg-warn/10 text-warn border-warn/30", ok: "bg-ok/10 text-ok border-ok/30",
};
export const Badge = ({ tone = "neutral", children, className }: { tone?: keyof typeof TONES; children: ReactNode; className?: string }) => (
  <span className={clsx("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", TONES[tone], className)}>{children}</span>
);

export const severityTone = (s: string) => (s === "critical" || s === "high" ? "danger" : s === "medium" ? "warn" : "neutral");

export const Skeleton = ({ className }: { className?: string }) => (
  <div aria-hidden className={clsx("animate-pulse rounded-md bg-subtle", className)} />
);

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-line px-6 py-12 text-center">
      <Info className="mb-3 h-8 w-8 text-muted" aria-hidden />
      <h3 className="text-base font-semibold">{title}</h3>
      {children && <p className="mt-1 max-w-md text-sm text-muted">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-xl border border-danger/40 bg-danger/5 p-5">
      <div className="flex items-center gap-2 font-semibold text-danger"><AlertTriangle className="h-5 w-5" aria-hidden /> Could not load data</div>
      <p className="text-sm">{msg}</p>
      {onRetry && <Button variant="secondary" onClick={onRetry}>Try again</Button>}
    </div>
  );
}

export function Alert({ tone = "info", title, children }: { tone?: "info" | "warn" | "danger" | "ok"; title?: string; children: ReactNode }) {
  const t = { info: "border-conv/40 bg-conv/5", warn: "border-warn/50 bg-warn/5", danger: "border-danger/40 bg-danger/5", ok: "border-ok/40 bg-ok/5" }[tone];
  const Icon = tone === "ok" ? CheckCircle2 : tone === "info" ? Info : AlertTriangle;
  return (
    <div role={tone === "danger" ? "alert" : "note"} className={clsx("flex gap-3 rounded-lg border p-4 text-sm", t)}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div>{title && <p className="font-semibold">{title}</p>}<div className="text-fg/90">{children}</div></div>
    </div>
  );
}

export function Field({ label, htmlFor, hint, error, children }: { label: string; htmlFor: string; hint?: string; error?: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium">{label}</label>
      {children}
      {hint && <p id={`${htmlFor}-hint`} className="text-xs text-muted">{hint}</p>}
      {error && <p id={`${htmlFor}-error`} role="alert" className="text-sm text-danger">{error}</p>}
    </div>
  );
}
export const inputCls = "min-h-[40px] w-full rounded-lg border border-line bg-surface px-3 text-sm placeholder:text-muted/70";

export function SelectFilter({ label, id, value, onChange, options, ...rest }: { label: string; id: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[] } & Omit<SelectHTMLAttributes<HTMLSelectElement>, "onChange" | "value">) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-xs font-medium text-muted">{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={clsx(inputCls, "pr-8")} {...rest}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

export function Modal({ open, onOpenChange, title, description, children, returnFocus }: { open: boolean; onOpenChange: (o: boolean) => void; title: string; description?: string; children: ReactNode; returnFocus?: RefObject<HTMLElement | null> }) {
  return (
    <RDialog.Root open={open} onOpenChange={onOpenChange}>
      <RDialog.Portal>
        <RDialog.Overlay className="fixed inset-0 z-40 bg-black/50" />
        <RDialog.Content onCloseAutoFocus={(e) => { if (returnFocus?.current) { e.preventDefault(); returnFocus.current.focus(); } }} className="fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-line bg-surface p-6 shadow-xl">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <RDialog.Title className="text-lg font-semibold">{title}</RDialog.Title>
              <RDialog.Description className={description ? "mt-1 text-sm text-muted" : "sr-only"}>{description ?? title}</RDialog.Description>
            </div>
            <RDialog.Close aria-label="Close dialog" className="rounded-md p-1.5 hover:bg-subtle"><X className="h-5 w-5" aria-hidden /></RDialog.Close>
          </div>
          {children}
        </RDialog.Content>
      </RDialog.Portal>
    </RDialog.Root>
  );
}

// ---- toasts ----
type Toast = { id: number; tone: "ok" | "danger" | "info"; text: string };
const ToastCtx = createContext<(tone: Toast["tone"], text: string) => void>(() => {});
export const useToast = () => useContext(ToastCtx);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((tone: Toast["tone"], text: string) => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { id, tone, text }]);
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 6000);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div aria-live="polite" role="status" className="fixed bottom-4 right-4 z-[60] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
        {items.map((t) => (
          <div key={t.id} className={clsx("rounded-lg border bg-surface p-3 text-sm shadow-lg", t.tone === "danger" ? "border-danger/50" : t.tone === "ok" ? "border-ok/50" : "border-line")}>{t.text}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export const PageTitle = ({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) => (
  <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
    <div><h1 className="text-2xl font-bold tracking-tight">{title}</h1>{subtitle && <p className="mt-1 max-w-2xl text-sm text-muted">{subtitle}</p>}</div>
    {actions}
  </div>
);
