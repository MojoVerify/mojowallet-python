# mojowallet

Python SDK for [MojoWallet](https://mojowallet.com) — digital wallet operations, sessions, balance management, and financial ledger tools.

## Installation

```bash
pip install mojowallet
```

**Requirements:** Python 3.10+ | **Dependencies:** `requests`, `pyobjict`

## Quick Start

```python
import mojowallet

mojowallet.configure("your-api-key", base_url="https://api.example.com")

wallet = mojowallet.Wallet.get(42)
wallet.add_funds(1000, "SC_REAL", source="CREDIT_CARD")
print(wallet.balance("SC_REAL"))
```

All responses support both dict-style (`resp["id"]`) and attribute-style (`resp.id`) access.

## Core Concepts

| Concept | Description |
|---------|-------------|
| [Wallet](docs/wallet.md) | OO wrapper — get a wallet, call actions on it |
| [Sessions](docs/sessions.md) | Concurrency control for withdrawals (context manager) |
| [Error Handling](docs/error-handling.md) | Exception hierarchy with domain-specific errors |

## Usage Examples

```python
# Funds
wallet.add_funds(1000, "SC_REAL", source="CREDIT_CARD", category="deposited")
wallet.purchase(500, "SC_REAL", merchant="Coffee Shop")
wallet.cashout(800, "SC_REAL", reference_id="cashout-001")

# Sessions (context manager for safety)
with wallet.session("game-xyz", expires_in_seconds=3600) as session:
    session.withdraw(500, "SC_REAL", reference_id="bet-001")
    session.extend(1800)

# Balances
balance = wallet.balance("SC_REAL")
summary = wallet.balance_summary()

# Reserve flow
wallet.reserve(2500, "SC_REAL", "SC_HOLD", reference_id="payout-001")
wallet.confirm_reservation("payout-001")

# Lock/unlock
wallet.lock(reason="Chargeback")
wallet.unlock(reason="Investigation cleared")
```

## Error Handling

```python
from mojowallet.exceptions import InsufficientBalanceError, SessionConflictError

try:
    wallet.cashout(10000, "SC_REAL", reference_id="cashout-002")
except InsufficientBalanceError as e:
    print(f"Not enough funds: {e.message}")
except SessionConflictError:
    print("Another session is already active")
```

## Documentation

- [Getting Started](docs/getting-started.md)
- [Wallet Operations](docs/wallet.md)
- [Sessions](docs/sessions.md)
- [Error Handling](docs/error-handling.md)
- [Changelog](docs/changelog.md)

## Development

```bash
pip install poetry
poetry install --with dev

# Run all tests (unit tests only — no API key needed)
pytest -v

# With sandbox credentials
cp .env.example .env
# Edit .env with your sandbox API key
pytest -v
```

## License

MIT
