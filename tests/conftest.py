import os
import uuid
import pytest

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import mojowallet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _api_key():
    return os.environ.get("MOJOWALLET_API_KEY")


def _base_url():
    return os.environ.get("MOJOWALLET_BASE_URL", "https://api.mojoverify.com")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def live_client():
    """Construct a Client with env-var credentials for integration tests."""
    key = _api_key()
    if not key:
        pytest.skip("MOJOWALLET_API_KEY not set")
    return mojowallet.Client(api_key=key, base_url=_base_url())


@pytest.fixture
def customer_uuid(live_client):
    """Customer UUID for integration tests.

    Set MOJOWALLET_CUSTOMER_UUID in .env, or auto-discover from first wallet.
    """
    cid = os.environ.get("MOJOWALLET_CUSTOMER_UUID")
    if cid:
        return cid
    wallets = live_client.Wallet.list(limit=1)
    if wallets and isinstance(wallets, list) and len(wallets) > 0:
        return wallets[0].customer_uuid
    pytest.skip("No MOJOWALLET_CUSTOMER_UUID and no wallets on server")


@pytest.fixture
def wallet(live_client, customer_uuid):
    """Get a wallet by customer UUID for integration tests."""
    return live_client.Wallet.get_by_customer(customer_uuid)


@pytest.fixture
def customer(live_client):
    """Create or retrieve the default test customer (John Doe)."""
    return live_client.Customer.create(
        first_name="John",
        last_name="Doe",
        dob="1990-01-15",
        email="test@mojoverify.com",
        phone="9498416357",
        address_line1="31212 Paseo Acacia",
        address_city="San Juan Capo",
        address_state="CA",
        address_postal_code="92675",
        address_country="US",
    )


@pytest.fixture
def funded_wallet(wallet):
    """A wallet with guaranteed funds for withdrawal tests."""
    wallet.add_funds(
        amount_units=10000,
        currency_code="SC_REAL",
        source="CREDIT_CARD",
        category="deposited",
        reference_id=f"fund-{uuid.uuid4().hex[:12]}",
    )
    return wallet


# ---------------------------------------------------------------------------
# Unit-test helpers (fake mode)
# ---------------------------------------------------------------------------
def fake_client(base_url="https://api.example.com", api_key="test-key"):
    """A Client in fake mode with a capturing helper attached.

    Tests register responders and inspect ``client.captured`` to assert what
    was called. Used by all unit tests so the SDK code path is exercised
    without ``requests`` ever being invoked.
    """
    client = mojowallet.Client(api_key=api_key, base_url=base_url, fake_mode=True)
    client.captured = []

    def capture_matcher(method, url, payload):
        client.captured.append((method, url, payload))
        return False  # let the next responder handle the actual reply

    client.register_fake_responder(capture_matcher, None)
    return client


@pytest.fixture
def client():
    """A fake-mode Client for unit tests."""
    return fake_client()


# ---------------------------------------------------------------------------
# Auto-skip integration tests when no API key
# ---------------------------------------------------------------------------
def pytest_collection_modifyitems(config, items):
    skip_marker = pytest.mark.skip(reason="MOJOWALLET_API_KEY not set")
    for item in items:
        if "integration" in item.keywords and not _api_key():
            item.add_marker(skip_marker)
