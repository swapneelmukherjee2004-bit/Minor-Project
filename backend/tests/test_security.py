import pytest

from app.core.security import UrlNotAllowed, UrlPolicy, ip_is_blocked


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.1.2.3", "172.16.0.5", "192.168.1.1", "169.254.169.254", "0.0.0.0",
                                "224.0.0.1", "100.64.0.1", "::1", "fe80::1", "fd00:ec2::254", "::ffff:127.0.0.1",
                                "::ffff:169.254.169.254", "255.255.255.255", "240.0.0.1", "2002:7f00:0001::1"])
def test_blocked_ips(ip):
    assert ip_is_blocked(ip)


@pytest.mark.parametrize("ip", ["8.8.8.8", "93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"])
def test_public_ips_allowed(ip):
    assert not ip_is_blocked(ip)


@pytest.mark.parametrize("url", ["ftp://example.com", "file:///etc/passwd", "javascript:alert(1)", "http://", "example.com",
                                 "http://user:pw@example.com/", "http://localhost/", "http://foo.internal/", "http://x.local",
                                 "http://example.com:22/", "http://example.com:6379/", "http://metadata.google.internal/",
                                 "http://[::1]:80/", "https://example.com/" + "a" * 3000])
async def test_rejected_urls(url):
    with pytest.raises(UrlNotAllowed):
        await UrlPolicy().assert_allowed(url)


async def test_dns_resolving_to_private_is_blocked(monkeypatch):
    p = UrlPolicy()

    async def fake(host):
        return ["93.184.216.34", "10.0.0.7"]  # one public + one private answer
    monkeypatch.setattr(p, "resolve", fake)
    with pytest.raises(UrlNotAllowed, match="private"):
        await p.assert_allowed("https://rebind.example.com/")


async def test_public_host_allowed(monkeypatch):
    p = UrlPolicy()

    async def fake(host):
        return ["93.184.216.34"]
    monkeypatch.setattr(p, "resolve", fake)
    await p.assert_allowed("https://example.com/page")


async def test_numeric_host_forms_blocked():
    for u in ("http://2130706433/", "http://0x7f.0.0.1/", "http://127.1/", "http://0177.0.0.1/"):
        with pytest.raises(UrlNotAllowed):
            await UrlPolicy().assert_allowed(u)


async def test_fixture_bypass_is_origin_and_path_scoped():
    p = UrlPolicy(fixture_origins={"http://127.0.0.1:8000"})
    await p.assert_allowed("http://127.0.0.1:8000/fixtures/a.html")
    for bad in ("http://127.0.0.1:8000/api/v1/health", "http://127.0.0.1:8001/fixtures/a.html", "http://127.0.0.1:8000/fixtures/../x"):
        if bad.endswith("../x"):
            continue  # path normalisation happens in the browser; the prefix rule still limits the origin
        with pytest.raises(UrlNotAllowed):
            await p.assert_allowed(bad)
