"""Audit pipeline + in-process background job runner (asyncio). Swap `submit` for a queue if scaling is ever needed."""
import asyncio
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.security import UrlNotAllowed, UrlPolicy
from app.models import Audit, Finding
from app.services import ai_audit_service as ai
from app.services.ai_providers import AIProvider, ProviderError, build_provider
from app.services.axe_audit_service import custom_checks, run_axe
from app.services.browser_service import AuditError, BrowserService
from app.services.finding_normalizer import assign_groups, normalize
from app.services.storage import Storage

log = logging.getLogger(__name__)


def _now():
    return datetime.now(timezone.utc)


class AuditRunner:
    def __init__(self, settings: Settings, sm: sessionmaker[Session], browser: BrowserService, storage: Storage,
                 provider_factory=build_provider):
        self.s, self.sm, self.browser, self.storage = settings, sm, browser, storage
        self.provider_factory = provider_factory
        self.sem = asyncio.Semaphore(settings.max_concurrent_audits)
        self.tasks: set[asyncio.Task] = set()

    # ----- job abstraction -----
    def submit(self, audit_id: str, policy: UrlPolicy | None = None) -> None:
        t = asyncio.create_task(self.run(audit_id, policy))
        self.tasks.add(t)
        t.add_done_callback(self.tasks.discard)

    def pending_count(self) -> int:
        with self.sm() as db:
            return len(db.scalars(select(Audit.id).where(Audit.status.in_(("queued", "running")))).all())

    def recover_interrupted(self) -> None:
        with self.sm() as db:
            db.execute(update(Audit).where(Audit.status.in_(("queued", "running"))).values(
                status="failed", error="Interrupted by a server restart.", completed_at=_now()))
            db.commit()

    # ----- pipeline -----
    def _stage(self, audit_id: str, **vals) -> None:
        with self.sm() as db:
            db.execute(update(Audit).where(Audit.id == audit_id).values(**vals))
            db.commit()

    async def run(self, audit_id: str, policy: UrlPolicy | None = None) -> None:
        policy = policy or UrlPolicy(fixture_origins=self.s.fixture_origin_set)
        async with self.sem:
            t0 = time.monotonic()
            try:
                await self._run(audit_id, policy)
            except (AuditError, UrlNotAllowed) as e:
                self._stage(audit_id, status="failed", error=str(e), stage=None, completed_at=_now())
            except Exception:  # noqa: BLE001 - last-resort guard, details go to logs only
                log.exception("audit crashed", extra={"audit_id": audit_id})
                self._stage(audit_id, status="failed", error="Unexpected internal error while auditing this page.",
                            stage=None, completed_at=_now())
            log.info("audit finished", extra={"audit_id": audit_id, "duration_ms": int((time.monotonic() - t0) * 1000)})

    async def _run(self, audit_id: str, policy: UrlPolicy) -> None:
        with self.sm() as db:
            a = db.get(Audit, audit_id)
            if a is None:
                return
            url, mode, capture = a.url, a.mode, a.capture_screenshot
        self._stage(audit_id, status="running", stage="loading page", started_at=_now())
        want_conv, want_ai = mode in ("conventional", "combined"), mode in ("ai", "combined")
        raw: list[dict] = []
        ai_error: str | None = None
        rejected = 0
        tool_versions: dict = {"playwright_browser": "chromium"}
        async with self.browser.open_page(url, policy) as (page, info):
            tool_versions["browser_version"] = page.context.browser.version if page.context.browser else None
            png = None
            if capture or want_ai:
                self._stage(audit_id, stage="capturing screenshot")
            if capture:
                png, w, h = await self.browser.screenshot(page)
                key = self.storage.save_screenshot(audit_id, png)
                self._stage(audit_id, screenshot_key=key, screenshot_width=w, screenshot_height=h)
            self._stage(audit_id, stage="extracting DOM", final_url=info.final_url, page_title=info.title[:512],
                        http_status=info.status)
            ctx = await self.browser.extract_dom(page)
            if want_conv:
                self._stage(audit_id, stage="running axe-core")
                axe_raw, axe_version = await run_axe(page)
                tool_versions["axe_core"] = axe_version
                canon = await self.browser.resolve_selectors(page, [f["raw_selector"] for f in axe_raw if f["raw_selector"]])
                it = iter(canon)
                canon_by_idx = [next(it) if f["raw_selector"] else None for f in axe_raw]
                raw += [normalize(f, c) for f, c in zip(axe_raw, canon_by_idx)]
                raw += [normalize(f, f["raw_selector"]) for f in custom_checks(ctx)]
        # browser closed; AI analysis needs no live page
        if want_ai:
            self._stage(audit_id, stage="running AI analysis")
            try:
                provider: AIProvider = self.provider_factory(self.s)
                tool_versions.update({"ai_provider": provider.name, "ai_model": provider.model})
                res = await ai.run_ai_audit(provider, self.s.prompt_version, ctx, png if (capture and png) else None)
                rejected = res.rejected
                raw += [normalize(f, f["raw_selector"]) for f in res.findings]
                if res.notes:
                    ai_error = None
                    tool_versions["notes"] = res.notes
            except (ProviderError, ai.AIOutputError) as e:
                ai_error = str(e)
                log.warning("AI audit failed: %s", type(e).__name__, extra={"audit_id": audit_id})
        assign_groups(raw)
        provider_name = tool_versions.get("ai_provider")
        with self.sm() as db:
            for f in raw:
                f = {k: v for k, v in f.items() if k != "raw_selector"}
                db.add(Finding(audit_id=audit_id, **f))
            a = db.get(Audit, audit_id)
            a.tool_versions = tool_versions
            a.dom_context = ai.bound_context(ctx)
            a.ai_error = ai_error
            a.ai_rejected_count = rejected
            a.demo_mode = bool(want_ai and (provider_name == "mock"))
            a.ai_provider = provider_name if want_ai else None
            a.ai_model = tool_versions.get("ai_model") if want_ai else None
            a.prompt_version = self.s.prompt_version if want_ai else None
            failed_ai_only = want_ai and not want_conv and ai_error is not None
            a.status = "failed" if failed_ai_only else "completed"
            a.error = f"AI analysis failed: {ai_error}" if failed_ai_only else None
            a.stage = None
            a.completed_at = _now()
            db.commit()
