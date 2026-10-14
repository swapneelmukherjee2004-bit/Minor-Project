import httpx
import pytest

from app.core.logging import redact
from app.services.ai_providers import ProviderError, _post_with_retry


def client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_retries_transient_then_succeeds(monkeypatch):
    calls = []

    def h(req):
        calls.append(1)
        return httpx.Response(503) if len(calls) < 3 else httpx.Response(200, json={"ok": True})
    monkeypatch.setattr("asyncio.sleep", lambda s: _noop())
    async with client(h) as c:
        assert await _post_with_retry(c, "http://x/y", {}, {}, 3) == {"ok": True}
    assert len(calls) == 3


async def _noop():
    return None


async def test_gives_up_after_bounded_retries(monkeypatch):
    calls = []

    def h(req):
        calls.append(1)
        return httpx.Response(429)
    monkeypatch.setattr("asyncio.sleep", lambda s: _noop())
    async with client(h) as c:
        with pytest.raises(ProviderError):
            await _post_with_retry(c, "http://x/y", {}, {}, 2)
    assert len(calls) == 3


async def test_client_error_not_retried_and_body_not_echoed():
    calls = []

    def h(req):
        calls.append(1)
        return httpx.Response(400, text="secret prompt text sk-ABCDEFGH12345")
    async with client(h) as c:
        with pytest.raises(ProviderError) as e:
            await _post_with_retry(c, "http://x/y", {}, {}, 3)
    assert len(calls) == 1 and "secret" not in str(e.value) and "sk-" not in str(e.value)


async def test_timeout_is_retried(monkeypatch):
    calls = []

    def h(req):
        calls.append(1)
        raise httpx.ReadTimeout("t")
    monkeypatch.setattr("asyncio.sleep", lambda s: _noop())
    async with client(h) as c:
        with pytest.raises(ProviderError):
            await _post_with_retry(c, "http://x/y", {}, {}, 1)
    assert len(calls) == 2


def test_log_redaction():
    assert "sk-abcdefghijk" not in redact("key sk-abcdefghijk and Bearer abc.def")
    assert "abc.def" not in redact("Authorization: Bearer abc.def")


def test_provider_config_status():
    from app.core.config import Settings
    assert Settings(ai_provider="anthropic", ai_api_key=None).ai_configured is False
    assert Settings(ai_provider="anthropic", ai_api_key="k").ai_configured is True
    assert Settings(ai_provider="openai_compatible", ai_api_key="k", ai_base_url="").ai_configured is False
    assert Settings(ai_provider="mock").demo_mode is True
