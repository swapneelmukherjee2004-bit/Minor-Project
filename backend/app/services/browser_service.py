"""Playwright browser service: isolated context, SSRF-guarded routing, screenshot + DOM extraction."""
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urljoin, urlsplit

from playwright.async_api import Page, Playwright, async_playwright

from app.core.config import Settings
from app.core.security import UrlNotAllowed, UrlPolicy

log = logging.getLogger(__name__)
ASSETS = Path(__file__).resolve().parents[1] / "assets"
EXTRACT_JS = (ASSETS / "extract_dom.js").read_text()
RESOLVE_JS = (ASSETS / "resolve_selectors.js").read_text()

DOM_LIMITS = {"perType": 60, "html": 300, "bodyText": 1500}
_ALLOWED_NON_HTTP = ("data:", "blob:", "about:")


class AuditError(Exception):
    """User-facing audit failure (safe to show)."""


@dataclass
class PageInfo:
    final_url: str
    status: int | None
    title: str


class BrowserService:
    def __init__(self, settings: Settings):
        self.s = settings
        self._pw: Playwright | None = None

    async def start(self) -> None:
        if self._pw is None:
            self._pw = await async_playwright().start()

    async def stop(self) -> None:
        if self._pw:
            await self._pw.stop()
            self._pw = None

    def _launch_args(self) -> list[str]:
        args = ["--disable-extensions", "--disable-dev-shm-usage", "--no-first-run",
                "--disable-background-networking", "--disable-sync", "--mute-audio"]
        if self.s.browser_no_sandbox:
            args += ["--no-sandbox"]
        return args  # note: no --remote-debugging-port: no debugging interface is exposed

    @asynccontextmanager
    async def open_page(self, url: str, policy: UrlPolicy) -> AsyncIterator[tuple[Page, PageInfo]]:
        """Open `url` in a fresh, isolated, guarded context. Every sub-request is re-validated."""
        await self.start()
        assert self._pw is not None
        await policy.assert_allowed(url)
        kwargs = {"headless": True, "args": self._launch_args()}
        if self.s.browser_executable_path:
            kwargs["executable_path"] = self.s.browser_executable_path
        browser = await self._pw.chromium.launch(**kwargs)
        counter = {"n": 0, "blocked": 0}
        try:
            ctx = await browser.new_context(
                viewport={"width": self.s.viewport_width, "height": self.s.viewport_height},
                accept_downloads=False, bypass_csp=True, java_script_enabled=True,
                service_workers="block", permissions=[], ignore_https_errors=False,
                user_agent="AccessAudit/1.0 (accessibility research tool)",
            )
            ctx.set_default_timeout(self.s.nav_timeout_ms)

            async def guard(route, request):
                u = request.url
                if u.startswith(_ALLOWED_NON_HTTP):
                    return await route.continue_()
                counter["n"] += 1
                if counter["n"] > self.s.max_requests_per_page or request.resource_type in ("websocket", "media", "eventsource"):
                    return await route.abort("blockedbyclient")
                try:
                    await policy.assert_allowed(u)
                except UrlNotAllowed:
                    counter["blocked"] += 1
                    log.warning("blocked sub-request", extra={"event": "ssrf_block"})
                    return await route.abort("blockedbyclient")
                # Redirects are NOT re-routed by Chromium, so fetch without following them, validate each
                # Location ourselves and hand the 3xx back to the browser, which then issues a new (re-guarded) request.
                try:
                    resp = await route.fetch(max_redirects=0, timeout=self.s.nav_timeout_ms)
                except Exception:  # noqa: BLE001 - network failure: let the browser surface it
                    return await route.abort("failed")
                loc = resp.headers.get("location")
                if 300 <= resp.status < 400 and loc:
                    try:
                        await policy.assert_allowed(urljoin(u, loc))
                    except UrlNotAllowed:
                        counter["blocked"] += 1
                        log.warning("blocked redirect", extra={"event": "ssrf_block"})
                        return await route.abort("blockedbyclient")
                await route.fulfill(response=resp)

            await ctx.route("**/*", guard)
            page = await ctx.new_page()
            try:
                resp = await page.goto(url, wait_until="load", timeout=self.s.nav_timeout_ms)
            except Exception as e:  # playwright Error / TimeoutError
                msg = str(e)
                if counter["blocked"]:
                    raise AuditError("The page (or a redirect) pointed at a blocked network address.") from e
                if "Timeout" in msg:
                    raise AuditError("The page did not finish loading within the time limit.") from e
                if counter["blocked"] or "ERR_BLOCKED" in msg:
                    raise AuditError("The page (or a redirect) pointed at a blocked network address.") from e
                if "ERR_NAME_NOT_RESOLVED" in msg:
                    raise AuditError("The host name could not be resolved.") from e
                if "ERR_CERT" in msg or "SSL" in msg:
                    raise AuditError("The site's TLS certificate could not be verified.") from e
                raise AuditError("The page could not be loaded (connection failed or refused).") from e
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass  # bounded wait; pages with long-polling never go idle
            status = resp.status if resp else None
            ctype = (resp.headers.get("content-type", "") if resp else "").lower()
            if status and status >= 400:
                raise AuditError(f"The server responded with HTTP {status}.")
            if ctype and "html" not in ctype and "xml" not in ctype:
                raise AuditError(f"Unsupported content type '{ctype.split(';')[0]}'; only HTML pages can be audited.")
            final = page.url
            await policy.assert_allowed(final)
            yield page, PageInfo(final_url=final, status=status, title=await page.title())
        finally:
            await browser.close()

    async def screenshot(self, page: Page) -> tuple[bytes, int, int]:
        h = await page.evaluate("Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0)")
        height = int(min(max(h, self.s.viewport_height), self.s.max_screenshot_height))
        data = await page.screenshot(type="png", clip={"x": 0, "y": 0, "width": self.s.viewport_width, "height": height},
                                     full_page=True)
        return data, self.s.viewport_width, height

    async def extract_dom(self, page: Page) -> dict:
        return await page.evaluate(EXTRACT_JS, {"limits": DOM_LIMITS})

    async def resolve_selectors(self, page: Page, selectors: list[str]) -> list[str | None]:
        if not selectors:
            return []
        return await page.evaluate(RESOLVE_JS, selectors)


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "")[:255]
