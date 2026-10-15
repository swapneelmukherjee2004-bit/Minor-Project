import clsx from "clsx";
import { BarChart3, FlaskConical, History, LayoutDashboard, Menu, PlusCircle, Settings as Cog, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useSettings } from "@/hooks/queries";
import { ThemeToggle } from "@/components/ThemeToggle";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/audits/new", label: "New audit", icon: PlusCircle },
  { to: "/audits", label: "History", icon: History, end: true },
  { to: "/evaluation", label: "Evaluation", icon: FlaskConical },
  { to: "/settings", label: "Settings & methodology", icon: Cog },
];

export default function AppLayout() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  const settings = useSettings();
  useEffect(() => setOpen(false), [loc.pathname]);
  const linkCls = ({ isActive }: { isActive: boolean }) =>
    clsx("flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium", isActive ? "bg-brand/10 text-brand" : "text-muted hover:bg-subtle hover:text-fg");
  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2">Skip to main content</a>
      <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
          <button className="rounded-md p-2 hover:bg-subtle lg:hidden" aria-label={open ? "Close navigation menu" : "Open navigation menu"} aria-expanded={open} aria-controls="side-nav" onClick={() => setOpen(!open)}>
            {open ? <X className="h-5 w-5" aria-hidden /> : <Menu className="h-5 w-5" aria-hidden />}
          </button>
          <Link to="/" className="flex items-center gap-2 font-bold"><BarChart3 className="h-5 w-5 text-brand" aria-hidden />AccessAudit</Link>
          <div className="ml-auto flex items-center gap-3 text-xs">
            {settings.data?.demo_mode && <span className="rounded-full border border-warn/50 bg-warn/10 px-2 py-1 font-medium text-warn">Demo mode: AI is a mock</span>}
            <ThemeToggle />
          </div>
        </div>
      </header>
      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6">
        <nav id="side-nav" aria-label="Primary" className={clsx("w-56 shrink-0 space-y-1 lg:block", open ? "block" : "hidden")}>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end ?? false} className={linkCls}><n.icon className="h-4 w-4" aria-hidden />{n.label}</NavLink>
          ))}
        </nav>
        <main id="main" tabIndex={-1} className="min-w-0 flex-1"><Outlet /></main>
      </div>
      <footer className="border-t border-line py-6 text-center text-xs text-muted">
        AccessAudit is an audit aid, not a WCAG conformance certification. AI observations require human verification.
      </footer>
    </div>
  );
}
