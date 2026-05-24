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

### Spending across a currency family

```python
# Walk the SC family in priority order and debit across holdings as needed.
wallet.spend(750, root_code="SC", reference_id="game-bet-001", merchant="Casino")
```

### Balance reads

`balance_summary()` returns balances grouped by **root currency family**
(`root_code`), with per-currency totals exposed separately:

```python
s = wallet.balance_summary()
s.balances.SC.available          # 200000
s.balances.SC.by_code.SC_REAL    # {quantity: 150000, formatted: "$1500.00"}
s.total_by_currency.SC_REAL      # per-currency rollup, unchanged from 2.2.x
```

For per-holding detail or a single family lookup:

```python
holdings   = wallet.get_holdings(root_code="SC")
sc_balance = wallet.get_root_balance("SC")
```

**⚠ Breaking change in 2.3.0**: `balance_summary().balances` is now keyed by
`root_code` (was `currency_code`). Callers reading `s.balances["SC_REAL"]`
must switch to `s.total_by_currency["SC_REAL"]` or
`s.balances["SC"].by_code["SC_REAL"]`.

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

### Error codes

Wallet errors carry a numeric `code` (5000-block) and an HTTP status from
the table below. The SDK raises a matching subclass whenever the response
body includes a `code` in this range — the dispatch is authoritative
regardless of HTTP status.

| Code | HTTP | Class |
|------|------|-------|
| 5001 | 500 | `WalletInvariantError` |
| 5002 | 402 | `InsufficientBalanceError` |
| 5003 | 423 | `WalletLockedError` |
| 5004 | 423 | `WalletSuspendedError` |
| 5005 | 423 | `WalletInactiveError` |
| 5006 | 400 | `InvalidReferenceError` |
| 5007 | 409 | `IdempotentReplayError` |

`WalletInvariantError` deliberately surfaces only a generic "please retry"
message — never the server's diff text — so safety-critical balance-check
failures don't leak internal state.

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
