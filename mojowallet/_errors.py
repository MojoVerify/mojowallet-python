"""Wallet error-code registry + dispatcher.

Mirrors the server-side registry in
``mverify_api/apps/mojopay/wallet/exceptions.py``. Codes are the source of
truth — when the response body carries a 5000-block ``code``, the SDK raises
the matching subclass regardless of HTTP status. Callers consult
``dispatch_wallet_error(body)`` from the response-handling path.
"""
from .exceptions import (
    IdempotentReplayError,
    InsufficientBalanceError,
    InvalidReferenceError,
    WalletInactiveError,
    WalletInvariantError,
    WalletLockedError,
    WalletSuspendedError,
)


WALLET_CODE_REGISTRY = {
    5001: WalletInvariantError,
    5002: InsufficientBalanceError,
    5003: WalletLockedError,
    5004: WalletSuspendedError,
    5005: WalletInactiveError,
    5006: InvalidReferenceError,
    5007: IdempotentReplayError,
}


# Per-class extra fields the dispatcher copies from the body when present.
_EXTRA_FIELDS = {
    InsufficientBalanceError: ("available", "required"),
    WalletSuspendedError:     ("suspended_until",),
}


def dispatch_wallet_error(body):
    """Raise the matching subclass if ``body`` carries a 5000-block ``code``.

    Returns None when no dispatch should happen (body is not a dict, no
    ``code`` key, or ``code`` is outside the registry). Callers handle the
    fallthrough.
    """
    if not isinstance(body, dict):
        return
    code = body.get("code")
    cls = WALLET_CODE_REGISTRY.get(code)
    if cls is None:
        return
    # WalletInvariantError ignores any server-supplied detail.
    if cls is WalletInvariantError:
        raise cls()
    msg = body.get("error") or body.get("message")
    extras = {k: body[k] for k in _EXTRA_FIELDS.get(cls, ()) if k in body}
    raise cls(message=msg, **extras)
