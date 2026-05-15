# Error Handling

## Exception Hierarchy

```
MojoWalletError (base)
├── AuthError                    # 401 — invalid or missing API key
├── InsufficientBalanceError     # 400 — not enough funds
├── SessionConflictError         # 400 — active withdraw session exists
├── WalletLockedError            # 400 — wallet is locked
├── PermissionError              # 403 — insufficient permissions
├── NotFoundError                # 404 — resource not found
├── RateLimitError               # 429 — too many requests
```

## Usage

```python
from mojowallet.exceptions import (
    MojoWalletError,
    AuthError,
    InsufficientBalanceError,
    SessionConflictError,
    WalletLockedError,
)

try:
    wallet.cashout(10000, "SC_REAL", reference_id="cashout-001")
except InsufficientBalanceError as e:
    print(f"Not enough funds: {e.message}")
    print(f"Available: {e.available}, Required: {e.required}")
except WalletLockedError:
    print("Wallet is locked — contact support")
except SessionConflictError:
    print("Close your existing session first")
except AuthError:
    print("Check your API key")
except MojoWalletError as e:
    print(f"API error {e.status_code}: {e.message}")
```

## Exception Attributes

### `MojoWalletError` (base)

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Human-readable error message |
| `status_code` | `int` | HTTP status code |
| `code` | `str` | Machine-readable error code |

### `InsufficientBalanceError`

| Attribute | Type | Description |
|-----------|------|-------------|
| `available` | `int` | Available balance (if provided) |
| `required` | `int` | Required amount (if provided) |

### `RateLimitError`

| Attribute | Type | Description |
|-----------|------|-------------|
| `retry_after` | `int` | Seconds to wait before retrying |
