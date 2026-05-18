"""
Per-instance HTTP client for MojoVerify (wallet + KYC + identity + comply).

Each ``Client`` carries its own credentials, so a single process can serve
multiple tenants by holding one ``Client`` per group::

    client_a = mojowallet.Client(api_key="key-for-group-a")
    client_b = mojowallet.Client(api_key="key-for-group-b")

    wallet_a = client_a.Wallet.get_by_customer("cust-aaa")
    wallet_b = client_b.Wallet.get_by_customer("cust-bbb")

Generic ``post``/``get``/``delete`` accept a ``prefix`` to route to any
endpoint on the same upstream — wallet, verify, identity, comply, account::

    client.post("ssn/verify", payload={...}, prefix="comply")
    client.get("apikey", prefix="account/group")
"""
import os

import requests
from objict import objict

from .exceptions import (
    AuthError,
    InsufficientBalanceError,
    MojoWalletError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    SessionConflictError,
    WalletLockedError,
)


_DEFAULT_BASE_URL = "https://api.mojoverify.com"
_DEFAULT_TIMEOUT = 30


def _env_fake_mode():
    return os.environ.get("MOJOWALLET_USE_FAKE_OUTBOUND", "").lower() in ("1", "true", "yes")


def _wrap(data):
    if isinstance(data, list):
        return [objict.fromdict(item) if isinstance(item, dict) else item for item in data]
    if isinstance(data, dict):
        return objict.fromdict(data)
    return data


class Client:
    """Holds credentials and routes HTTP calls to the MojoVerify API.

    ``fake_mode`` short-circuits the network and consults responders registered
    via ``register_fake_responder``. Useful for unit tests that exercise the
    full SDK call path without an external server. Reads the
    ``MOJOWALLET_USE_FAKE_OUTBOUND`` env var when ``fake_mode`` is not set
    explicitly.
    """

    def __init__(self, api_key, base_url=None, timeout=_DEFAULT_TIMEOUT, fake_mode=None):
        self.api_key = api_key
        self.base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.fake_mode = _env_fake_mode() if fake_mode is None else bool(fake_mode)
        self._fake_responders = []

    def __repr__(self):
        # never include api_key in repr
        return f"Client(base_url={self.base_url!r}, fake_mode={self.fake_mode})"

    # ── Fake-mode registry ───────────────────────────────────────

    def register_fake_responder(self, matcher, response):
        """Add a responder consulted when ``fake_mode`` is True.

        ``matcher(method, url, payload_or_params) -> bool`` decides match.
        ``response`` is ``{"status_code": int, "body": dict}`` or a callable
        producing that dict. Order matters — first matching responder wins.
        """
        self._fake_responders.append((matcher, response))

    def reset_fake_responders(self):
        self._fake_responders.clear()

    # ── Public verbs ─────────────────────────────────────────────

    def post(self, path, payload=None, prefix="wallet"):
        return self._request("POST", path, json=payload or {}, prefix=prefix)

    def get(self, path, params=None, prefix="wallet"):
        return self._request("GET", path, params=params, prefix=prefix)

    def delete(self, path, prefix="wallet"):
        return self._request("DELETE", path, prefix=prefix)

    # ── Typed accessors ──────────────────────────────────────────

    @property
    def Wallet(self):
        from .wallet import WalletNamespace
        return WalletNamespace(self)

    @property
    def Customer(self):
        from .customer import CustomerNamespace
        return CustomerNamespace(self)

    # ── Internals ────────────────────────────────────────────────

    def _url(self, path, prefix):
        return f"{self.base_url}/api/{prefix}/{path.lstrip('/')}"

    def _headers(self):
        if not self.api_key:
            raise AuthError("Client.api_key is empty — pass api_key to Client()")
        return {
            "Authorization": f"apikey {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method, path, *, json=None, params=None, prefix="wallet"):
        url = self._url(path, prefix)
        if self.fake_mode:
            return self._fake_dispatch(method, url, json if method in ("POST",) else params)

        try:
            resp = requests.request(
                method, url,
                headers=self._headers(),
                json=json if method == "POST" else None,
                params=params if method == "GET" else None,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise MojoWalletError(f"connection error: {exc}", status_code=599)

        return self._parse_response(resp)

    def _fake_dispatch(self, method, url, payload):
        for matcher, response in self._fake_responders:
            try:
                matched = matcher(method, url, payload)
            except Exception:
                matched = False
            if matched:
                resolved = response() if callable(response) else response
                status_code = resolved.get("status_code", 200)
                body = resolved.get("body") or {}
                if status_code >= 400:
                    self._raise_for_status(status_code, body, headers={})
                return self._process_body(body, status_code)
        raise MojoWalletError(
            f"No fake responder matched {method} {url}",
            status_code=599,
        )

    def _parse_response(self, resp):
        self._raise_if_error(resp)
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            return resp.content
        return self._process_body(resp.json(), resp.status_code)

    def _process_body(self, body, status_code):
        # Envelope: {"status": true/false, "data": ...}
        if isinstance(body, dict) and "status" in body:
            if not body["status"]:
                msg = body.get("error") or body.get("message") or "API error"
                raise MojoWalletError(msg, status_code=status_code, code=body.get("code"))
            return _wrap(body.get("data", body))
        return _wrap(body)

    def _raise_if_error(self, resp):
        if resp.status_code < 400:
            return
        try:
            body = resp.json()
        except ValueError:
            body = {}
        self._raise_for_status(resp.status_code, body, resp.headers, raw_text=resp.text)

    def _raise_for_status(self, status_code, body, headers, raw_text=""):
        if status_code == 401:
            raise AuthError("Invalid or expired API key.", status_code=401)
        if status_code == 403:
            msg = (body.get("error") if isinstance(body, dict) else None) or "Permission denied"
            raise PermissionError(msg)
        if status_code == 404:
            raise NotFoundError()
        if status_code == 429:
            retry_after = headers.get("Retry-After") if headers else None
            try:
                retry_after = int(retry_after) if retry_after else None
            except (TypeError, ValueError):
                retry_after = None
            raise RateLimitError(retry_after=retry_after)

        if isinstance(body, dict):
            msg = body.get("error") or body.get("message") or raw_text or f"HTTP {status_code}"
        else:
            msg = raw_text or f"HTTP {status_code}"

        msg_lower = msg.lower() if isinstance(msg, str) else ""
        if "insufficient" in msg_lower and "balance" in msg_lower:
            raise InsufficientBalanceError(msg)
        if "active withdraw session" in msg_lower or "session conflict" in msg_lower:
            raise SessionConflictError(msg)
        if "locked" in msg_lower and "wallet" in msg_lower:
            raise WalletLockedError(msg)
        raise MojoWalletError(msg, status_code=status_code)
