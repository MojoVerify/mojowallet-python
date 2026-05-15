"""Unit tests for Customer class — mocked, no API key needed."""

from unittest.mock import patch
import pytest
from objict import objict

from mojowallet.customer import Customer
from mojowallet import _client


@pytest.fixture(autouse=True)
def reset_state():
    original = dict(_client._state)
    _client._state["api_key"] = "test-key"
    _client._state["base_url"] = "https://api.example.com"
    yield
    _client._state.update(original)


def _customer_data(**overrides):
    data = objict(
        id=7, uuid="cust-abc123",
        first_name="John", last_name="Doe",
        email="john@example.com", phone="+15551234567",
        status="active", kyc_level=0,
        risk_level="low", trust_level="none",
        confidence_score=0,
        is_email_verified=False, is_phone_verified=False,
        is_ssn_verified=False, is_gov_id_verified=False,
        is_liveness_verified=False,
    )
    data.update(overrides)
    return data


class TestCustomerCRUD:
    @patch("mojowallet.customer._client.post")
    def test_create(self, mock_post):
        mock_post.return_value = _customer_data()
        c = Customer.create(first_name="John", last_name="Doe", dob="1990-01-15")
        assert c.id == 7
        assert c.first_name == "John"
        mock_post.assert_called_once_with(
            "customer",
            payload={"first_name": "John", "last_name": "Doe", "date_of_birth": "1990-01-15"},
            prefix="verify",
        )

    @patch("mojowallet.customer._client.post")
    def test_create_with_address(self, mock_post):
        mock_post.return_value = _customer_data()
        Customer.create(
            first_name="John", last_name="Doe",
            email="john@example.com",
            address_line1="123 Main St", address_city="Test", address_state="CA",
            address_postal_code="92675", address_country="US",
        )
        payload = mock_post.call_args[1]["payload"]
        assert payload["address_line1"] == "123 Main St"
        assert payload["address_state"] == "CA"

    @patch("mojowallet.customer._client.get")
    def test_get_by_id(self, mock_get):
        mock_get.return_value = _customer_data()
        c = Customer.get(7)
        assert c.id == 7
        assert c.uuid == "cust-abc123"
        mock_get.assert_called_once_with("customer/7", prefix="verify")

    @patch("mojowallet.customer._client.get")
    def test_get_by_uuid(self, mock_get):
        mock_get.return_value = _customer_data()
        c = Customer.get("cust-abc123")
        assert c.first_name == "John"
        mock_get.assert_called_once_with("customer/cust-abc123", prefix="verify")

    @patch("mojowallet.customer._client.get")
    def test_list(self, mock_get):
        mock_get.return_value = [_customer_data(id=1), _customer_data(id=2)]
        result = Customer.list(status="active")
        assert len(result) == 2
        assert result[0].id == 1
        mock_get.assert_called_once_with("customer", params={"status": "active"}, prefix="verify")

    @patch("mojowallet.customer._client.get")
    def test_refresh(self, mock_get):
        mock_get.return_value = _customer_data(kyc_level=2)
        c = Customer(_customer_data())
        c.refresh()
        assert c.kyc_level == 2

    @patch("mojowallet.customer._client.post")
    def test_update(self, mock_post):
        mock_post.return_value = _customer_data(email="new@example.com")
        c = Customer(_customer_data())
        c.update(email="new@example.com", phone="+15559999999")
        mock_post.assert_called_once_with(
            "customer/7",
            payload={"email": "new@example.com", "phone": "+15559999999"},
            prefix="verify",
        )
        assert c.email == "new@example.com"

    @patch("mojowallet.customer._client.post")
    def test_update_meta(self, mock_post):
        mock_post.return_value = _customer_data()
        c = Customer(_customer_data())
        c.update_meta({"vip": True, "tier": "gold"})
        mock_post.assert_called_once_with(
            "customer/7",
            payload={"metadata": {"vip": True, "tier": "gold"}},
            prefix="verify",
        )


class TestCustomerVerification:
    def _make(self):
        return Customer(_customer_data())

    @patch("mojowallet.customer._client.post")
    def test_verify_email(self, mock_post):
        mock_post.return_value = objict(email="john@example.com", token="abc-123", expires_at="2026-03-10T00:00:00Z", send_status="sent")
        c = self._make()
        result = c.verify_email()
        mock_post.assert_called_once_with(
            "email/verify",
            payload={"email": "john@example.com", "redirect_url": ""},
            prefix="tools",
        )
        assert result.send_status == "sent"

    @patch("mojowallet.customer._client.post")
    def test_verify_email_custom(self, mock_post):
        mock_post.return_value = objict(email="other@example.com", token="xyz", expires_at="2026-03-10T00:00:00Z", send_status="sent")
        c = self._make()
        c.verify_email(email="other@example.com", redirect_url="https://app.com/done")
        mock_post.assert_called_once_with(
            "email/verify",
            payload={"email": "other@example.com", "redirect_url": "https://app.com/done"},
            prefix="tools",
        )

    @patch("mojowallet.customer._client.post")
    def test_verify_phone(self, mock_post):
        mock_post.return_value = objict(phone="+15551234567", token="def-456", expires_at="2026-03-10T00:00:00Z", send_status="sent")
        c = self._make()
        result = c.verify_phone()
        mock_post.assert_called_once_with(
            "phone/verify",
            payload={"phone": "+15551234567", "redirect_url": ""},
            prefix="tools",
        )
        assert result.send_status == "sent"


class TestCustomerLiveness:
    def _make(self):
        return Customer(_customer_data())

    @patch("mojowallet.customer._client.post")
    def test_request_liveness_with_existing_request(self, mock_post):
        mock_post.return_value = objict(session_token="ident-abc123", session_id=99, status="pending")
        c = self._make()
        token = c.request_liveness_check(verification_request_id=789)
        assert token == "ident-abc123"
        mock_post.assert_called_once_with(
            "sessions",
            payload={"verification_request": 789, "require_liveness": True},
            prefix="identity",
        )

    @patch("mojowallet.customer._client.post")
    def test_request_liveness_auto_creates_request(self, mock_post):
        # First call creates the verify request, second starts identity session
        mock_post.side_effect = [
            objict(id=100, uuid="pvr-abc"),                  # create request
            objict(session_token="ident-xyz", session_id=50, status="pending"),  # start session
        ]
        c = self._make()
        token = c.request_liveness_check()
        assert token == "ident-xyz"
        assert mock_post.call_count == 2
        # First call: create verify request
        first_call = mock_post.call_args_list[0]
        assert first_call[0][0] == "requests"
        assert first_call[1]["prefix"] == "verify"
        assert first_call[1]["payload"]["require_liveness"] is True
        # Second call: start identity session
        second_call = mock_post.call_args_list[1]
        assert second_call[0][0] == "sessions"
        assert second_call[1]["prefix"] == "identity"
        assert second_call[1]["payload"]["verification_request"] == 100

    @patch("mojowallet.customer._client.get")
    def test_check_liveness_status(self, mock_get):
        mock_get.return_value = objict(status="completed", decision="pass", overall_score=95)
        c = self._make()
        result = c.check_liveness_status("ident-abc123")
        assert result.decision == "pass"
        mock_get.assert_called_once_with(
            "sessions/status",
            params={"session_token": "ident-abc123"},
            prefix="identity",
        )


class TestCustomerKYC:
    def _make(self):
        return Customer(_customer_data())

    @patch("mojowallet.customer._client.post")
    def test_request_kyc(self, mock_post):
        mock_post.return_value = objict(id=200, uuid="pvr-kyc-001", status="pending")
        c = self._make()
        request_uuid = c.request_kyc(require_ssn=True, require_gov_id=True)
        assert request_uuid == "pvr-kyc-001"
        payload = mock_post.call_args[1]["payload"]
        assert payload["first_name"] == "John"
        assert payload["last_name"] == "Doe"
        assert payload["require_ssn"] is True
        assert payload["require_gov_id"] is True
        mock_post.assert_called_once_with("requests", payload=payload, prefix="verify")

    @patch("mojowallet.customer._client.get")
    def test_check_kyc_request(self, mock_get):
        mock_get.return_value = objict(
            id=200, uuid="pvr-kyc-001", status="completed",
            kyc_level=2, risk_level="low",
            is_ssn_verified=True, is_gov_id_verified=True,
        )
        c = self._make()
        result = c.check_kyc_request("pvr-kyc-001")
        assert result.status == "completed"
        assert result.kyc_level == 2
        mock_get.assert_called_once_with("requests/uuid/pvr-kyc-001", prefix="verify")

    @patch("mojowallet.customer._client.get")
    def test_get_kyc_status(self, mock_get):
        mock_get.return_value = _customer_data(
            kyc_level=2, is_email_verified=True, is_ssn_verified=True,
        )
        c = Customer(_customer_data())
        status = c.get_kyc_status()
        assert status.kyc_level == 2
        assert status.is_email_verified is True
        assert status.is_ssn_verified is True


class TestCustomerRepr:
    def test_repr(self):
        c = Customer(_customer_data())
        assert repr(c) == "Customer(id=7, name='John Doe')"

    def test_attribute_access(self):
        c = Customer(_customer_data())
        assert c.uuid == "cust-abc123"
        assert c.status == "active"

    def test_missing_attribute_raises(self):
        c = Customer(_customer_data())
        with pytest.raises(AttributeError):
            _ = c.nonexistent_field
