"""Unit tests for the Client class — no API key needed, fake mode only."""

from unittest.mock import patch, MagicMock
import pytest

import mojowallet
from mojowallet._client import Client, _wrap
from mojowallet.exceptions import (
    AuthError,
    MojoWalletError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    InsufficientBalanceError,
    SessionConflictError,
    WalletLockedError,
)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------
class TestClientConstruction:
    def test_default_base_url(self):
        c = Client(api_key="key")
        assert c.base_url == "https://api.mojoverify.com"

    def test_custom_base_url(self):
        c = Client(api_key="key", base_url="https://custom.example.com/")
        assert c.base_url == "https://custom.example.com"

    def test_strips_trailing_slashes(self):
        c = Client(api_key="key", base_url="https://x.com///")
        assert c.base_url == "https://x.com"

    def test_repr_does_not_leak_api_key(self):
        c = Client(api_key="secret-key-do-not-show")
        assert "secret-key" not in repr(c)


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------
class TestHeaders:
    def test_uses_apikey_scheme_not_bearer(self):
        c = Client(api_key="test-key")
        headers = c._headers()
        assert headers["Authorization"] == "apikey test-key"
        assert "Bearer" not in headers["Authorization"]

    def test_raises_when_no_key(self):
        c = Client(api_key="")
        with pytest.raises(AuthError):
            c._headers()

    def test_two_clients_have_independent_keys(self):
        a = Client(api_key="key-a")
        b = Client(api_key="key-b")
        assert a._headers()["Authorization"] == "apikey key-a"
        assert b._headers()["Authorization"] == "apikey key-b"


# ---------------------------------------------------------------------------
# URL building
# ---------------------------------------------------------------------------
class TestUrlBuilding:
    def test_default_prefix_is_wallet(self):
        c = Client(api_key="k", base_url="https://api.example.com")
        assert c._url("wallet/42", prefix="wallet") == "https://api.example.com/api/wallet/wallet/42"

    def test_comply_prefix(self):
        c = Client(api_key="k", base_url="https://api.example.com")
        assert c._url("ssn/verify", prefix="comply") == "https://api.example.com/api/comply/ssn/verify"

    def test_identity_prefix(self):
        c = Client(api_key="k", base_url="https://api.example.com")
        assert c._url("sessions", prefix="identity") == "https://api.example.com/api/identity/sessions"

    def test_nested_prefix(self):
        c = Client(api_key="k", base_url="https://api.example.com")
        assert c._url("apikey", prefix="account/group") == "https://api.example.com/api/account/group/apikey"

    def test_strips_leading_slash_on_path(self):
        c = Client(api_key="k", base_url="https://api.example.com")
        assert c._url("/wallet/42", prefix="wallet") == "https://api.example.com/api/wallet/wallet/42"


# ---------------------------------------------------------------------------
# Fake mode
# ---------------------------------------------------------------------------
class TestFakeMode:
    def test_fake_mode_short_circuits_requests(self):
        """With fake_mode=True, no HTTP call is made."""
        c = Client(api_key="k", fake_mode=True)
        c.register_fake_responder(
            lambda method, url, payload: True,
            {"status_code": 200, "body": {"status": True, "data": {"id": 42}}},
        )
        with patch("mojowallet._client.requests.request") as mock_req:
            result = c.post("wallet/action/1", payload={"action": "test"})
            mock_req.assert_not_called()
        assert result.id == 42

    def test_responder_callable_response(self):
        """Response can be a callable producing the response dict."""
        c = Client(api_key="k", fake_mode=True)
        counter = {"n": 0}

        def make_response():
            counter["n"] += 1
            return {"status_code": 200, "body": {"status": True, "data": {"call": counter["n"]}}}

        c.register_fake_responder(lambda *a: True, make_response)
        r1 = c.post("x")
        r2 = c.post("x")
        assert r1.call == 1
        assert r2.call == 2

    def test_no_matching_responder_raises(self):
        c = Client(api_key="k", fake_mode=True)
        with pytest.raises(MojoWalletError, match="No fake responder matched"):
            c.post("wallet/42")

    def test_fake_mode_envelope_unwrapped(self):
        c = Client(api_key="k", fake_mode=True)
        c.register_fake_responder(
            lambda *a: True,
            {"status_code": 200, "body": {"status": True, "data": {"balance": 5000}}},
        )
        result = c.get("wallet/query/42", params={"q": "balance"})
        assert result.balance == 5000

    def test_fake_mode_envelope_error(self):
        c = Client(api_key="k", fake_mode=True)
        c.register_fake_responder(
            lambda *a: True,
            {"status_code": 200, "body": {"status": False, "error": "Something failed"}},
        )
        with pytest.raises(MojoWalletError, match="Something failed"):
            c.post("wallet/42")

    def test_fake_mode_http_error_status(self):
        c = Client(api_key="k", fake_mode=True)
        c.register_fake_responder(
            lambda *a: True,
            {"status_code": 404, "body": {"error": "Not found"}},
        )
        with pytest.raises(NotFoundError):
            c.get("wallet/999")

    def test_reset_fake_responders(self):
        c = Client(api_key="k", fake_mode=True)
        c.register_fake_responder(lambda *a: True, {"status_code": 200, "body": {}})
        c.reset_fake_responders()
        with pytest.raises(MojoWalletError, match="No fake responder"):
            c.post("x")

    def test_env_var_enables_fake_mode(self, monkeypatch):
        monkeypatch.setenv("MOJOWALLET_USE_FAKE_OUTBOUND", "true")
        c = Client(api_key="k")
        assert c.fake_mode is True

    def test_env_var_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("MOJOWALLET_USE_FAKE_OUTBOUND", raising=False)
        c = Client(api_key="k")
        assert c.fake_mode is False

    def test_explicit_fake_mode_overrides_env(self, monkeypatch):
        monkeypatch.setenv("MOJOWALLET_USE_FAKE_OUTBOUND", "true")
        c = Client(api_key="k", fake_mode=False)
        assert c.fake_mode is False


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------
class TestErrorMapping:
    def _client_with(self, status_code, body):
        c = Client(api_key="k", fake_mode=True)
        c.register_fake_responder(lambda *a: True, {"status_code": status_code, "body": body})
        return c

    def test_401_raises_auth_error(self):
        c = self._client_with(401, {"error": "bad"})
        with pytest.raises(AuthError):
            c.get("x")

    def test_403_raises_permission_error(self):
        c = self._client_with(403, {"error": "Forbidden"})
        with pytest.raises(PermissionError):
            c.get("x")

    def test_404_raises_not_found(self):
        c = self._client_with(404, {})
        with pytest.raises(NotFoundError):
            c.get("x")

    def test_400_insufficient_balance(self):
        c = self._client_with(400, {"error": "Insufficient balance for withdrawal"})
        with pytest.raises(InsufficientBalanceError):
            c.post("x")

    def test_400_session_conflict(self):
        c = self._client_with(400, {"error": "Wallet already has an active withdraw session"})
        with pytest.raises(SessionConflictError):
            c.post("x")

    def test_400_wallet_locked(self):
        c = self._client_with(400, {"error": "Wallet is locked"})
        with pytest.raises(WalletLockedError):
            c.post("x")

    def test_500_raises_generic_error(self):
        c = self._client_with(500, {"error": "Server error"})
        with pytest.raises(MojoWalletError):
            c.get("x")


# ---------------------------------------------------------------------------
# Real-mode wiring (mocking the requests layer)
# ---------------------------------------------------------------------------
class TestRealMode:
    def _mock_resp(self, status_code, json_body, content_type="application/json"):
        resp = MagicMock()
        resp.status_code = status_code
        resp.headers = {"Content-Type": content_type}
        resp.json.return_value = json_body
        resp.text = ""
        return resp

    @patch("mojowallet._client.requests.request")
    def test_post_sends_apikey_header(self, mock_req):
        mock_req.return_value = self._mock_resp(200, {"status": True, "data": {"id": 1}})
        c = Client(api_key="test-key", base_url="https://api.example.com")
        result = c.post("wallet/action/42", payload={"action": "test"})

        mock_req.assert_called_once()
        kwargs = mock_req.call_args[1]
        assert kwargs["headers"]["Authorization"] == "apikey test-key"
        assert kwargs["json"] == {"action": "test"}
        assert result.id == 1

    @patch("mojowallet._client.requests.request")
    def test_get_uses_params_not_json(self, mock_req):
        mock_req.return_value = self._mock_resp(200, {"status": True, "data": {"balance": 100}})
        c = Client(api_key="key", base_url="https://api.example.com")
        c.get("wallet/query/42", params={"q": "balance"})

        kwargs = mock_req.call_args[1]
        assert kwargs["params"] == {"q": "balance"}
        assert kwargs["json"] is None

    @patch("mojowallet._client.requests.request")
    def test_two_clients_send_different_keys(self, mock_req):
        mock_req.return_value = self._mock_resp(200, {"status": True, "data": {}})
        a = Client(api_key="key-a", base_url="https://api.example.com")
        b = Client(api_key="key-b", base_url="https://api.example.com")

        a.get("x")
        b.get("x")

        first_call_headers = mock_req.call_args_list[0][1]["headers"]
        second_call_headers = mock_req.call_args_list[1][1]["headers"]
        assert first_call_headers["Authorization"] == "apikey key-a"
        assert second_call_headers["Authorization"] == "apikey key-b"

    @patch("mojowallet._client.requests.request")
    def test_url_built_correctly(self, mock_req):
        mock_req.return_value = self._mock_resp(200, {"status": True, "data": {}})
        c = Client(api_key="k", base_url="https://api.example.com")
        c.post("ssn/verify", payload={}, prefix="comply")

        args = mock_req.call_args
        assert args[0][1] == "https://api.example.com/api/comply/ssn/verify"


# ---------------------------------------------------------------------------
# _wrap
# ---------------------------------------------------------------------------
class TestWrap:
    def test_wraps_dict(self):
        result = _wrap({"id": 1, "name": "test"})
        assert result.id == 1
        assert result.name == "test"

    def test_wraps_list(self):
        result = _wrap([{"id": 1}, {"id": 2}])
        assert len(result) == 2
        assert result[0].id == 1

    def test_passes_through_primitives(self):
        assert _wrap(42) == 42
        assert _wrap("hello") == "hello"


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------
class TestExports:
    def test_client_exported(self):
        assert mojowallet.Client is Client

    def test_configure_removed(self):
        assert not hasattr(mojowallet, "configure")
