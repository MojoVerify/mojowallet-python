"""Unit tests for Session class — fake-mode Client, no network."""

import pytest
from objict import objict

import mojowallet
from mojowallet.wallet import Wallet
from mojowallet.session import Session


def _wallet_data():
    return objict(id=42, uuid="wlt-abc123", name="Main Wallet",
                  is_active=True, is_locked=False)


def _session_data():
    return objict(id=10, uuid="sess-abc123", session_id="game-xyz")


@pytest.fixture
def captured():
    return []


@pytest.fixture
def client(captured):
    c = mojowallet.Client(api_key="test-key", base_url="https://api.example.com", fake_mode=True)

    def capture(method, url, payload):
        captured.append({"method": method, "url": url, "payload": payload})
        return False

    c.register_fake_responder(capture, None)
    return c


def _respond(client, body):
    client.register_fake_responder(
        lambda *a: True,
        {"status_code": 200, "body": {"status": True, "data": body}},
    )


class TestSessionWithdraw:
    def test_withdraw_routes_through_wallet_client(self, client, captured):
        _respond(client, {"id": 1, "status": "COMPLETED"})
        w = Wallet(_wallet_data(), client)
        s = Session(_session_data(), w)

        s.withdraw(500, "SC_REAL", reference_id="bet-001")

        assert captured[-1]["url"] == "https://api.example.com/api/wallet/wallet/action/42"
        assert captured[-1]["payload"] == {
            "action": "withdraw",
            "amount_units": 500,
            "currency_code": "SC_REAL",
            "session_id": "game-xyz",
            "reference_id": "bet-001",
        }


class TestSessionExtend:
    def test_extend(self, client, captured):
        _respond(client, {"expires_at": "2025-01-01T00:30:00Z"})
        w = Wallet(_wallet_data(), client)
        s = Session(_session_data(), w)

        s.extend(1800)
        assert captured[-1]["url"] == "https://api.example.com/api/wallet/session/10"
        assert captured[-1]["payload"] == {"extend": {"duration": 1800}}


class TestSessionClose:
    def test_close(self, client, captured):
        _respond(client, {"is_active": False})
        w = Wallet(_wallet_data(), client)
        s = Session(_session_data(), w)

        s.close()
        assert captured[-1]["url"] == "https://api.example.com/api/wallet/session/10"
        assert captured[-1]["payload"] == {"close": True}
        assert s._closed is True

    def test_close_is_idempotent(self, client, captured):
        _respond(client, {"is_active": False})
        w = Wallet(_wallet_data(), client)
        s = Session(_session_data(), w)

        s.close()
        s.close()
        close_calls = [c for c in captured if c["payload"] == {"close": True}]
        assert len(close_calls) == 1


class TestSessionContextManager:
    def test_context_manager_closes_on_exit(self, client, captured):
        client.reset_fake_responders()
        responses = iter([
            {"status_code": 200, "body": {"status": True, "data": {"id": 10, "uuid": "sess-abc", "session_id": "game-xyz"}}},
            {"status_code": 200, "body": {"status": True, "data": {"is_active": False}}},
        ])

        def capture(method, url, payload):
            captured.append({"method": method, "url": url, "payload": payload})
            return False

        client.register_fake_responder(capture, None)
        client.register_fake_responder(lambda *a: True, lambda: next(responses))

        w = Wallet(_wallet_data(), client)

        with w.session("game-xyz") as s:
            assert s.session_id == "game-xyz"

        # 2 POSTs total: start + close
        post_count = len([c for c in captured if c["method"] == "POST"])
        assert post_count == 2
        # Last should be close
        assert captured[-1]["payload"] == {"close": True}

    def test_context_manager_closes_on_exception(self, client, captured):
        client.reset_fake_responders()
        responses = iter([
            {"status_code": 200, "body": {"status": True, "data": {"id": 10, "uuid": "sess-abc", "session_id": "game-xyz"}}},
            {"status_code": 200, "body": {"status": True, "data": {"is_active": False}}},
        ])

        def capture(method, url, payload):
            captured.append({"method": method, "url": url, "payload": payload})
            return False

        client.register_fake_responder(capture, None)
        client.register_fake_responder(lambda *a: True, lambda: next(responses))

        w = Wallet(_wallet_data(), client)

        with pytest.raises(ValueError):
            with w.session("game-xyz"):
                raise ValueError("test error")

        # close should still be called (2 POSTs: start + close)
        post_count = len([c for c in captured if c["method"] == "POST"])
        assert post_count == 2


class TestSessionRepr:
    def test_repr_active(self, client):
        w = Wallet(_wallet_data(), client)
        s = Session(_session_data(), w)
        assert "active" in repr(s)
        assert "game-xyz" in repr(s)

    def test_repr_closed(self, client):
        w = Wallet(_wallet_data(), client)
        s = Session(_session_data(), w)
        s._closed = True
        assert "closed" in repr(s)
