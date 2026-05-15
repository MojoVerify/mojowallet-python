import os
import uuid
import pytest

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import mojowallet
from mojowallet import _client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _api_key():
    return os.environ.get("MOJOWALLET_API_KEY")


def _base_url():
    return os.environ.get("MOJOWALLET_BASE_URL", "https://api.mojoverify.com/")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def configured_client():
    """Configure mojowallet with env-var credentials, then reset state."""
    key = _api_key()
    if not key:
        pytest.skip("MOJOWALLET_API_KEY not set")

    original_state = dict(_client._state)
    mojowallet.configure(key, base_url=_base_url())
    yield
    _client._state.update(original_state)


@pytest.fixture
def customer_uuid(configured_client):
    """Customer UUID for integration tests.

    Set MOJOWALLET_CUSTOMER_UUID in .env, or auto-discovers from first wallet.
    """
    cid = os.environ.get("MOJOWALLET_CUSTOMER_UUID")
    if cid:
        return cid
    wallets = mojowallet.Wallet.list(limit=1)
    if wallets and isinstance(wallets, list) and len(wallets) > 0:
        return wallets[0].customer_uuid
    pytest.skip("No MOJOWALLET_CUSTOMER_UUID and no wallets on server")


@pytest.fixture
def wallet(configured_client, customer_uuid):
    """Get a wallet by customer UUID for integration tests."""
    return mojowallet.Wallet.get_by_customer(customer_uuid)


@pytest.fixture
def customer(configured_client):
    """Create or retrieve the default test customer (John Doe)."""
    return mojowallet.Customer.create(
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
# Auto-skip integration tests when no API key
# ---------------------------------------------------------------------------
def pytest_collection_modifyitems(config, items):
    skip_marker = pytest.mark.skip(reason="MOJOWALLET_API_KEY not set")
    for item in items:
        if "integration" in item.keywords and not _api_key():
            item.add_marker(skip_marker)
