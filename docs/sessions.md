# Sessions

Sessions provide concurrency control for wallet operations. Only one active withdraw session per wallet at a time, preventing concurrent withdrawal races.

## Context Manager (Recommended)

```python
with wallet.session("game-xyz", expires_in_seconds=3600) as session:
    session.withdraw(500, "SC_REAL", reference_id="bet-001")
    session.withdraw(300, "SC_REAL", reference_id="bet-002")
    session.extend(1800)
# session auto-closed on exit
```

The session is automatically closed when the `with` block exits, even if an exception occurs.

## Manual Lifecycle

```python
session = wallet.start_session("game-xyz", expires_in_seconds=3600)
session.withdraw(500, "SC_REAL", reference_id="bet-001")
session.close()
```

---

## `wallet.session(session_id, **kwargs)`

Start a session as a context manager.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | `str` | Yes | Unique external session identifier |
| `expires_in_seconds` | `int` | No | Session expiry in seconds |
| `can_withdraw` | `bool` | No | Whether session allows withdrawals (default `True`) |
| `metadata` | `dict` | No | Arbitrary metadata |

**Returns:** `Session` (context manager)

## `wallet.start_session(session_id, **kwargs)`

Start a session with manual lifecycle. Same parameters as `session()`.

**Returns:** `Session`

---

## Session Methods

### `session.withdraw(amount_units, currency_code, reference_id, **kwargs)`

Withdraw funds within this session.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount_units` | `int` | Yes | Amount |
| `currency_code` | `str` | Yes | Currency code |
| `reference_id` | `str` | Yes | Unique reference for this withdrawal |

### `session.extend(duration)`

Extend the session expiry.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `duration` | `int` | Yes | Extension in seconds |

### `session.close()`

Close the session. Idempotent — safe to call multiple times.

---

## Concurrency Rules

- Only **one active withdraw session** per wallet at a time (DB constraint)
- Starting a second withdraw session raises `SessionConflictError`
- Expired sessions are automatically cleaned up
- Multiple deposit-only sessions are allowed

```python
from mojowallet.exceptions import SessionConflictError

try:
    with wallet.session("game-2") as s:
        s.withdraw(100, "SC_REAL", reference_id="bet-x")
except SessionConflictError:
    print("Another session is already active")
```

## Session Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `int` | Session integer ID |
| `uuid` | `str` | Session UUID |
| `session_id` | `str` | External session identifier |
