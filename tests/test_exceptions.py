"""Unit tests for exception hierarchy."""

import pytest
from mojowallet.exceptions import (
    MojoWalletError,
    AuthError,
    InsufficientBalanceError,
    SessionConflictError,
    WalletLockedError,
    RateLimitError,
    NotFoundError,
    PermissionError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_base(self):
        for exc_cls in [AuthError, InsufficientBalanceError, SessionConflictError,
                        WalletLockedError, RateLimitError, NotFoundError, PermissionError]:
            assert issubclass(exc_cls, MojoWalletError)

    def test_base_error_attributes(self):
        e = MojoWalletError("test error", status_code=400, code="BAD_REQUEST")
        assert e.message == "test error"
        assert e.status_code == 400
        assert e.code == "BAD_REQUEST"
        assert str(e) == "test error"

    def test_auth_error(self):
        e = AuthError("bad key", status_code=401)
        assert e.status_code == 401

    def test_insufficient_balance_error(self):
        e = InsufficientBalanceError(available=100, required=500)
        assert e.available == 100
        assert e.required == 500
        assert e.status_code == 400

    def test_session_conflict_error(self):
        e = SessionConflictError("already exists")
        assert e.status_code == 400

    def test_wallet_locked_error(self):
        e = WalletLockedError()
        assert e.status_code == 400

    def test_rate_limit_error(self):
        e = RateLimitError(retry_after=60)
        assert e.retry_after == 60
        assert e.status_code == 429

    def test_not_found_error(self):
        e = NotFoundError()
        assert e.status_code == 404

    def test_permission_error(self):
        e = PermissionError()
        assert e.status_code == 403

    def test_repr(self):
        e = MojoWalletError("test", status_code=400)
        assert "400" in repr(e)
        assert "test" in repr(e)
