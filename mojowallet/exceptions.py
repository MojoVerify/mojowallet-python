class MojoWalletError(Exception):
    def __init__(self, message, status_code=None, code=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code

    def __repr__(self):
        return f"{self.__class__.__name__}({self.status_code}: {self.message})"


class AuthError(MojoWalletError):
    """Invalid or missing API key."""


class InsufficientBalanceError(MojoWalletError):
    """Wallet balance is too low for the requested operation."""

    def __init__(self, message="Insufficient balance", available=None, required=None):
        super().__init__(message, status_code=400)
        self.available = available
        self.required = required


class SessionConflictError(MojoWalletError):
    """Wallet already has an active withdraw session."""

    def __init__(self, message="Session conflict"):
        super().__init__(message, status_code=400)


class WalletLockedError(MojoWalletError):
    """Wallet is locked and cannot perform operations."""

    def __init__(self, message="Wallet is locked"):
        super().__init__(message, status_code=400)


class RateLimitError(MojoWalletError):
    """Too many requests."""

    def __init__(self, message="Rate limit exceeded", retry_after=None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class NotFoundError(MojoWalletError):
    """Resource not found."""

    def __init__(self, message="Not found"):
        super().__init__(message, status_code=404)


class PermissionError(MojoWalletError):
    """API key lacks required permission."""

    def __init__(self, message="Permission denied"):
        super().__init__(message, status_code=403)
