"""Unit tests for exception hierarchy."""

import pytest
from mojowallet.exceptions import (
    MojoWalletError,
    AuthError,
    IdempotentReplayError,
    InsufficientBalanceError,
    InvalidReferenceError,
    SessionConflictError,
    WalletInactiveError,
    WalletInvariantError,
    WalletLockedError,
    WalletSuspendedError,
    RateLimitError,
    NotFoundError,
    PermissionError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_base(self):
        for exc_cls in [AuthError, IdempotentReplayError, InsufficientBalanceError,
                        InvalidReferenceError, SessionConflictError, WalletInactiveError,
                        WalletInvariantError, WalletLockedError, WalletSuspendedError,
                        RateLimitError, NotFoundError, PermissionError]:
            assert issubclass(exc_cls, MojoWalletError), \
                f"{exc_cls.__name__} must inherit from MojoWalletError"

    def test_base_error_attributes(self):
        e = MojoWalletError("test error", status_code=400, code=4242)
        assert e.message == "test error", "message attr set"
        assert e.status_code == 400, "status_code attr set"
        assert e.code == 4242, "code attr set"
        assert str(e) == "test error", "str() returns the message"

    def test_base_error_uses_default_message_when_omitted(self):
        e = MojoWalletError()
        assert e.message == "Wallet error", "base default_message kicks in"

    def test_auth_error(self):
        e = AuthError("bad key")
        assert e.status_code == 401, "AuthError defaults to 401"

    def test_auth_error_status_override(self):
        e = AuthError("bad key", status_code=499)
        assert e.status_code == 499, "explicit status_code overrides class default"

    def test_insufficient_balance_error(self):
        e = InsufficientBalanceError(available=100, required=500)
        assert e.available == 100, "available kwarg set"
        assert e.required == 500, "required kwarg set"
        assert e.status_code == 402, "InsufficientBalanceError now uses HTTP 402 (was 400)"
        assert e.code == 5002, "InsufficientBalanceError code is 5002"
        assert e.message == "Insufficient balance", "default message preserved"

    def test_session_conflict_error(self):
        e = SessionConflictError("already exists")
        assert e.status_code == 400, "SessionConflictError stays 400 (transport-level error)"

    def test_wallet_locked_error(self):
        e = WalletLockedError()
        assert e.status_code == 423, "WalletLockedError now uses HTTP 423 (was 400)"
        assert e.code == 5003, "WalletLockedError code is 5003"

    def test_wallet_invariant_error_uses_canned_message(self):
        e = WalletInvariantError()
        assert e.code == 5001, "WalletInvariantError code is 5001"
        assert e.status_code == 500, "WalletInvariantError uses HTTP 500"
        assert "retry" in e.message.lower(), "canned retry message expected"

    def test_wallet_invariant_error_ignores_caller_message(self):
        """Safety-critical: caller-supplied detail must never override the canned message."""
        e = WalletInvariantError(message="internal diff: SC_REAL mismatch")
        assert "diff" not in e.message, "server detail must be suppressed"
        assert "retry" in e.message.lower(), "canned message must remain"

    def test_wallet_suspended_error(self):
        e = WalletSuspendedError(suspended_until="2026-06-01T00:00:00Z")
        assert e.code == 5004, "WalletSuspendedError code is 5004"
        assert e.status_code == 423, "WalletSuspendedError uses HTTP 423"
        assert e.suspended_until == "2026-06-01T00:00:00Z", "suspended_until kwarg accepted"

    def test_wallet_inactive_error(self):
        e = WalletInactiveError()
        assert e.code == 5005, "WalletInactiveError code is 5005"
        assert e.status_code == 423, "WalletInactiveError uses HTTP 423"

    def test_invalid_reference_error(self):
        e = InvalidReferenceError("bad ref")
        assert e.code == 5006, "InvalidReferenceError code is 5006"
        assert e.status_code == 400, "InvalidReferenceError uses HTTP 400"

    def test_idempotent_replay_error(self):
        e = IdempotentReplayError()
        assert e.code == 5007, "IdempotentReplayError code is 5007"
        assert e.status_code == 409, "IdempotentReplayError uses HTTP 409"

    def test_rate_limit_error(self):
        e = RateLimitError(retry_after=60)
        assert e.retry_after == 60, "retry_after kwarg set"
        assert e.status_code == 429, "RateLimitError uses HTTP 429"

    def test_not_found_error(self):
        e = NotFoundError()
        assert e.status_code == 404, "NotFoundError uses HTTP 404"

    def test_permission_error(self):
        e = PermissionError()
        assert e.status_code == 403, "PermissionError uses HTTP 403"

    def test_repr(self):
        e = MojoWalletError("test", status_code=400)
        assert "400" in repr(e), "repr includes status_code"
        assert "test" in repr(e), "repr includes message"
