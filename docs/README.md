# MojoWallet Python SDK Documentation

## Guides

| Doc | Description |
|-----|-------------|
| [Getting Started](getting-started.md) | Install, configure, first request |
| [Wallet Operations](wallet.md) | Full wallet API reference |
| [Sessions](sessions.md) | Concurrency control, context managers |
| [Error Handling](error-handling.md) | Exception hierarchy |
| [Changelog](changelog.md) | Version history |

## Architecture

The SDK is OO — you get a `Wallet` instance and call operations on it:

```python
import mojowallet

mojowallet.configure("api-key")
wallet = mojowallet.Wallet.get(42)
wallet.add_funds(1000, "SC_REAL", source="CREDIT_CARD")
```

### REST Mapping

| SDK Method | REST Endpoint | Purpose |
|-----------|---------------|---------|
| `wallet.add_funds(...)` | `POST /api/wallet/wallet/action/<pk>` | Mutations |
| `wallet.balance(...)` | `GET /api/wallet/wallet/query/<pk>` | Queries |
| `wallet.lock(...)` | `POST /api/wallet/wallet/<pk>` | POST_SAVE_ACTIONS |
| `session.close()` | `POST /api/wallet/session/<pk>` | Session actions |
| `Wallet.batch_balances(...)` | `POST /api/wallet/wallet/batch` | Batch operations |
