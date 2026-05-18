"""Unit tests for Customer class — fake-mode Client, no network."""

import pytest
from objict import objict

import mojowallet
from mojowallet.customer import Customer


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


def _respond_list(client, items):
    client.register_fake_responder(
        lambda *a: True,
        {"status_code": 200, "body": {"status": True, "data": items}},
    )


class TestCustomerNamespace:
    def test_create(self, client, captured):
        _respond(client, _customer_data())
        c = client.Customer.create(first_name="John", last_name="Doe", dob="1990-01-15")
        assert c.id == 7
        assert c.first_name == "John"
        assert c._client is client
        assert captured[-1]["method"] == "POST"
        assert captured[-1]["url"] == "https://api.example.com/api/verify/customer"
        assert captured[-1]["payload"] == {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-15",
        }

    def test_create_with_address(self, client, captured):
        _respond(client, _customer_data())
        client.Customer.create(
            first_name="John", last_name="Doe",
            email="john@example.com",
            address_line1="123 Main St", address_city="Test", address_state="CA",
            address_postal_code="92675", address_country="US",
        )
        p = captured[-1]["payload"]
        assert p["address_line1"] == "123 Main St"
        assert p["address_state"] == "CA"

    def test_get_by_id(self, client, captured):
        _respond(client, _customer_data())
        c = client.Customer.get(7)
        assert c.id == 7
        assert c.uuid == "cust-abc123"
        assert captured[-1]["url"] == "https://api.example.com/api/verify/customer/7"

    def test_get_by_uuid(self, client, captured):
        _respond(client, _customer_data())
        c = client.Customer.get("cust-abc123")
        assert c.first_name == "John"
        assert captured[-1]["url"] == "https://api.example.com/api/verify/customer/cust-abc123"

    def test_list(self, client, captured):
        _respond_list(client, [{"id": 1, "first_name": "A", "last_name": "X"},
                               {"id": 2, "first_name": "B", "last_name": "Y"}])
        result = client.Customer.list(status="active")
        assert len(result) == 2
        assert result[0]._client is client
        assert captured[-1]["url"] == "https://api.example.com/api/verify/customer"
        assert captured[-1]["payload"] == {"status": "active"}


class TestCustomerInstance:
    def _c(self, client):
        return Customer(_customer_data(), client)

    def test_refresh(self, client, captured):
        _respond(client, _customer_data(kyc_level=2))
        c = self._c(client)
        c.refresh()
        assert c.kyc_level == 2

    def test_update(self, client, captured):
        _respond(client, _customer_data(email="new@example.com"))
        c = self._c(client)
        c.update(email="new@example.com", phone="+15559999999")
        assert captured[-1]["url"] == "https://api.example.com/api/verify/customer/7"
        assert captured[-1]["payload"] == {"email": "new@example.com", "phone": "+15559999999"}
        assert c.email == "new@example.com"

    def test_update_meta(self, client, captured):
        _respond(client, _customer_data())
        self._c(client).update_meta({"vip": True, "tier": "gold"})
        assert captured[-1]["payload"] == {"metadata": {"vip": True, "tier": "gold"}}


class TestCustomerVerification:
    def _c(self, client):
        return Customer(_customer_data(), client)

    def test_verify_email(self, client, captured):
        _respond(client, {"email": "john@example.com", "token": "abc",
                          "expires_at": "2026-03-10T00:00:00Z", "send_status": "sent"})
        result = self._c(client).verify_email()
        assert captured[-1]["url"] == "https://api.example.com/api/tools/email/verify"
        assert captured[-1]["payload"] == {"email": "john@example.com", "redirect_url": ""}
        assert result.send_status == "sent"

    def test_verify_email_custom(self, client, captured):
        _respond(client, {"send_status": "sent"})
        self._c(client).verify_email(email="other@example.com", redirect_url="https://app.com/done")
        assert captured[-1]["payload"]["email"] == "other@example.com"
        assert captured[-1]["payload"]["redirect_url"] == "https://app.com/done"

    def test_verify_phone(self, client, captured):
        _respond(client, {"send_status": "sent"})
        result = self._c(client).verify_phone()
        assert captured[-1]["url"] == "https://api.example.com/api/tools/phone/verify"
        assert captured[-1]["payload"]["phone"] == "+15551234567"
        assert result.send_status == "sent"


class TestCustomerLiveness:
    def _c(self, client):
        return Customer(_customer_data(), client)

    def test_request_liveness_with_existing_request(self, client, captured):
        _respond(client, {"session_token": "ident-abc123", "session_id": 99, "status": "pending"})
        token = self._c(client).request_liveness_check(verification_request_id=789)
        assert token == "ident-abc123"
        assert captured[-1]["url"] == "https://api.example.com/api/identity/sessions"
        assert captured[-1]["payload"]["verification_request"] == 789

    def test_request_liveness_auto_creates_request(self, client, captured):
        client.reset_fake_responders()
        responses = iter([
            {"status_code": 200, "body": {"status": True, "data": {"id": 100, "uuid": "pvr-abc"}}},
            {"status_code": 200, "body": {"status": True, "data": {"session_token": "ident-xyz", "session_id": 50, "status": "pending"}}},
        ])

        def capture(method, url, payload):
            captured.append({"method": method, "url": url, "payload": payload})
            return False

        client.register_fake_responder(capture, None)
        client.register_fake_responder(lambda *a: True, lambda: next(responses))

        token = self._c(client).request_liveness_check()
        assert token == "ident-xyz"
        # First call: create verify request at /api/verify/requests
        assert captured[0]["url"] == "https://api.example.com/api/verify/requests"
        # Second call: start identity session
        assert captured[1]["url"] == "https://api.example.com/api/identity/sessions"
        assert captured[1]["payload"]["verification_request"] == 100

    def test_check_liveness_status(self, client, captured):
        _respond(client, {"status": "completed", "decision": "pass", "overall_score": 95})
        result = self._c(client).check_liveness_status("ident-abc123")
        assert result.decision == "pass"
        assert captured[-1]["url"] == "https://api.example.com/api/identity/sessions/status"
        assert captured[-1]["payload"] == {"session_token": "ident-abc123"}


class TestCustomerKYC:
    def _c(self, client):
        return Customer(_customer_data(), client)

    def test_request_kyc(self, client, captured):
        _respond(client, {"id": 200, "uuid": "pvr-kyc-001", "status": "pending"})
        request_uuid = self._c(client).request_kyc(require_ssn=True, require_gov_id=True)
        assert request_uuid == "pvr-kyc-001"
        p = captured[-1]["payload"]
        assert p["first_name"] == "John"
        assert p["last_name"] == "Doe"
        assert p["require_ssn"] is True
        assert p["require_gov_id"] is True
        assert captured[-1]["url"] == "https://api.example.com/api/verify/requests"

    def test_check_kyc_request(self, client, captured):
        _respond(client, {
            "id": 200, "uuid": "pvr-kyc-001", "status": "completed",
            "kyc_level": 2, "risk_level": "low",
            "is_ssn_verified": True, "is_gov_id_verified": True,
        })
        result = self._c(client).check_kyc_request("pvr-kyc-001")
        assert result.status == "completed"
        assert result.kyc_level == 2
        assert captured[-1]["url"] == "https://api.example.com/api/verify/requests/uuid/pvr-kyc-001"

    def test_get_kyc_status(self, client):
        _respond(client, _customer_data(kyc_level=2, is_email_verified=True, is_ssn_verified=True))
        c = Customer(_customer_data(), client)
        status = c.get_kyc_status()
        assert status.kyc_level == 2
        assert status.is_email_verified is True


class TestCustomerRepr:
    def test_repr(self, client):
        c = Customer(_customer_data(), client)
        assert repr(c) == "Customer(id=7, name='John Doe')"

    def test_attribute_access(self, client):
        c = Customer(_customer_data(), client)
        assert c.uuid == "cust-abc123"
        assert c.status == "active"

    def test_missing_attribute_raises(self, client):
        c = Customer(_customer_data(), client)
        with pytest.raises(AttributeError):
            _ = c.nonexistent_field
