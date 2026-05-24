"""Exception hierarchy for mojowallet-python.

The wallet errors mirror the server-side registry in
``mverify_api/apps/mojopay/wallet/exceptions.py``. Each subclass owns a
numeric ``code`` (5000-block) and a default ``status_code`` as class
attributes. The dispatcher in ``mojowallet._errors`` consults the registry
when a response body carries a ``code`` and raises the matching subclass.

Codes are stable; the REST contract names them. Do not renumber.
"""


class MojoWalletError(Exception):
    """Base for all SDK errors. Subclasses set class-level ``code`` and
    ``status_code``; the constructor falls back to the class attributes when
    callers omit them."""

    code = None
    status_code = None
    default_message = "Wallet error"

    def __init__(self, message=None, status_code=None, code=None):
        msg = message or self.default_message
        super().__init__(msg)
        self.message = msg
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code

    def __repr__(self):
        return f"{self.__class__.__name__}({self.status_code}: {self.message})"


# ── Transport / framework errors (not in 5000-block) ────────────────────

class AuthError(MojoWalletError):
    """Invalid or missing API key."""
    status_code = 401
    default_message = "Authentication failed"


class RateLimitError(MojoWalletError):
    """Too many requests."""
    status_code = 429
    default_message = "Rate limit exceeded"

    def __init__(self, message=None, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class NotFoundError(MojoWalletError):
    """Resource not found."""
    status_code = 404
    default_message = "Not found"


class PermissionError(MojoWalletError):
    """API key lacks required permission."""
    status_code = 403
    default_message = "Permission denied"


class SessionConflictError(MojoWalletError):
    """Wallet already has an active withdraw session."""
    status_code = 400
    default_message = "Session conflict"


# ── Wallet errors (5000-block, mirrors server-side registry) ────────────

class WalletInvariantError(MojoWalletError):
    """A server-side cross-check between two views of the same ledger
    disagreed. The server masks the diff at the REST boundary; the SDK
    reinforces by always surfacing a canned retry message — caller-supplied
    detail is ignored. Callers should ``except WalletInvariantError`` and
    surface a "please retry" UX, never the raw exception text."""
    code = 5001
    status_code = 500
    default_message = "Wallet balance check failed — please retry"

    def __init__(self, message=None):
        # Ignore any caller- or server-supplied message — the canned default
        # is mandatory for this class. See _errors.dispatch_wallet_error.
        super().__init__(message=None)


class InsufficientBalanceError(MojoWalletError):
    """Spend or purchase exceeds available balance."""
    code = 5002
    status_code = 402
    default_message = "Insufficient balance"

    def __init__(self, message=None, available=None, required=None):
        super().__init__(message)
        self.available = available
        self.required = required


class WalletLockedError(MojoWalletError):
    """Wallet is locked — no mutations allowed."""
    code = 5003
    status_code = 423
    default_message = "Wallet is locked"


class WalletSuspendedError(MojoWalletError):
    """Wallet is suspended until a future time — no mutations allowed."""
    code = 5004
    status_code = 423
    default_message = "Wallet is suspended"

    def __init__(self, message=None, suspended_until=None):
        super().__init__(message)
        self.suspended_until = suspended_until


class WalletInactiveError(MojoWalletError):
    """Wallet has been deactivated — no mutations allowed."""
    code = 5005
    status_code = 423
    default_message = "Wallet is inactive"


class InvalidReferenceError(MojoWalletError):
    """``reference_id`` is malformed (missing, contains '#', etc.)."""
    code = 5006
    status_code = 400
    default_message = "Invalid reference_id"


class IdempotentReplayError(MojoWalletError):
    """A replay was detected with the same reference_id but a different
    payload than the original — usually a caller bug."""
    code = 5007
    status_code = 409
    default_message = "Idempotent replay with divergent payload"
