"""Unit tests for Session class — mocked, no API key needed."""

from unittest.mock import patch, MagicMock, call
import pytest
from objict import objict

from mojowallet.wallet import Wallet
from mojowallet.session import Session
from mojowallet import _client


@pytest.fixture(autouse=True)
def reset_state():
    original = dict(_client._state)
    _client._state["api_key"] = "test-key"
    _client._state["base_url"] = "https://api.example.com"
    yield
    _client._state.update(original)


def _wallet_data():
    return objict(id=42, uuid="wlt-abc123", name="Main Wallet",
                  is_active=True, is_locked=False)


def _session_data():
    return objict(id=10, uuid="sess-abc123", session_id="game-xyz")


class TestSessionWithdraw:
    @patch("mojowallet._client.post")
    def test_withdraw_sends_correct_request(self, mock_post):
        mock_post.return_value = objict(id=1, status="COMPLETED")
        w = Wallet(_wallet_data())
        s = Session(_session_data(), w)

        s.withdraw(500, "SC_REAL", reference_id="bet-001")

        mock_post.assert_called_once_with(
            "wallet/action/42",
            payload={"action": "withdraw", "amount_units": 500,
                     "currency_code": "SC_REAL", "session_id": "game-xyz",
                     "reference_id": "bet-001"},
        )


class TestSessionExtend:
    @patch("mojowallet._client.post")
    def test_extend(self, mock_post):
        mock_post.return_value = objict(expires_at="2025-01-01T00:30:00Z")
        w = Wallet(_wallet_data())
        s = Session(_session_data(), w)

        s.extend(1800)
        mock_post.assert_called_once_with(
            "session/10",
            payload={"extend": {"duration": 1800}},
        )


class TestSessionClose:
    @patch("mojowallet._client.post")
    def test_close(self, mock_post):
        mock_post.return_value = objict(is_active=False)
        w = Wallet(_wallet_data())
        s = Session(_session_data(), w)

        s.close()
        mock_post.assert_called_once_with(
            "session/10",
            payload={"close": True},
        )
        assert s._closed is True

    @patch("mojowallet._client.post")
    def test_close_is_idempotent(self, mock_post):
        mock_post.return_value = objict(is_active=False)
        w = Wallet(_wallet_data())
        s = Session(_session_data(), w)

        s.close()
        s.close()
        assert mock_post.call_count == 1


class TestSessionContextManager:
    @patch("mojowallet._client.post")
    def test_context_manager_closes_on_exit(self, mock_post):
        # First call: start_session, second call: close
        mock_post.side_effect = [
            objict(id=10, uuid="sess-abc", session_id="game-xyz"),
            objict(is_active=False),
        ]

        w = Wallet(_wallet_data())

        with w.session("game-xyz") as s:
            assert s.session_id == "game-xyz"

        assert mock_post.call_count == 2
        # Second call should be close
        mock_post.assert_called_with(
            "session/10",
            payload={"close": True},
        )

    @patch("mojowallet._client.post")
    def test_context_manager_closes_on_exception(self, mock_post):
        mock_post.side_effect = [
            objict(id=10, uuid="sess-abc", session_id="game-xyz"),
            objict(is_active=False),
        ]

        w = Wallet(_wallet_data())

        with pytest.raises(ValueError):
            with w.session("game-xyz") as s:
                raise ValueError("test error")

        # close should still be called (2 calls total: start + close)
        assert mock_post.call_count == 2


class TestSessionRepr:
    def test_repr_active(self):
        w = Wallet(_wallet_data())
        s = Session(_session_data(), w)
        assert "active" in repr(s)
        assert "game-xyz" in repr(s)

    def test_repr_closed(self):
        w = Wallet(_wallet_data())
        s = Session(_session_data(), w)
        s._closed = True
        assert "closed" in repr(s)
