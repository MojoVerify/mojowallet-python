"""Unit tests for _client.py — no API key needed, all mocked."""

from unittest.mock import patch, MagicMock
import pytest

from mojowallet import _client
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
# configure()
# ---------------------------------------------------------------------------
class TestConfigure:
    def setup_method(self):
        self._original = dict(_client._state)

    def teardown_method(self):
        _client._state.update(self._original)

    def test_configure_sets_api_key(self):
        _client.configure("test-key-123")
        assert _client._state["api_key"] == "test-key-123"

    def test_configure_sets_base_url(self):
        _client.configure("key", base_url="https://custom.example.com/")
        assert _client._state["base_url"] == "https://custom.example.com"

    def test_configure_strips_trailing_slash(self):
        _client.configure("key", base_url="https://example.com///")
        assert _client._state["base_url"] == "https://example.com"

    def test_configure_keeps_default_url_when_none(self):
        _client.configure("key")
        assert _client._state["base_url"] == _client._DEFAULT_BASE_URL


# ---------------------------------------------------------------------------
# _get_headers()
# ---------------------------------------------------------------------------
class TestGetHeaders:
    def setup_method(self):
        self._original = dict(_client._state)

    def teardown_method(self):
        _client._state.update(self._original)

    def test_raises_auth_error_when_no_key(self):
        _client._state["api_key"] = None
        with pytest.raises(AuthError):
            _client._get_headers()

    def test_returns_correct_headers(self):
        _client._state["api_key"] = "test-key"
        headers = _client._get_headers()
        assert headers["Authorization"] == "apikey test-key"
        assert headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# _url()
# ---------------------------------------------------------------------------
class TestUrl:
    def setup_method(self):
        self._original = dict(_client._state)
        _client._state["base_url"] = "https://api.example.com"

    def teardown_method(self):
        _client._state.update(self._original)

    def test_builds_url(self):
        assert _client._url("wallet/42") == "https://api.example.com/api/wallet/wallet/42"

    def test_strips_leading_slash(self):
        assert _client._url("/wallet/42") == "https://api.example.com/api/wallet/wallet/42"


# ---------------------------------------------------------------------------
# _wrap()
# ---------------------------------------------------------------------------
class TestWrap:
    def test_wraps_dict(self):
        result = _client._wrap({"id": 1, "name": "test"})
        assert result.id == 1
        assert result.name == "test"

    def test_wraps_list(self):
        result = _client._wrap([{"id": 1}, {"id": 2}])
        assert len(result) == 2
        assert result[0].id == 1

    def test_passes_through_primitives(self):
        assert _client._wrap(42) == 42
        assert _client._wrap("hello") == "hello"


# ---------------------------------------------------------------------------
# _raise_for_response()
# ---------------------------------------------------------------------------
class TestRaiseForResponse:
    def _mock_response(self, status_code, json_data=None, text="", headers=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        resp.headers = headers or {}
        if json_data is not None:
            resp.json.return_value = json_data
        else:
            resp.json.side_effect = ValueError("No JSON")
        return resp

    def test_401_raises_auth_error(self):
        with pytest.raises(AuthError):
            _client._raise_for_response(self._mock_response(401))

    def test_403_raises_permission_error(self):
        with pytest.raises(PermissionError):
            _client._raise_for_response(self._mock_response(403, {"error": "Forbidden"}))

    def test_404_raises_not_found(self):
        with pytest.raises(NotFoundError):
            _client._raise_for_response(self._mock_response(404))

    def test_429_raises_rate_limit(self):
        with pytest.raises(RateLimitError):
            _client._raise_for_response(self._mock_response(429, headers={"Retry-After": "30"}))

    def test_429_captures_retry_after(self):
        try:
            _client._raise_for_response(self._mock_response(429, headers={"Retry-After": "30"}))
        except RateLimitError as e:
            assert e.retry_after == 30

    def test_400_insufficient_balance(self):
        resp = self._mock_response(400, {"error": "Insufficient balance for withdrawal"})
        with pytest.raises(InsufficientBalanceError):
            _client._raise_for_response(resp)

    def test_400_session_conflict(self):
        resp = self._mock_response(400, {"error": "Wallet already has an active withdraw session"})
        with pytest.raises(SessionConflictError):
            _client._raise_for_response(resp)

    def test_400_wallet_locked(self):
        resp = self._mock_response(400, {"error": "Wallet is locked"})
        with pytest.raises(WalletLockedError):
            _client._raise_for_response(resp)

    def test_500_raises_generic_error(self):
        with pytest.raises(MojoWalletError):
            _client._raise_for_response(self._mock_response(500, {"error": "Server error"}))

    def test_200_does_not_raise(self):
        _client._raise_for_response(self._mock_response(200))


# ---------------------------------------------------------------------------
# _parse()
# ---------------------------------------------------------------------------
class TestParse:
    def _mock_response(self, status_code, json_data=None, content_type="application/json"):
        resp = MagicMock()
        resp.status_code = status_code
        resp.headers = {"Content-Type": content_type}
        resp.text = ""
        if json_data is not None:
            resp.json.return_value = json_data
        return resp

    def test_unwraps_envelope(self):
        resp = self._mock_response(200, {"status": True, "data": {"id": 42, "name": "Test"}})
        result = _client._parse(resp)
        assert result.id == 42
        assert result.name == "Test"

    def test_raises_on_false_status(self):
        resp = self._mock_response(200, {"status": False, "error": "Something failed"})
        with pytest.raises(MojoWalletError, match="Something failed"):
            _client._parse(resp)

    def test_handles_list_response(self):
        resp = self._mock_response(200, {"status": True, "data": [{"id": 1}, {"id": 2}]})
        result = _client._parse(resp)
        assert len(result) == 2
        assert result[0].id == 1

    def test_returns_bytes_for_non_json(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/pdf"}
        resp.text = ""
        resp.content = b"PDF-content"
        result = _client._parse(resp)
        assert result == b"PDF-content"


# ---------------------------------------------------------------------------
# post() / get()
# ---------------------------------------------------------------------------
class TestRequests:
    def setup_method(self):
        self._original = dict(_client._state)
        _client._state["api_key"] = "test-key"
        _client._state["base_url"] = "https://api.example.com"

    def teardown_method(self):
        _client._state.update(self._original)

    @patch("mojowallet._client.requests.post")
    def test_post_sends_correct_request(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.json.return_value = {"status": True, "data": {"id": 1}}
        mock_resp.text = ""
        mock_post.return_value = mock_resp

        result = _client.post("wallet/action/42", payload={"action": "add_funds", "amount": 1000})

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.example.com/api/wallet/wallet/action/42"
        assert call_args[1]["json"] == {"action": "add_funds", "amount": 1000}
        assert result.id == 1

    @patch("mojowallet._client.requests.get")
    def test_get_sends_correct_request(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.json.return_value = {"status": True, "data": {"balance": 5000}}
        mock_resp.text = ""
        mock_get.return_value = mock_resp

        result = _client.get("wallet/query/42", params={"q": "balance", "currency_code": "SC_REAL"})

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://api.example.com/api/wallet/wallet/query/42"
        assert call_args[1]["params"] == {"q": "balance", "currency_code": "SC_REAL"}
        assert result.balance == 5000
