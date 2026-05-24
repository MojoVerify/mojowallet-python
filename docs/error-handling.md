# Error Handling

## Exception Hierarchy

```
MojoWalletError (base)
├── Transport / framework
│   ├── AuthError                   # 401 — invalid or missing API key
│   ├── PermissionError             # 403 — insufficient permissions
│   ├── NotFoundError               # 404 — resource not found
│   ├── RateLimitError              # 429 — too many requests
│   └── SessionConflictError        # 400 — active withdraw session exists
└── Wallet errors (5000-block — body-carried code is authoritative)
    ├── WalletInvariantError        # 5001 / 500 — server cross-check failed
    ├── InsufficientBalanceError    # 5002 / 402 — not enough funds
    ├── WalletLockedError           # 5003 / 423 — wallet is locked
    ├── WalletSuspendedError        # 5004 / 423 — wallet is suspended
    ├── WalletInactiveError         # 5005 / 423 — wallet is inactive
    ├── InvalidReferenceError       # 5006 / 400 — malformed reference_id
    └── IdempotentReplayError       # 5007 / 409 — replay with divergent payload
```

## How dispatch works

When a response body carries a `code` in the 5000-block, the SDK raises the
matching subclass **regardless of HTTP status**. This is intentional: the
server registry is the source of truth, and the HTTP status is informational
for non-SDK consumers. The dispatcher runs before the transport-level
401/403/404/429 dispatch, so a 500 with `code=5001` surfaces as
`WalletInvariantError` rather than a generic error.

Responses without a 5000-block `code` fall through to the existing
transport-level dispatch (HTTP-status-based) and a small set of string
heuristics (`"insufficient balance"`, `"active withdraw session"`,
`"locked … wallet"`) on 400 responses.

## Usage

```python
from mojowallet.exceptions import (
    MojoWalletError,
    InsufficientBalanceError,
    SessionConflictError,
    WalletInvariantError,
    WalletLockedError,
    WalletSuspendedError,
    WalletInactiveError,
    InvalidReferenceError,
    IdempotentReplayError,
)

try:
    wallet.spend(10000, "SC", reference_id="bet-001")
except InsufficientBalanceError as e:
    print(f"Not enough funds: {e.message}")
    if e.available is not None:
        print(f"Available: {e.available}, Required: {e.required}")
except (WalletLockedError, WalletSuspendedError, WalletInactiveError) as e:
    print(f"Wallet is unavailable: {e.message}")
except InvalidReferenceError as e:
    print(f"Bad reference_id: {e.message}")
except WalletInvariantError:
    # Never surface raw text — the server masks the diff, the SDK reinforces.
    print("Wallet temporarily unavailable, please retry")
except IdempotentReplayError:
    print("Replay with divergent payload — investigate the duplicate request")
except MojoWalletError as e:
    print(f"API error {e.status_code}: {e.message}")
```

## Exception Attributes

### `MojoWalletError` (base)

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Human-readable error message |
| `status_code` | `int` | HTTP status code |
| `code` | `int` | Numeric error code (5000-block for wallet errors) |

### `InsufficientBalanceError`

| Attribute | Type | Description |
|-----------|------|-------------|
| `available` | `int` | Available balance (when the server includes it) |
| `required` | `int` | Required amount (when the server includes it) |

### `WalletSuspendedError`

| Attribute | Type | Description |
|-----------|------|-------------|
| `suspended_until` | `str` | ISO8601 timestamp (when the server includes it) |

### `RateLimitError`

| Attribute | Type | Description |
|-----------|------|-------------|
| `retry_after` | `int` | Seconds to wait before retrying |

### `WalletInvariantError`

No additional attributes. The message is **always** the canned
`"Wallet balance check failed — please retry"` — caller-supplied or
server-supplied detail is deliberately ignored so safety-critical
balance-check failures don't leak internal state. Callers should surface a
"please retry" UX, never raw exception text.
