import requests
from objict import objict

from .exceptions import (
    AuthError,
    MojoWalletError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    InsufficientBalanceError,
    SessionConflictError,
    WalletLockedError,
)

_DEFAULT_BASE_URL = "https://api.mojowallet.com"

_state = {
    "api_key": None,
    "base_url": _DEFAULT_BASE_URL,
}


def configure(api_key, base_url=None):
    _state["api_key"] = api_key
    if base_url:
        _state["base_url"] = base_url.rstrip("/")


def _get_headers():
    if not _state["api_key"]:
        raise AuthError("Call mojowallet.configure(api_key) before making requests.")
    return {
        "Authorization": f"apikey {_state['api_key']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _url(path, prefix="wallet"):
    return f"{_state['base_url']}/api/{prefix}/{path.lstrip('/')}"


def _wrap(data):
    if isinstance(data, list):
        return [objict.fromdict(item) if isinstance(item, dict) else item for item in data]
    if isinstance(data, dict):
        return objict.fromdict(data)
    return data


def _raise_for_response(http_resp):
    status_code = http_resp.status_code

    if status_code == 401:
        raise AuthError("Invalid or expired API key.", status_code=401)
    if status_code == 403:
        try:
            body = http_resp.json()
            msg = body.get("error") or body.get("message") or "Permission denied"
        except Exception:
            msg = "Permission denied"
        raise PermissionError(msg)
    if status_code == 404:
        raise NotFoundError()
    if status_code == 429:
        retry_after = http_resp.headers.get("Retry-After")
        raise RateLimitError(retry_after=int(retry_after) if retry_after else None)
    if status_code >= 400:
        try:
            body = http_resp.json()
            msg = body.get("error") or body.get("message") or http_resp.text
        except Exception:
            msg = http_resp.text or f"HTTP {status_code}"

        # Map known error messages to specific exceptions
        msg_lower = msg.lower() if isinstance(msg, str) else ""
        if "insufficient" in msg_lower and "balance" in msg_lower:
            raise InsufficientBalanceError(msg)
        if "active withdraw session" in msg_lower or "session conflict" in msg_lower:
            raise SessionConflictError(msg)
        if "locked" in msg_lower and "wallet" in msg_lower:
            raise WalletLockedError(msg)

        raise MojoWalletError(msg, status_code=status_code)


def _parse(http_resp):
    _raise_for_response(http_resp)

    content_type = http_resp.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        return http_resp.content

    body = http_resp.json()

    # Envelope: {"status": true/false, "data": ...}
    if isinstance(body, dict) and "status" in body:
        if not body["status"]:
            msg = body.get("error") or body.get("message") or "API error"
            code = body.get("code")
            raise MojoWalletError(msg, status_code=http_resp.status_code, code=code)
        return _wrap(body.get("data", body))

    return _wrap(body)


def post(path, payload=None, prefix="wallet"):
    resp = requests.post(
        _url(path, prefix=prefix),
        json=payload or {},
        headers=_get_headers(),
        timeout=30,
    )
    return _parse(resp)


def get(path, params=None, prefix="wallet"):
    resp = requests.get(
        _url(path, prefix=prefix),
        params=params,
        headers=_get_headers(),
        timeout=30,
    )
    return _parse(resp)
