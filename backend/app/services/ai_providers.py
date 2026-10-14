"""AI provider adapters (Strategy pattern). API keys never leave the backend and are never logged."""
import asyncio
import base64
import json
import logging
import random
import re
from typing import Protocol

import httpx

from app.core.config import Settings

log = logging.getLogger(__name__)
CONTEXT_START, CONTEXT_END = "<<<PAGE_CONTEXT_JSON", "PAGE_CONTEXT_JSON>>>"


class ProviderError(Exception):
    """Provider failure; message is sanitised and safe to store/show."""


class AIProvider(Protocol):
    name: str
    model: str

    async def complete(self, system: str, user_text: str, image_jpeg: bytes | None) -> str: ...


async def _post_with_retry(client: httpx.AsyncClient, url: str, headers: dict, body: dict, retries: int) -> dict:
    delay = 1.0
    for attempt in range(retries + 1):
        try:
            r = await client.post(url, headers=headers, json=body)
            if r.status_code == 429 or r.status_code >= 500:
                raise httpx.HTTPStatusError("transient", request=r.request, response=r)
            if r.status_code >= 400:
                # do not echo the body: it may contain prompt fragments
                raise ProviderError(f"Provider rejected the request (HTTP {r.status_code}). Check model name, key and quota.")
            return r.json()
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if attempt >= retries:
                raise ProviderError(f"Provider unavailable after {retries + 1} attempts ({status or type(e).__name__}).") from None
            log.warning("transient AI provider error; retrying", extra={"event": "ai_retry"})
            await asyncio.sleep(min(delay, 20) + random.uniform(0, 0.25))
            delay *= 2
    raise ProviderError("Provider unavailable.")


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, s: Settings):
        self.s, self.model = s, s.ai_model
        self.base = (s.ai_base_url or "https://api.anthropic.com").rstrip("/")

    async def complete(self, system, user_text, image_jpeg):
        content: list[dict] = []
        if image_jpeg:
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                        "data": base64.b64encode(image_jpeg).decode()}})
        content.append({"type": "text", "text": user_text})
        body = {"model": self.model, "max_tokens": self.s.ai_max_output_tokens, "system": system,
                "messages": [{"role": "user", "content": content}]}
        headers = {"x-api-key": self.s.ai_api_key.get_secret_value(), "anthropic-version": "2023-06-01",
                   "content-type": "application/json"}
        async with httpx.AsyncClient(timeout=self.s.ai_timeout_seconds) as c:
            data = await _post_with_retry(c, f"{self.base}/v1/messages", headers, body, self.s.ai_max_retries)
        try:
            return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError):
            raise ProviderError("Unexpected provider response shape.") from None


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(self, s: Settings):
        self.s, self.model = s, s.ai_model
        self.base = s.ai_base_url.rstrip("/")

    async def complete(self, system, user_text, image_jpeg):
        parts: list[dict] = [{"type": "text", "text": user_text}]
        if image_jpeg:
            parts.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(image_jpeg).decode()}})
        body = {"model": self.model, "max_tokens": self.s.ai_max_output_tokens, "temperature": 0,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": parts}]}
        headers = {"Authorization": f"Bearer {self.s.ai_api_key.get_secret_value()}", "content-type": "application/json"}
        async with httpx.AsyncClient(timeout=self.s.ai_timeout_seconds) as c:
            data = await _post_with_retry(c, f"{self.base}/chat/completions", headers, body, self.s.ai_max_retries)
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise ProviderError("Unexpected provider response shape.") from None


_VAGUE_ALT = {"image", "picture", "photo", "graphic", "icon", "banner", "img", "logo", "pic", "photograph", "illustration"}
_TOKEN = re.compile(r"[a-z]{3,}")


class MockProvider:
    """DEMO provider: no network, no model. It applies simple heuristics to the supplied DOM context and emits
    schema-conforming JSON so the full pipeline can run without credentials. Its output is NOT evidence about
    multimodal AI quality and is labelled as demo data everywhere in the UI."""
    name = "mock"
    model = "demo-heuristic-v1"

    async def complete(self, system: str, user_text: str, image_jpeg: bytes | None) -> str:
        raw = user_text.split(CONTEXT_START, 1)[1].rsplit(CONTEXT_END, 1)[0]
        ctx = json.loads(raw)["page"]
        shot = bool(image_jpeg)
        out: list[dict] = []

        def add(el, **kw):
            base = {"element_ref": el["ref"], "wcag_criteria": [], "screenshot_observation": "",
                    "verification_method": "AI_inference", "status": "suspected", "user_impact": "", "recommendation": ""}
            base.update(kw)
            out.append(base)

        for im in ctx.get("images", []):
            alt = (im.get("alt") or "").strip()
            if not alt:
                continue
            toks = set(_TOKEN.findall(alt.lower()))
            if alt.lower() in _VAGUE_ALT or (len(alt.split()) == 1 and alt.lower() in _VAGUE_ALT):
                add(im, title="Alt text is present but uninformative", category="images", severity="medium", confidence=0.7,
                    description=f"The alt text \"{alt}\" does not convey the purpose or content of the image.",
                    dom_observation=f"img alt=\"{alt}\"; nearby: {im.get('nearbyText', '')[:160]}", wcag_criteria=["1.1.1"],
                    user_impact="Screen-reader users get no information about what the image shows or why it is there.",
                    recommendation="Replace with a concise description of the image's purpose in context, or alt=\"\" if decorative.")
                continue
            near = set(_TOKEN.findall((im.get("nearbyText") or "").lower()))
            if len(toks) >= 2 and len(near) >= 4 and not (toks & near) and "caption:" in (im.get("nearbyText") or ""):
                add(im, title="Alt text may not match the surrounding context", category="images", severity="low", confidence=0.35,
                    status="needs_manual_review", verification_method="manual_review",
                    description=f"The alt text \"{alt}\" shares no terms with the image's caption/nearby text.",
                    dom_observation=f"alt=\"{alt}\"; nearby: {im.get('nearbyText', '')[:200]}", wcag_criteria=["1.1.1"],
                    recommendation="Check whether the description matches what the caption and text say about the image.")
        for a in ctx.get("links", []) + ctx.get("buttons", []):
            name = (a.get("accessibleName") or "").strip().lower()
            vis = (a.get("visibleText") or a.get("text") or "").strip().lower()
            if name in {"click here", "here", "read more", "more", "learn more", "link", "details"}:
                add(a, title="Ambiguous link label", category="navigation", severity="medium", confidence=0.65,
                    description=f"The label \"{name}\" is not meaningful out of context.", wcag_criteria=["2.4.4"],
                    dom_observation=f"accessibleName=\"{name}\"; nearby: {a.get('nearbyText', '')[:160]}",
                    user_impact="Users navigating by a list of links cannot tell where this one goes.",
                    recommendation="Use descriptive link text that states the destination or action.")
            elif a.get("ariaLabel") and vis and vis not in a["ariaLabel"].strip().lower():
                add(a, title="Accessible name does not contain the visible label", category="semantics", severity="medium",
                    confidence=0.7, wcag_criteria=["2.5.3"],
                    description=f"The visible label \"{vis}\" differs from the accessible name \"{a['ariaLabel']}\".",
                    dom_observation=f"visible text=\"{vis}\"; aria-label=\"{a['ariaLabel']}\"",
                    user_impact="Speech-input users who say the visible label may fail to activate the control.",
                    recommendation="Make the accessible name start with / contain the visible label text.")
        for st in ctx.get("styledTextCandidates", []):
            add(st, title="Visually styled heading is not marked up as a heading", category="semantics", severity="medium",
                confidence=0.6, wcag_criteria=["1.3.1"],
                screenshot_observation="Large bold text appears to act as a section title." if shot else "",
                description=f"\"{st['text']}\" is rendered at {st['fontSize']} / weight {st['fontWeight']} but is a <{st['tag']}>, not a heading.",
                dom_observation=f"<{st['tag']}> font-size {st['fontSize']}, weight {st['fontWeight']}, not inside any heading element",
                user_impact="Screen-reader users cannot navigate to this section by heading.",
                recommendation="Use an appropriate h1-h6 element and style it with CSS.")
        for f in ctx.get("formControls", []):
            if f.get("placeholder") and not f.get("labelText") and not f.get("ariaLabel"):
                add(f, title="Placeholder used as the only label", category="forms", severity="medium", confidence=0.6,
                    wcag_criteria=["3.3.2"], description=f"The field relies on placeholder \"{f['placeholder']}\" instead of a persistent label.",
                    dom_observation=f"placeholder=\"{f['placeholder']}\"; no <label> or aria-label",
                    user_impact="The hint disappears once typing starts, which hurts users with memory or cognitive disabilities.",
                    recommendation="Add a visible <label> associated with the input.")
                continue
            if f.get("required") and not f.get("describedBy") and f.get("accessibleName") and f["type"] in ("password", "email", "tel"):
                add(f, title="Format or requirement instructions not associated with the field", category="forms", severity="low",
                    confidence=0.4, status="needs_manual_review", verification_method="manual_review", wcag_criteria=["3.3.2"],
                    description=f"Required {f['type']} field \"{f['accessibleName']}\" has no programmatically associated hint.",
                    dom_observation="required=true, aria-describedby empty",
                    recommendation="If a format is expected, state it and link it with aria-describedby.")
        return json.dumps({"findings": out})


def build_provider(s: Settings) -> AIProvider:
    if s.ai_provider == "mock":
        return MockProvider()
    if not s.ai_configured:
        raise ProviderError("AI provider is not configured (missing API key or base URL).")
    return AnthropicProvider(s) if s.ai_provider == "anthropic" else OpenAICompatibleProvider(s)
