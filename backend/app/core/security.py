"""SSRF protection: URL validation, DNS resolution checks, fixture allow-list."""
import asyncio
import ipaddress
import socket
from dataclasses import dataclass, field
from urllib.parse import urlsplit

ALLOWED_PORTS = {80, 443, 8080, 8443}
FIXTURE_PATH_PREFIX = "/fixtures/"
_CGNAT = ipaddress.ip_network("100.64.0.0/10")
_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal", "metadata"}
_BLOCKED_SUFFIXES = (".local", ".internal", ".localhost", ".localdomain", ".lan")


class UrlNotAllowed(ValueError):
    """Raised when a URL fails the SSRF policy. Message is safe to show to users."""


def ip_is_blocked(ip: str | ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    addr = ipaddress.ip_address(ip) if isinstance(ip, str) else ip
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    if isinstance(addr, ipaddress.IPv6Address) and addr.sixtofour:
        addr = addr.sixtofour
    return (
        addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast
        or addr.is_reserved or addr.is_unspecified or getattr(addr, "is_site_local", False)
        or (isinstance(addr, ipaddress.IPv4Address) and addr in _CGNAT)
        or not addr.is_global
    )


@dataclass
class UrlPolicy:
    """Policy for outbound URLs. `fixture_origins` bypasses only for /fixtures/ paths."""
    fixture_origins: set[str] = field(default_factory=set)
    _dns_cache: dict[str, list[str]] = field(default_factory=dict)

    def is_fixture_url(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}".lower()
        return origin in self.fixture_origins and parts.path.startswith(FIXTURE_PATH_PREFIX)

    def check_syntax(self, url: str) -> None:
        if not url or len(url) > 2048:
            raise UrlNotAllowed("URL is empty or longer than 2048 characters.")
        try:
            parts = urlsplit(url.strip())
            port = parts.port
        except ValueError:
            raise UrlNotAllowed("URL is malformed.") from None
        if parts.scheme not in ("http", "https"):
            raise UrlNotAllowed("Only http:// and https:// URLs are allowed.")
        if not parts.hostname:
            raise UrlNotAllowed("URL must include a host name.")
        if parts.username or parts.password:
            raise UrlNotAllowed("URLs containing credentials are not allowed.")
        if self.is_fixture_url(url):
            return
        effective = port or (443 if parts.scheme == "https" else 80)
        if effective not in ALLOWED_PORTS:
            raise UrlNotAllowed(f"Port {effective} is not allowed (allowed: {sorted(ALLOWED_PORTS)}).")
        host = parts.hostname.lower().rstrip(".")
        if host in _BLOCKED_HOSTNAMES or host.endswith(_BLOCKED_SUFFIXES):
            raise UrlNotAllowed("This host name is not allowed.")

    async def resolve(self, host: str) -> list[str]:
        if host in self._dns_cache:
            return self._dns_cache[host]
        loop = asyncio.get_running_loop()
        try:
            infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise UrlNotAllowed("Host name could not be resolved.") from None
        ips = sorted({i[4][0].split("%")[0] for i in infos})
        if not ips:
            raise UrlNotAllowed("Host name could not be resolved.")
        self._dns_cache[host] = ips
        return ips

    async def assert_allowed(self, url: str) -> None:
        """Validate syntax and that every resolved address is publicly routable."""
        self.check_syntax(url)
        if self.is_fixture_url(url):
            return
        host = urlsplit(url).hostname or ""
        ips = await self.resolve(host)
        for ip in ips:
            if ip_is_blocked(ip):
                raise UrlNotAllowed("This host resolves to a private or reserved network address, which is blocked.")
