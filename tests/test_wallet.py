"""Unit tests for Wallet class — mocked, no API key needed."""

from unittest.mock import patch, MagicMock
import pytest
from objict import objict

from mojowallet.wallet import Wallet
from mojowallet import _client


@pytest.fixture(autouse=True)
def reset_state():
    original = dict(_client._state)
    _client._state["api_key"] = "test-key"
    _client._state["base_url"] = "https://api.example.com"
    yield
    _client._state.update(original)


def _wallet_data(**overrides):
    data = objict(id=42, uuid="wlt-abc123", name="Main Wallet",
                  is_active=True, is_locked=False)
    data.update(overrides)
    return data


class TestWalletGet:
    @patch("mojowallet.wallet._client.get")
    def test_get_returns_wallet(self, mock_get):
        mock_get.return_value = _wallet_data()
        w = Wallet.get(42)
        assert w.id == 42
        assert w.uuid == "wlt-abc123"
        assert w.name == "Main Wallet"
        mock_get.assert_called_once_with("wallet/42")

    @patch("mojowallet.wallet._client.get")
    def test_get_by_customer(self, mock_get):
        mock_get.return_value = _wallet_data()
        w = Wallet.get_by_customer("cust-abc123")
        assert w.id == 42
        assert w.name == "Main Wallet"
        mock_get.assert_called_once_with("wallet/cust-abc123")


class TestWalletActions:
    def _make_wallet(self):
        return Wallet(_wallet_data())

    @patch("mojowallet.wallet._client.post")
    def test_add_funds(self, mock_post):
        mock_post.return_value = objict(id=1, status="COMPLETED")
        w = self._make_wallet()
        result = w.add_funds(1000, "SC_REAL", source="CREDIT_CARD")
        mock_post.assert_called_once_with(
            "wallet/action/42",
            payload={"action": "add_funds", "amount_units": 1000,
                     "currency_code": "SC_REAL", "source": "CREDIT_CARD"},
        )

    @patch("mojowallet.wallet._client.post")
    def test_purchase(self, mock_post):
        mock_post.return_value = objict(id=2, status="COMPLETED")
        w = self._make_wallet()
        w.purchase(500, "SC_REAL", merchant="Coffee Shop")
        mock_post.assert_called_once_with(
            "wallet/action/42",
            payload={"action": "purchase", "amount_units": 500,
                     "currency_code": "SC_REAL", "merchant": "Coffee Shop"},
        )

    @patch("mojowallet.wallet._client.post")
    def test_cashout(self, mock_post):
        mock_post.return_value = objict(id=3, status="COMPLETED")
        w = self._make_wallet()
        w.cashout(800, "SC_REAL", reference_id="cashout-001")
        mock_post.assert_called_once_with(
            "wallet/action/42",
            payload={"action": "cashout", "amount_units": 800,
                     "currency_code": "SC_REAL", "reference_id": "cashout-001"},
        )

    @patch("mojowallet.wallet._client.post")
    def test_reserve(self, mock_post):
        mock_post.return_value = objict(id=4, status="COMPLETED")
        w = self._make_wallet()
        w.reserve(2500, "SC_REAL", "SC_HOLD", "payout-001")
        mock_post.assert_called_once_with(
            "wallet/action/42",
            payload={"action": "reserve", "amount_units": 2500,
                     "currency_code": "SC_REAL", "hold_currency_code": "SC_HOLD",
                     "reference_id": "payout-001"},
        )

    @patch("mojowallet.wallet._client.post")
    def test_confirm_reservation(self, mock_post):
        mock_post.return_value = objict(status="COMPLETED")
        w = self._make_wallet()
        w.confirm_reservation("payout-001")
        mock_post.assert_called_once_with(
            "wallet/action/42",
            payload={"action": "confirm_reservation", "reference_id": "payout-001"},
        )

    @patch("mojowallet.wallet._client.post")
    def test_release_reservation(self, mock_post):
        mock_post.return_value = objict(status="RELEASED")
        w = self._make_wallet()
        w.release_reservation("payout-001")
        mock_post.assert_called_once_with(
            "wallet/action/42",
            payload={"action": "release_reservation", "reference_id": "payout-001"},
        )


class TestWalletQueries:
    def _make_wallet(self):
        return Wallet(_wallet_data())

    @patch("mojowallet.wallet._client.get")
    def test_balance(self, mock_get):
        mock_get.return_value = objict(balance=5000)
        w = self._make_wallet()
        result = w.balance("SC_REAL")
        assert result == 5000
        mock_get.assert_called_once_with(
            "wallet/query/42",
            params={"q": "balance", "currency_code": "SC_REAL"},
        )

    @patch("mojowallet.wallet._client.get")
    def test_balance_summary(self, mock_get):
        mock_get.return_value = objict(SC_REAL=5000, SC_PROMO=1000)
        w = self._make_wallet()
        result = w.balance_summary()
        assert result.SC_REAL == 5000

    @patch("mojowallet.wallet._client.get")
    def test_cashable(self, mock_get):
        mock_get.return_value = objict(cashable=3000)
        w = self._make_wallet()
        result = w.cashable("SC_REAL")
        assert result == 3000

    @patch("mojowallet.wallet._client.get")
    def test_transactions(self, mock_get):
        mock_get.return_value = [objict(id=1), objict(id=2)]
        w = self._make_wallet()
        result = w.transactions(currency_code="SC_REAL", limit=20)
        assert len(result) == 2


class TestWalletSaveActions:
    def _make_wallet(self):
        return Wallet(_wallet_data())

    @patch("mojowallet.wallet._client.post")
    def test_lock(self, mock_post):
        mock_post.return_value = objict(locked=True)
        w = self._make_wallet()
        w.lock(reason="Chargeback")
        mock_post.assert_called_once_with(
            "wallet/42",
            payload={"lock": {"reason": "Chargeback"}},
        )

    @patch("mojowallet.wallet._client.post")
    def test_unlock(self, mock_post):
        mock_post.return_value = objict(locked=False)
        w = self._make_wallet()
        w.unlock(reason="Cleared")
        mock_post.assert_called_once_with(
            "wallet/42",
            payload={"unlock": {"reason": "Cleared"}},
        )

    @patch("mojowallet.wallet._client.post")
    def test_redeem_promo(self, mock_post):
        mock_post.return_value = objict(id=5, status="COMPLETED")
        w = self._make_wallet()
        w.redeem_promo("WELCOME100", reference_id="promo-001")
        mock_post.assert_called_once_with(
            "wallet/42",
            payload={"redeem_promo": {"code": "WELCOME100", "reference_id": "promo-001"}},
        )


class TestWalletSessions:
    def _make_wallet(self):
        return Wallet(_wallet_data())

    @patch("mojowallet.wallet._client.post")
    def test_start_session(self, mock_post):
        mock_post.return_value = objict(id=10, uuid="sess-abc", session_id="game-xyz")
        w = self._make_wallet()
        session = w.start_session("game-xyz", expires_in_seconds=3600)
        assert session.id == 10
        assert session.session_id == "game-xyz"

    @patch("mojowallet.wallet._client.post")
    def test_session_context_manager(self, mock_post):
        mock_post.return_value = objict(id=10, uuid="sess-abc", session_id="game-xyz")
        w = self._make_wallet()
        with w.session("game-xyz") as s:
            assert s.session_id == "game-xyz"
        # close should have been called
        assert mock_post.call_count >= 2  # start + close


class TestWalletBatch:
    @patch("mojowallet.wallet._client.post")
    def test_batch_balances(self, mock_post):
        mock_post.return_value = [objict(wallet_id=1, balance=1000), objict(wallet_id=2, balance=2000)]
        result = Wallet.batch_balances([1, 2], currency_code="SC_REAL")
        mock_post.assert_called_once_with(
            "wallet/batch",
            payload={"action": "batch_balances", "wallet_ids": [1, 2], "currency_code": "SC_REAL"},
        )
        assert len(result) == 2
