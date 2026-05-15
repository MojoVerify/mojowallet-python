# Wallet Operations

Full API reference for the `Wallet` class. All operations are methods on a wallet instance.

```python
import mojowallet
wallet = mojowallet.Wallet.get(42)
```

---

## Retrieval

### `Wallet.get(id)`

Get a wallet by integer ID.

```python
wallet = mojowallet.Wallet.get(42)
print(wallet.id, wallet.uuid, wallet.name)
```

**Returns:** `Wallet` instance with attributes: `id`, `uuid`, `name`, `is_active`, `is_locked`

### `Wallet.list(**filters)`

List wallets with optional filtering.

```python
wallets = mojowallet.Wallet.list(is_active=True)
```

### `wallet.refresh()`

Reload wallet data from the server.

---

## Funds Operations

### `wallet.add_funds(amount_units, currency_code, source, **kwargs)`

Add funds (deposit).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount_units` | `int` | Yes | Amount in smallest units |
| `currency_code` | `str` | Yes | Currency code (e.g. `"SC_REAL"`) |
| `source` | `str` | Yes | Source (e.g. `"CREDIT_CARD"`, `"BANK_TRANSFER"`) |
| `category` | `str` | No | Spending category (e.g. `"deposited"`) |
| `can_cashout` | `bool` | No | Whether funds are cashable |
| `reference_id` | `str` | No | External reference |
| `metadata` | `dict` | No | Arbitrary metadata |

```python
txn = wallet.add_funds(1000, "SC_REAL", source="CREDIT_CARD",
                       category="deposited", reference_id="deposit-001")
```

### `wallet.award_reward(amount_units, currency_code, reward_type, **kwargs)`

Award reward/bonus funds.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount_units` | `int` | Yes | Amount |
| `currency_code` | `str` | Yes | Currency code |
| `reward_type` | `str` | Yes | Reward type (e.g. `"signup_bonus"`) |

### `wallet.admin_adjust(amount_units, currency_code, direction, reason, **kwargs)`

Admin balance adjustment.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount_units` | `int` | Yes | Amount |
| `currency_code` | `str` | Yes | Currency code |
| `direction` | `str` | Yes | `"credit"` or `"debit"` |
| `reason` | `str` | Yes | Reason for adjustment |

### `wallet.refund(original_txn, amount_units=None, reason="", **kwargs)`

Refund a previous transaction.

### `wallet.purchase(amount_units, currency_code, merchant, **kwargs)`

Make a purchase (debit).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount_units` | `int` | Yes | Amount |
| `currency_code` | `str` | Yes | Currency code |
| `merchant` | `str` | Yes | Merchant name |

### `wallet.cashout(amount_units, currency_code, reference_id, **kwargs)`

Cash out funds to external destination.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount_units` | `int` | Yes | Amount |
| `currency_code` | `str` | Yes | Currency code |
| `reference_id` | `str` | Yes | External reference |

### `wallet.transfer(to_wallet_id, amount_units, currency_code, **kwargs)`

Transfer funds to another wallet.

---

## Reserve Flow

Three-step pattern for external payouts.

### `wallet.reserve(amount_units, currency_code, hold_currency_code, reference_id, **kwargs)`

Reserve funds (move to hold).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount_units` | `int` | Yes | Amount to reserve |
| `currency_code` | `str` | Yes | Source currency |
| `hold_currency_code` | `str` | Yes | Hold currency (e.g. `"SC_HOLD"`) |
| `reference_id` | `str` | Yes | Reference for confirm/release |
| `expires_in` | `int` | No | Expiry in seconds |

### `wallet.confirm_reservation(reference_id)`

Confirm a pending reservation (finalize).

### `wallet.release_reservation(reference_id)`

Release a reservation (return funds).

```python
wallet.reserve(2500, "SC_REAL", "SC_HOLD", reference_id="payout-001")
# ... later ...
wallet.confirm_reservation("payout-001")
# or
wallet.release_reservation("payout-001")
```

---

## Balance Queries

### `wallet.balance(currency_code)`

Get balance for a currency. Returns integer (units).

```python
balance = wallet.balance("SC_REAL")  # e.g. 5000
```

### `wallet.balance_summary()`

Get balances across all currencies.

### `wallet.cashable(currency_code)`

Get cashable (withdrawable) balance.

### `wallet.spending_power(currency_code)`

Get spending power (balance minus limits).

### `wallet.transactions(**kwargs)`

Get transaction history.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `currency_code` | `str` | No | Filter by currency |
| `limit` | `int` | No | Max records |
| `offset` | `int` | No | Pagination offset |

### `wallet.balance_at(currency_code, timestamp)`

Get historical balance at a timestamp.

### `wallet.transaction_aggregation(currency_code, **kwargs)`

Get aggregated transaction data.

---

## Lock / Unlock

### `wallet.lock(reason="")`

Lock the wallet. All operations blocked until unlocked.

```python
wallet.lock(reason="Chargeback investigation")
```

### `wallet.unlock(reason="")`

Unlock the wallet.

```python
wallet.unlock(reason="Investigation cleared")
```

---

## Promo Codes

### `wallet.redeem_promo(code, reference_id=None, **kwargs)`

Redeem a promotional code.

```python
wallet.redeem_promo("WELCOME100", reference_id="promo-001")
```

---

## Metrics

### `wallet.record_metric(key, **kwargs)`

Record a counter metric.

### `wallet.set_gauge(key, value)`

Set a gauge metric.

### `wallet.get_metric(key, **kwargs)`

Get counter metric data.

### `wallet.get_gauge(key, **kwargs)`

Get gauge value.

---

## Batch Operations

### `Wallet.batch_balances(wallet_ids, currency_code=None)`

Get balances for multiple wallets at once.

```python
balances = mojowallet.Wallet.batch_balances([1, 2, 3], currency_code="SC_REAL")
```
