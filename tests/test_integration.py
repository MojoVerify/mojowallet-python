"""Integration tests — hit a live server via the SDK.

Requires MOJOWALLET_API_KEY and (optionally) MOJOWALLET_BASE_URL in .env.
Skipped automatically when MOJOWALLET_API_KEY is not set.

Run with:  pytest tests/test_integration.py -v -s
"""

import uuid
import pytest

pytestmark = pytest.mark.integration


def _ref(prefix="int"):
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _sid():
    return f"sess-{uuid.uuid4().hex[:12]}"


# ── Wallet Retrieval ──────────────────────────────────────────

class TestWalletRetrieval:
    def test_list_wallets(self, live_client):
        result = live_client.Wallet.list()
        assert isinstance(result, list)

    def test_get_wallet_by_id(self, live_client, wallet):
        fetched = live_client.Wallet.get(wallet.id)
        assert fetched.id == wallet.id
        assert fetched.name == wallet.name

    def test_get_wallet_by_customer_uuid(self, live_client, wallet, customer_uuid):
        fetched = live_client.Wallet.get_by_customer(customer_uuid)
        assert fetched.id == wallet.id

    def test_refresh(self, wallet):
        wallet.refresh()
        assert wallet.id is not None


# ── Fund Operations ───────────────────────────────────────────

class TestFundOperations:
    def test_add_funds(self, wallet):
        result = wallet.add_funds(
            amount_units=1000,
            currency_code="SC_REAL",
            source="CREDIT_CARD",
            category="deposited",
            reference_id=_ref("deposit"),
        )
        assert result is not None

    def test_balance(self, wallet):
        bal = wallet.balance("SC_REAL")
        assert isinstance(bal, (int, float))
        assert bal >= 0

    def test_balance_summary(self, wallet):
        summary = wallet.balance_summary()
        assert summary is not None

    def test_cashable(self, wallet):
        cashable = wallet.cashable("SC_REAL")
        assert isinstance(cashable, (int, float))

    def test_transactions(self, wallet):
        txns = wallet.transactions(currency_code="SC_REAL", limit=5)
        assert txns is not None


# ── Withdraw / Cashout ────────────────────────────────────────

class TestWithdrawals:
    def test_withdraw_in_session(self, funded_wallet):
        wallet = funded_wallet
        session = wallet.start_session(_sid(), expires_in_seconds=3600)
        try:
            result = session.withdraw(
                amount_units=100,
                currency_code="SC_REAL",
                reference_id=_ref("bet"),
            )
            assert result is not None
        finally:
            session.close()

    def test_cashout(self, funded_wallet):
        result = funded_wallet.cashout(
            amount_units=50,
            currency_code="SC_REAL",
            reference_id=_ref("cashout"),
        )
        assert result is not None


# ── Reserve Flow ──────────────────────────────────────────────

class TestReserveFlow:
    def test_reserve_and_release(self, funded_wallet):
        ref = _ref("reserve")
        funded_wallet.reserve(500, "SC_REAL", "SC_HOLD", ref)
        result = funded_wallet.release_reservation(ref)
        assert result is not None

    def test_reserve_and_confirm(self, funded_wallet):
        ref = _ref("reserve")
        funded_wallet.reserve(300, "SC_REAL", "SC_HOLD", ref)
        result = funded_wallet.confirm_reservation(ref)
        assert result is not None


# ── Sessions ──────────────────────────────────────────────────

class TestSessions:
    def test_start_and_close(self, wallet):
        session = wallet.start_session(_sid(), expires_in_seconds=60)
        assert session.session_id is not None
        session.close()

    def test_context_manager(self, wallet):
        with wallet.session(_sid(), expires_in_seconds=60) as s:
            assert s.session_id is not None

    def test_extend_session(self, wallet):
        session = wallet.start_session(_sid(), expires_in_seconds=60)
        result = session.extend(1800)
        assert result is not None
        session.close()


# ── Lock / Unlock ─────────────────────────────────────────────

class TestLockUnlock:
    def test_lock_and_unlock(self, wallet):
        wallet.lock(reason="integration test")
        wallet.refresh()
        assert wallet.is_locked is True

        wallet.unlock(reason="integration test done")
        wallet.refresh()
        assert wallet.is_locked is False


# ── Full Lifecycle ────────────────────────────────────────────

class TestLifecycle:
    def test_deposit_play_cashout(self, wallet):
        """Full lifecycle: deposit → check balance → session → withdraw → close → balance."""
        wallet.add_funds(5000, "SC_REAL", source="CREDIT_CARD",
                         category="deposited", reference_id=_ref("lifecycle"))

        bal_before = wallet.balance("SC_REAL")
        assert bal_before >= 5000

        sid = _sid()
        session = wallet.start_session(sid, expires_in_seconds=3600)
        session.withdraw(2000, "SC_REAL", reference_id=_ref("play"))
        session.close()

        bal_after = wallet.balance("SC_REAL")
        assert bal_after == bal_before - 2000


# ── Customer CRUD ────────────────────────────────────────────

class TestCustomerCRUD:
    def test_create_customer(self, customer):
        assert customer.id is not None
        assert customer.first_name == "John"
        assert customer.last_name == "Doe"
        assert customer.uuid is not None

    def test_get_customer_by_id(self, live_client, customer):
        fetched = live_client.Customer.get(customer.id)
        assert fetched.id == customer.id
        assert fetched.first_name == "John"

    def test_get_customer_by_uuid(self, live_client, customer):
        fetched = live_client.Customer.get(customer.uuid)
        assert fetched.uuid == customer.uuid

    def test_list_customers(self, live_client):
        result = live_client.Customer.list()
        assert isinstance(result, list)

    def test_update_customer(self, customer):
        customer.update(email="test@mojoverify.com")
        assert customer.email == "test@mojoverify.com"

    def test_update_meta(self, customer):
        customer.update_meta({"test_run": True, "sdk": "python"})
        customer.refresh()

    def test_refresh(self, customer):
        customer.refresh()
        assert customer.id is not None
        assert customer.first_name == "John"


# ── Customer Verification ────────────────────────────────────

class TestCustomerVerification:
    def test_verify_email(self, customer):
        result = customer.verify_email()
        assert result.send_status is not None

    def test_verify_email_custom(self, customer):
        result = customer.verify_email(email="test@mojoverify.com")
        assert result.send_status is not None

    def test_verify_phone(self, customer):
        result = customer.verify_phone()
        assert result.send_status is not None


# ── Customer KYC ─────────────────────────────────────────────

class TestCustomerKYC:
    def test_request_kyc(self, customer):
        request_uuid = customer.request_kyc(
            require_ssn=True,
            require_gov_id=False,
        )
        assert request_uuid is not None
        assert isinstance(request_uuid, str)

    def test_check_kyc_request(self, customer):
        request_uuid = customer.request_kyc(require_ssn=True)
        result = customer.check_kyc_request(request_uuid)
        assert result.status is not None
        assert result.uuid == request_uuid

    def test_get_kyc_status(self, customer):
        status = customer.get_kyc_status()
        assert hasattr(status, "kyc_level")
