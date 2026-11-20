"""Outbound URL policy for local clients and the authenticated loopback API."""

import ipaddress
import socket
from urllib.parse import urlsplit, urljoin
import requests


class PublicAddressAdapter(requests.adapters.HTTPAdapter):
    """Pin the socket to the validated DNS answer while preserving TLS SNI."""

    def __init__(self, allow_local=False):
        self.allow_local = allow_local
        super().__init__()

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        p = urlsplit(request.url)
        check_public(request.url, self.allow_local)
        addresses = socket.getaddrinfo(
            p.hostname,
            p.port or (443 if p.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
        if not self.allow_local and any(
            not ipaddress.ip_address(a[4][0]).is_global for a in addresses
        ):
            raise ValueError("Unsafe DNS answer")
        selected = next((a for a in addresses if a[0] == socket.AF_INET), addresses[0])[
            4
        ][0]
        host_params, pool_kwargs = self.build_connection_pool_key_attributes(
            request, verify, cert
        )
        host_params["host"] = selected
        if p.scheme == "https":
            pool_kwargs.update(assert_hostname=p.hostname, server_hostname=p.hostname)
        request.headers["Host"] = p.netloc
        return self.poolmanager.connection_from_host(
            **host_params, pool_kwargs=pool_kwargs
        )


def check_public(url: str, allow_local: bool = False) -> None:
    p = urlsplit(url)
    if (
        p.scheme not in ("http", "https")
        or not p.hostname
        or p.username
        or p.password
        or "\\" in url
        or any(ord(c) < 32 for c in url)
    ):
        raise ValueError("Invalid HTTP(S) URL")
    if allow_local:
        return
    if p.port not in (None, 80, 443):
        raise ValueError("Only standard public web ports are supported")
    addresses = socket.getaddrinfo(
        p.hostname,
        p.port or (443 if p.scheme == "https" else 80),
        type=socket.SOCK_STREAM,
    )
    if not addresses or any(
        not ipaddress.ip_address(a[4][0]).is_global for a in addresses
    ):
        raise ValueError(
            "Private, loopback, link-local and reserved network targets are blocked"
        )


def get_public(url: str, *, allow_local=False, **kwargs):
    """Validate each redirect, disable ambient proxies and retain no cookie store."""
    session = requests.Session()
    session.trust_env = False
    adapter = PublicAddressAdapter(allow_local)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    for _ in range(6):
        check_public(url, allow_local)
        response = session.get(url, allow_redirects=False, **kwargs)
        if response.status_code in (301, 302, 303, 307, 308):
            next_url = urljoin(url, response.headers.get("Location", ""))
            response.close()
            if urlsplit(url).scheme == "https" and urlsplit(next_url).scheme != "https":
                raise ValueError("HTTPS downgrade blocked")
            url = next_url
        else:
            return response
    session.close()
    raise ValueError("Too many redirects")
