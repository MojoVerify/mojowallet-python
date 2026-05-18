"""Unit tests for Wallet class — fake-mode Client, no network."""

import pytest
from objict import objict

import mojowallet
from mojowallet.wallet import Wallet


def _wallet_data(**overrides):
    data = objict(id=42, uuid="wlt-abc123", name="Main Wallet",
                  is_active=True, is_locked=False)
    data.update(overrides)
    return data


@pytest.fixture
def captured():
    return []


@pytest.fixture
def client(captured):
    c = mojowallet.Client(api_key="test-key", base_url="https://api.example.com", fake_mode=True)

    def capture(method, url, payload):
        captured.append({"method": method, "url": url, "payload": payload})
        return False  # let the next responder reply

    c.register_fake_responder(capture, None)
    return c


def _respond(client, body):
    client.register_fake_responder(
        lambda *a: True,
        {"status_code": 200, "body": {"status": True, "data": body}},
    )


def _respond_list(client, items):
    client.register_fake_responder(
        lambda *a: True,
        {"status_code": 200, "body": {"status": True, "data": items}},
    )


class TestWalletNamespace:
    def test_get(self, client, captured):
        _respond(client, _wallet_data())
        w = client.Wallet.get(42)
        assert w.id == 42
        assert w.uuid == "wlt-abc123"
        assert w.name == "Main Wallet"
        assert captured[-1]["method"] == "GET"
        assert captured[-1]["url"] == "https://api.example.com/api/wallet/wallet/42"

    def test_get_by_customer(self, client, captured):
        _respond(client, _wallet_data())
        w = client.Wallet.get_by_customer("cust-abc123")
        assert w.id == 42
        assert captured[-1]["url"] == "https://api.example.com/api/wallet/wallet/cust-abc123"

    def test_list(self, client, captured):
        _respond_list(client, [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}])
        result = client.Wallet.list(status="active")
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0]._client is client  # bound to client
        assert captured[-1]["url"] == "https://api.example.com/api/wallet/wallet"

    def test_batch_balances(self, client, captured):
        _respond_list(client, [{"wallet_id": 1, "balance": 1000}, {"wallet_id": 2, "balance": 2000}])
        result = client.Wallet.batch_balances([1, 2], currency_code="SC_REAL")
        assert len(result) == 2
        assert captured[-1]["method"] == "POST"
        assert captured[-1]["payload"]["action"] == "batch_balances"
        assert captured[-1]["payload"]["wallet_ids"] == [1, 2]
        assert captured[-1]["payload"]["currency_code"] == "SC_REAL"


class TestWalletActions:
    def _w(self, client):
        return Wallet(_wallet_data(), client)

    def test_add_funds(self, client, captured):
        _respond(client, {"id": 1, "status": "COMPLETED"})
        self._w(client).add_funds(1000, "SC_REAL", source="CREDIT_CARD")
        assert captured[-1]["payload"] == {
            "action": "add_funds",
            "amount_units": 1000,
            "currency_code": "SC_REAL",
            "source": "CREDIT_CARD",
        }
        assert captured[-1]["url"] == "https://api.example.com/api/wallet/wallet/action/42"

    def test_purchase(self, client, captured):
        _respond(client, {"id": 2, "status": "COMPLETED"})
        self._w(client).purchase(500, "SC_REAL", merchant="Coffee Shop")
        assert captured[-1]["payload"]["action"] == "purchase"
        assert captured[-1]["payload"]["merchant"] == "Coffee Shop"

    def test_cashout(self, client, captured):
        _respond(client, {"id": 3, "status": "COMPLETED"})
        self._w(client).cashout(800, "SC_REAL", reference_id="cashout-001")
        assert captured[-1]["payload"]["action"] == "cashout"
        assert captured[-1]["payload"]["reference_id"] == "cashout-001"

    def test_reserve(self, client, captured):
        _respond(client, {"id": 4, "status": "COMPLETED"})
        self._w(client).reserve(2500, "SC_REAL", "SC_HOLD", "payout-001")
        p = captured[-1]["payload"]
        assert p["action"] == "reserve"
        assert p["hold_currency_code"] == "SC_HOLD"
        assert p["reference_id"] == "payout-001"

    def test_confirm_reservation(self, client, captured):
        _respond(client, {"status": "COMPLETED"})
        self._w(client).confirm_reservation("payout-001")
        assert captured[-1]["payload"] == {"action": "confirm_reservation", "reference_id": "payout-001"}

    def test_release_reservation(self, client, captured):
        _respond(client, {"status": "RELEASED"})
        self._w(client).release_reservation("payout-001")
        assert captured[-1]["payload"] == {"action": "release_reservation", "reference_id": "payout-001"}


class TestWalletQueries:
    def _w(self, client):
        return Wallet(_wallet_data(), client)

    def test_balance(self, client, captured):
        _respond(client, {"balance": 5000})
        result = self._w(client).balance("SC_REAL")
        assert result == 5000
        assert captured[-1]["method"] == "GET"
        assert captured[-1]["payload"] == {"q": "balance", "currency_code": "SC_REAL"}

    def test_balance_summary(self, client):
        _respond(client, {"SC_REAL": 5000, "SC_PROMO": 1000})
        result = self._w(client).balance_summary()
        assert result.SC_REAL == 5000

    def test_cashable(self, client):
        _respond(client, {"cashable": 3000})
        result = self._w(client).cashable("SC_REAL")
        assert result == 3000

    def test_transactions(self, client):
        _respond_list(client, [{"id": 1}, {"id": 2}])
        result = self._w(client).transactions(currency_code="SC_REAL", limit=20)
        assert len(result) == 2


class TestWalletSaveActions:
    def _w(self, client):
        return Wallet(_wallet_data(), client)

    def test_lock(self, client, captured):
        _respond(client, {"locked": True})
        self._w(client).lock(reason="Chargeback")
        assert captured[-1]["url"] == "https://api.example.com/api/wallet/wallet/42"
        assert captured[-1]["payload"] == {"lock": {"reason": "Chargeback"}}

    def test_unlock(self, client, captured):
        _respond(client, {"locked": False})
        self._w(client).unlock(reason="Cleared")
        assert captured[-1]["payload"] == {"unlock": {"reason": "Cleared"}}

    def test_redeem_promo(self, client, captured):
        _respond(client, {"id": 5, "status": "COMPLETED"})
        self._w(client).redeem_promo("WELCOME100", reference_id="promo-001")
        assert captured[-1]["payload"] == {
            "redeem_promo": {"code": "WELCOME100", "reference_id": "promo-001"}
        }


class TestWalletSessions:
    def _w(self, client):
        return Wallet(_wallet_data(), client)

    def test_start_session(self, client, captured):
        _respond(client, {"id": 10, "uuid": "sess-abc", "session_id": "game-xyz"})
        session = self._w(client).start_session("game-xyz", expires_in_seconds=3600)
        assert session.id == 10
        assert session.session_id == "game-xyz"
        assert captured[-1]["payload"]["action"] == "start_session"

    def test_session_context_manager(self, client, captured):
        # First call returns session start, second handles close
        client.reset_fake_responders()
        responses = iter([
            {"status_code": 200, "body": {"status": True, "data": {"id": 10, "uuid": "sess-abc", "session_id": "game-xyz"}}},
            {"status_code": 200, "body": {"status": True, "data": {"closed": True}}},
        ])

        def capture(method, url, payload):
            captured.append({"method": method, "url": url, "payload": payload})
            return False

        client.register_fake_responder(capture, None)
        client.register_fake_responder(lambda *a: True, lambda: next(responses))

        w = self._w(client)
        with w.session("game-xyz") as s:
            assert s.session_id == "game-xyz"
        # Two POSTs: start_session + close
        assert len([c for c in captured if c["method"] == "POST"]) == 2


class TestWalletIsolation:
    """Critical: two Clients with different keys must not share state."""

    def test_two_clients_independent(self):
        a = mojowallet.Client(api_key="key-a", base_url="https://api.example.com", fake_mode=True)
        b = mojowallet.Client(api_key="key-b", base_url="https://api.example.com", fake_mode=True)

        a.register_fake_responder(lambda *args: True, {"status_code": 200,
            "body": {"status": True, "data": _wallet_data(id=1, name="Wallet A")}})
        b.register_fake_responder(lambda *args: True, {"status_code": 200,
            "body": {"status": True, "data": _wallet_data(id=2, name="Wallet B")}})

        wa = a.Wallet.get(1)
        wb = b.Wallet.get(2)

        assert wa._client is a
        assert wb._client is b
        assert wa.id == 1 and wb.id == 2
        assert a.api_key == "key-a"
        assert b.api_key == "key-b"
