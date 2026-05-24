# mojowallet-python SDK update for wallet hardening Phase 2

- **Type**: request
- **Status**: resolved
- **Date**: 2026-05-23
- **Resolved**: 2026-05-23 — released as v2.3.0
- **Priority**: high
- **Cross-repo source**: `../mverify_api/planning/requests/wallet-hardening.md` (Phase 7)
- **Pinned API commit**: `a3f9a57` on `main` of `mverify_api` (Phase 2 landed — root_code rename, root-grouped balances, get_holdings/get_root_balance, WalletError registry)
- **Target SDK version**: bump from 2.2.1 → 2.3.0 (SemVer minor — additive methods + breaking response-shape change for `balance_summary`)

## Description

The mverify_api wallet hardening initiative landed Phase 2 — structural changes to the wallet's balance-read APIs and a new numeric error-code registry. The SDK needs five changes to track:

1. A new typed `Wallet.spend(amount_units, root_code, reference_id, **kwargs)` method (today callers use the generic `wallet.action("spend", ...)`).
2. Exception subclasses for the API's 5000-block error codes, with a response-dispatcher that picks the right subclass off the response payload.
3. New read methods `Wallet.get_holdings(...)` and `Wallet.get_root_balance(root_code)` — thin wrappers over the new `q=holdings` and `q=root_balance` REST queries.
4. README + CHANGELOG updates documenting the new `balance_summary` response shape (`balances` is now keyed by `root_code`, not `currency_code`). This is a breaking shape change for any caller parsing `resp.balances[currency_code]`.
5. Bump version 2.2.1 → 2.3.0.

This request is the first SDK feature delivered through a planning/request workflow — the repo had no `planning/` directory before. Future SDK requests follow this template.

## Context

### What's locked in the API

Pin against `mverify_api` commit `a3f9a57` on `main`. Phase 2 of `mverify_api/planning/requests/wallet-hardening.md` landed and the wire contract is stable for the duration of Phases 3–6 (which are additive).

#### New `balance_summary` response

```json
{
  "wallet_uuid": "...",
  "wallet_name": "...",
  "customer": {"email": "...", "name": "..."},
  "balances": {
    "SC": {
      "available": 200000,
      "total":     215000,
      "by_code": {
        "SC_REAL":  {"quantity": 150000, "formatted": "$1500.00"},
        "SC_BONUS": {"quantity":  50000, "formatted":  "$500.00"},
        "SC_HOLD":  {"quantity":  15000, "formatted":  "$150.00"}
      }
    },
    "GC": { ... }
  },
  "total_by_currency": {
    "SC_REAL":  {"quantity": 150000, "formatted": "$1500.00"},
    "SC_BONUS": {"quantity":  50000, "formatted":  "$500.00"},
    ...
  },
  "cashable_by_currency": {
    "SC_REAL": 100000, ...
  },
  "is_active": true, "is_locked": false, "is_suspended": false,
  "suspended_until": null
}
```

**Breaking for callers reading `resp.balances[currency_code]`** — `balances` is now keyed by `root_code`. The per-currency rollup moved to `total_by_currency` (which was already present and is preserved as-is — wmx_api consumes only this field).

#### New queries

- `GET /api/wallet/wallet/query/<pk>?q=holdings` → `{holdings: [...]}` — raw per-holding list.
- `GET /api/wallet/wallet/query/<pk>?q=root_balance&root_code=SC` → `{root_balance: {available, total, by_code}}`.

#### New error-code registry (5000-block)

REST error responses carry `{"status": false, "error": "...", "code": NNNN}` with HTTP status matching the registry:

| Code | HTTP | Class (proposed SDK name) | When raised |
|---|---|---|---|
| 5001 | 500 | `WalletInvariantError` | Server-side cross-check failure. Generic message only — caller should retry, never display raw text. |
| 5002 | 402 | `InsufficientBalanceError` | Spend or purchase exceeds available balance. |
| 5003 | 423 | `WalletLockedError` | Wallet is locked. |
| 5004 | 423 | `WalletSuspendedError` | Wallet is suspended until a future time. |
| 5005 | 423 | `WalletInactiveError` | Wallet has been deactivated. |
| 5006 | 400 | `InvalidReferenceError` | `reference_id` malformed (missing, contains `#`, etc.). |
| 5007 | 409 | `IdempotentReplayError` | Replay detected with the same `reference_id` but a different payload. |

#### `wallet.spend` is renamed at the API

`wallet.action("spend", spend_group="SC", ...)` → `wallet.action("spend", root_code="SC", ...)`. The SDK's typed wrapper takes `root_code`.

### Current SDK state

Inspected at `mojowallet-python` HEAD:

- **[mojowallet/wallet.py:103–138](mojowallet/wallet.py:103)** — `purchase`, `cashout`, `transfer`, `reserve` are typed wrappers. **No `spend` wrapper today** — callers fall back to `wallet.action("spend", ...)`.
- **[mojowallet/wallet.py:147](mojowallet/wallet.py:147)** — `balance_summary()` is a passthrough; it returns whatever the server returns. Works with the new shape but doesn't introspect.
- **[mojowallet/exceptions.py](mojowallet/exceptions.py)** — has `MojoWalletError` base with a `code` field (line 6) that's never populated; subclasses `InsufficientBalanceError`, `WalletLockedError`, `SessionConflictError`, `RateLimitError`, `NotFoundError`, `PermissionError`. None map to the 5000-block.
- **[mojowallet/_client.py](mojowallet/_client.py)** — the response-handling path that translates non-2xx responses into exceptions. The dispatch lives there.

## Acceptance Criteria

### 1. New typed `Wallet.spend` method

- [ ] Add `Wallet.spend(amount_units, root_code, reference_id, *, merchant="", metadata=None)` in [mojowallet/wallet.py](mojowallet/wallet.py). Signature mirrors the server-side `wallet_ops.spend.spend`.
- [ ] Implementation: thin wrapper over `self._action("spend", amount_units=..., root_code=..., reference_id=..., merchant=..., metadata=...)`. Returns the response (a `{"transactions": [...]}` envelope — match the existing `purchase` / `transfer` return convention).
- [ ] Validate `reference_id` client-side (non-empty, no `#`) before the round-trip so the SDK fails fast on the same constraints the server enforces. Raise `InvalidReferenceError` (code 5006) locally on violation.
- [ ] Docstring documents the priority spend ordering (lower `currency.spend_priority` first within the family, then per-holding `created` ascending — once Phase 4 lands, also `holding.spend_priority`).

### 2. Exception registry update

- [ ] Update [mojowallet/exceptions.py](mojowallet/exceptions.py):
  - Set `class WalletInvariantError(MojoWalletError)` with `code = 5001`, `status_code = 500`. Default message: `"Wallet balance check failed — please retry"`. Do NOT accept caller-supplied detail in the message (the API masks the cross-check diff; the SDK should not invent one).
  - Update `InsufficientBalanceError` — set `code = 5002`, `status_code = 402` (was 400). Keep the `available` / `required` kwargs.
  - Update `WalletLockedError` — set `code = 5003`, `status_code = 423` (was 400).
  - Add `WalletSuspendedError(MojoWalletError)` — `code = 5004`, `status_code = 423`. Default message `"Wallet is suspended"`. Optional `suspended_until` kwarg.
  - Add `WalletInactiveError(MojoWalletError)` — `code = 5005`, `status_code = 423`.
  - Add `InvalidReferenceError(MojoWalletError)` — `code = 5006`, `status_code = 400`.
  - Add `IdempotentReplayError(MojoWalletError)` — `code = 5007`, `status_code = 409`.
- [ ] Keep `AuthError`, `SessionConflictError`, `RateLimitError`, `NotFoundError`, `PermissionError` as-is (they aren't in the 5000-block; they're transport / framework errors).

### 3. Response dispatcher

- [ ] Add a `_dispatch_wallet_error(response)` helper (in `_client.py` or a new `_errors.py`) that takes a parsed response payload and:
  - If `response.get("status") is True`, return — not an error.
  - If `response.get("code")` is in `{5001..5007}`, raise the matching subclass with `message=response.get("error", "")` and any subclass-specific fields populated from the response payload (e.g., `available` / `required` for 5002 if the server adds them later).
  - Otherwise fall through to the existing dispatch (HTTP-status-based).
- [ ] Wire the dispatcher into the existing response path in [mojowallet/_client.py](mojowallet/_client.py) — wherever the SDK currently raises on a `{"status": false}` body. Confirm the dispatcher runs BEFORE the existing HTTP-status check so a 500 with `code=5001` is raised as `WalletInvariantError`, not a generic `MojoWalletError`.

### 4. New read methods

- [ ] `Wallet.get_holdings(currency_code=None, root_code=None, include_expired=False)`. Thin wrapper over `self._query("holdings", **filters)`. Return value is the `holdings` list extracted from the response (match the existing `balance()` / `cashable()` convention of unwrapping single-key responses).
- [ ] `Wallet.get_root_balance(root_code)`. Thin wrapper over `self._query("root_balance", root_code=root_code)`. Returns the `root_balance` dict from the response.

### 5. Tests

- [ ] Extend `tests/` to cover:
  - The new `spend` method — happy path (200 with a `{"transactions": [...]}` body), client-side validation (empty reference_id, `#` in reference_id raises `InvalidReferenceError`).
  - The new `get_holdings` and `get_root_balance` methods — happy path, parameter passthrough.
  - The error dispatcher — one test per code in the 5000-block. Mock the HTTP layer; build response payloads carrying `code=NNNN`; assert the matching subclass is raised with the right `code`, `status_code`, and message.
  - The shape change in `balance_summary` — confirm a sample response with the new shape (`balances[root_code]`) deserializes without errors and exposes both `balances` (root-grouped) and `total_by_currency` (per-currency).
- [ ] No live API dependency in tests — all use the SDK's existing mock pattern.

### 6. Documentation

- [ ] Update [README.md](README.md):
  - Add a "Balance reads" section documenting the new shape with a JSON example.
  - Add an "Error codes" subsection mapping the 5000-block to exception classes.
  - Add examples for `wallet.spend(...)`, `wallet.get_holdings(...)`, `wallet.get_root_balance(...)`.
  - Flag the breaking change in `balance_summary.balances` keying for anyone upgrading from 2.2.x.
- [ ] Update [CHANGELOG.md](CHANGELOG.md) with a 2.3.0 entry listing:
  - New `Wallet.spend`, `Wallet.get_holdings`, `Wallet.get_root_balance` methods.
  - New exception subclasses (`WalletInvariantError`, `WalletSuspendedError`, `WalletInactiveError`, `InvalidReferenceError`, `IdempotentReplayError`).
  - Updated codes/statuses on `InsufficientBalanceError` (now 5002 / HTTP 402) and `WalletLockedError` (now 5003 / HTTP 423).
  - `balance_summary.balances` keying changed from currency code to `root_code` — breaking for callers parsing that field.
- [ ] Bump `[tool.poetry] version = "2.3.0"` in [pyproject.toml](pyproject.toml).

## Implementation notes

- **`code` is the source of truth for dispatch.** The SDK has always carried `code` on `MojoWalletError` (it was unused). Now the API populates it on every wallet error response. The dispatcher should ignore the HTTP status when `code` is in the 5000-block and trust the registry — the HTTP status is informational for the client.
- **`WalletInvariantError` message stays generic.** The API server masks the cross-check diff at the REST boundary (see commit `b49cc8d` in `mverify_api`); the SDK reinforces by ignoring any caller-supplied detail. Calling code should `except WalletInvariantError` and surface a "please retry" UX, never raw exception text.
- **Don't add a `withdraw` wrapper now.** The wallet has both `withdraw` and `cashout` actions; the SDK has `cashout` (via [wallet.py:111](mojowallet/wallet.py:111)) but no `withdraw` typed wrapper. Out of scope for this request.

## Out of scope

- The portal-side updates — those live in two separate requests (`../mverify_portal/planning/requests/wallet-admin-views.md` and `../wmx_portal/planning/requests/055-wallet-display-shape-updates.md`).
- The wmx_api wallet-service updates — those are tracked under `../wmx_api/planning/requests/45-wmx-wallet-contract-hardening.md`.
- Per-holding `spend_priority` editing (Phase 4 of the API hardening — separate SDK update when it lands).
- Reconciliation cron exposure (Phase 6 of the API hardening — separate SDK update if/when needed; likely not, since reconciliation is server-side).
- Any Twisted/async variant of the SDK — `mojowallet-python` is the sync requests-based SDK; an async client is a separate request.

## Related work

- `../mverify_api/planning/requests/wallet-hardening.md` — origin initiative. Phase 2 landed and locked the API contract this SDK update consumes. Phases 3–6 are additive and won't reshape the wire format further.
- `../mverify_portal/planning/requests/wallet-admin-views.md` — sibling portal-side request consuming the same contract.
- `../wmx_portal/planning/requests/055-wallet-display-shape-updates.md` — sibling wmx-portal request, downstream of wmx_api hardening.
- `../wmx_api/planning/requests/45-wmx-wallet-contract-hardening.md` — wmx-side companion to the API hardening; tightens wmx parsers against the new contract.

---

## Plan

### Objective

Ship `mojowallet-python` 2.3.0 against the API contract pinned at `mverify_api@a3f9a57`. Five deliverables: typed `Wallet.spend`, code-based exception dispatcher for the 5000-block registry, two new read methods (`get_holdings`, `get_root_balance`), updated exception subclasses, and refreshed README / CHANGELOG / docs / `pyproject.toml` version.

### File-level steps

#### Step 1 — Refactor [mojowallet/exceptions.py](../mojowallet/exceptions.py)

Restructure so each subclass declares `code` and `status_code` as class attributes (mirrors the server-side `WalletError` pattern in `mverify_api/apps/mojopay/wallet/exceptions.py`). The base `__init__` reads them so subclasses don't need to repeat the values in every constructor.

```python
class MojoWalletError(Exception):
    code = None
    status_code = None
    default_message = "Wallet error"

    def __init__(self, message=None, status_code=None, code=None):
        msg = message or self.default_message
        super().__init__(msg)
        self.message = msg
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code

    def __repr__(self):
        return f"{self.__class__.__name__}({self.status_code}: {self.message})"
```

Existing subclasses to restamp:

- `InsufficientBalanceError` — `code = 5002`, `status_code = 402`, accept `available=None`, `required=None`.
- `WalletLockedError` — `code = 5003`, `status_code = 423`.
- `AuthError` — leave at `status_code = 401` (no 5000-code; transport-level).
- `SessionConflictError` — leave at `status_code = 400` (not in 5000-block; raised by string-heuristic dispatch).
- `RateLimitError` — leave at `status_code = 429`.
- `NotFoundError` — leave at `status_code = 404`.
- `PermissionError` — leave at `status_code = 403`.

New subclasses to add:

- `WalletInvariantError(MojoWalletError)` — `code = 5001`, `status_code = 500`, `default_message = "Wallet balance check failed — please retry"`. **Do not** accept a caller-supplied detail in the message — the server masks the cross-check diff, the SDK must not reinvent one. The constructor signature is `__init__(self, message=None)` and any non-None `message` is **ignored** (forced to `default_message`) to enforce the rule even if the dispatcher tries to pass the server's `error` field.
- `WalletSuspendedError(MojoWalletError)` — `code = 5004`, `status_code = 423`, accept `suspended_until=None`.
- `WalletInactiveError(MojoWalletError)` — `code = 5005`, `status_code = 423`.
- `InvalidReferenceError(MojoWalletError)` — `code = 5006`, `status_code = 400`.
- `IdempotentReplayError(MojoWalletError)` — `code = 5007`, `status_code = 409`.

#### Step 2 — Create [mojowallet/_errors.py](../mojowallet/_errors.py)

```python
"""Wallet error-code registry + dispatcher.

Mirrors the server-side registry in mverify_api/apps/mojopay/wallet/exceptions.py.
Codes are the source of truth — when the response body carries a 5000-block code,
the SDK raises the matching subclass regardless of HTTP status.
"""
from .exceptions import (
    InsufficientBalanceError,
    InvalidReferenceError,
    IdempotentReplayError,
    WalletInactiveError,
    WalletInvariantError,
    WalletLockedError,
    WalletSuspendedError,
)


WALLET_CODE_REGISTRY = {
    5001: WalletInvariantError,
    5002: InsufficientBalanceError,
    5003: WalletLockedError,
    5004: WalletSuspendedError,
    5005: WalletInactiveError,
    5006: InvalidReferenceError,
    5007: IdempotentReplayError,
}


# Per-class extra fields the dispatcher copies from the body (if present).
_EXTRA_FIELDS = {
    InsufficientBalanceError: ("available", "required"),
    WalletSuspendedError:     ("suspended_until",),
}


def dispatch_wallet_error(body):
    """If ``body`` carries a 5000-block ``code``, raise the matching subclass.

    Returns None when no dispatch should happen (no code, not in registry).
    Callers handle the fallthrough.
    """
    if not isinstance(body, dict):
        return
    code = body.get("code")
    cls = WALLET_CODE_REGISTRY.get(code)
    if cls is None:
        return
    # WalletInvariantError ignores the server message on purpose.
    if cls is WalletInvariantError:
        raise cls()
    msg = body.get("error") or body.get("message")
    extras = {k: body[k] for k in _EXTRA_FIELDS.get(cls, ()) if k in body}
    raise cls(message=msg, **extras)
```

#### Step 3 — Wire dispatcher into [mojowallet/_client.py](../mojowallet/_client.py)

Two integration points:

**`_process_body`** (currently raises `MojoWalletError` on `{"status": false}` envelopes — see [_client.py:167-174](../mojowallet/_client.py:167)):

```python
def _process_body(self, body, status_code):
    if isinstance(body, dict) and "status" in body:
        if not body["status"]:
            dispatch_wallet_error(body)  # raises if code matches
            msg = body.get("error") or body.get("message") or "API error"
            raise MojoWalletError(msg, status_code=status_code, code=body.get("code"))
        return _wrap(body.get("data", body))
    return _wrap(body)
```

**`_raise_for_status`** (currently runs transport-level dispatch first — see [_client.py:185-213](../mojowallet/_client.py:185)). Insert dispatch as the very first step so a 500 with `code=5001` becomes `WalletInvariantError`, not generic, and a 423 with `code=5003` doesn't fall through to the unsupported-status branch:

```python
def _raise_for_status(self, status_code, body, headers, raw_text=""):
    dispatch_wallet_error(body)  # earliest exit — code is authoritative
    if status_code == 401:
        raise AuthError("Invalid or expired API key.", status_code=401)
    # ... existing 403/404/429 branches unchanged ...
    # ... existing string-heuristic 400 fallbacks unchanged ...
```

Add `from ._errors import dispatch_wallet_error` at the top.

Keep the existing string-heuristic fallback for `InsufficientBalanceError` / `SessionConflictError` / `WalletLockedError` on a 400 with no `code` — defensive for any older or non-wallet endpoint that returns those phrasings. Existing `test_400_*` tests remain green.

#### Step 4 — Add three methods to [mojowallet/wallet.py](../mojowallet/wallet.py)

Insert `spend` in the Withdrawals section (after `cashout`, before `transfer`):

```python
def spend(self, amount_units, root_code, reference_id, *, merchant="", metadata=None):
    """Spend funds from a currency family (e.g. ``"SC"``).

    The server walks the family's holdings in priority order
    (currency ``spend_priority`` ascending, then holding ``created``
    ascending) and debits across as many holdings as needed.

    Idempotent on ``reference_id``: a replay returns the original
    transactions instead of double-debiting.

    Raises ``InvalidReferenceError`` (5006) locally if ``reference_id`` is
    empty or contains ``'#'`` — the server enforces the same constraint.
    """
    if not reference_id:
        raise InvalidReferenceError("reference_id is required for spend")
    if '#' in reference_id:
        raise InvalidReferenceError("reference_id must not contain '#'")
    return self._action(
        "spend",
        amount_units=amount_units,
        root_code=root_code,
        reference_id=reference_id,
        merchant=merchant,
        metadata=metadata,
    )
```

Add `get_holdings` and `get_root_balance` in the Balance Queries section (after `spending_power`):

```python
def get_holdings(self, currency_code=None, root_code=None, include_expired=False):
    """List per-holding balances. Filter by ``currency_code`` or
    ``root_code``; both optional. Returns the holdings list."""
    params = {}
    if currency_code is not None:
        params["currency_code"] = currency_code
    if root_code is not None:
        params["root_code"] = root_code
    if include_expired:
        params["include_expired"] = True
    result = self._query("holdings", **params)
    return result.holdings if hasattr(result, "holdings") else result

def get_root_balance(self, root_code):
    """Get aggregated balance for a currency family (e.g. ``"SC"``).

    Returns a dict with ``available``, ``total``, and ``by_code`` (per-currency
    breakdown within the family)."""
    result = self._query("root_balance", root_code=root_code)
    return result.root_balance if hasattr(result, "root_balance") else result
```

Update `balance_summary` docstring to document the new shape:

```python
def balance_summary(self):
    """Get full balance summary across all currency families.

    Response shape (since API a3f9a57)::

        {
          "balances": {                  # KEYED BY ROOT_CODE
            "SC": {"available": ..., "total": ..., "by_code": {...}},
            "GC": {...},
          },
          "total_by_currency": {         # keyed by currency_code
            "SC_REAL": {"quantity": ..., "formatted": ...},
            ...
          },
          "cashable_by_currency": {"SC_REAL": ..., ...},
          "is_active": bool, "is_locked": bool,
          "is_suspended": bool, "suspended_until": iso8601|null,
        }

    BREAKING CHANGE vs 2.2.x: ``balances`` was previously keyed by
    currency_code; it is now keyed by root_code. Per-currency rollups
    moved to ``total_by_currency`` (which existed before and is preserved)."""
    return self._query("balance_summary")
```

Add `from .exceptions import InvalidReferenceError` at the top of `wallet.py`.

#### Step 5 — Update [mojowallet/__init__.py](../mojowallet/__init__.py)

- Bump `__version__ = "2.3.0"`.
- Add the five new exception classes to the imports and `__all__`.

#### Step 6 — Bump [pyproject.toml](../pyproject.toml)

- `version = "2.3.0"`.

#### Step 7 — Tests

**[tests/test_exceptions.py](../tests/test_exceptions.py)** — update existing assertions and add new subclasses:

- `test_insufficient_balance_error` → assert `status_code == 402` and `code == 5002`.
- `test_wallet_locked_error` → assert `status_code == 423` and `code == 5003`.
- New `test_wallet_invariant_error` — assert `code == 5001`, `status_code == 500`, message is the canned default even if caller passes one.
- New `test_wallet_suspended_error` — assert `code == 5004`, `status_code == 423`, `suspended_until` kwarg accepted.
- New `test_wallet_inactive_error` — assert `code == 5005`, `status_code == 423`.
- New `test_invalid_reference_error` — assert `code == 5006`, `status_code == 400`.
- New `test_idempotent_replay_error` — assert `code == 5007`, `status_code == 409`.
- Update `test_base_error_attributes` to use a numeric code (registry is ints now, not strings like `"BAD_REQUEST"`).
- Update `test_all_inherit_from_base` to include the five new classes.

**[tests/test_client.py](../tests/test_client.py)** — new `TestWalletErrorDispatch` class. One test per 5000-block code. Each builds a body `{"status": False, "error": "...", "code": NNNN, ...}` with the matching HTTP status from the registry, and asserts the right subclass is raised with `code`, `status_code`, and (where applicable) extras populated.

```python
class TestWalletErrorDispatch:
    @pytest.mark.parametrize("code,status,exc_cls", [
        (5001, 500, WalletInvariantError),
        (5002, 402, InsufficientBalanceError),
        (5003, 423, WalletLockedError),
        (5004, 423, WalletSuspendedError),
        (5005, 423, WalletInactiveError),
        (5006, 400, InvalidReferenceError),
        (5007, 409, IdempotentReplayError),
    ])
    def test_code_dispatch(self, code, status, exc_cls):
        c = Client(api_key="k", fake_mode=True)
        c.register_fake_responder(
            lambda *a: True,
            {"status_code": status, "body": {"status": False, "error": "boom", "code": code}},
        )
        with pytest.raises(exc_cls) as ei:
            c.post("wallet/action/1")
        assert ei.value.code == code, f"expected code {code}, got {ei.value.code}"
        assert ei.value.status_code == status, f"expected status {status}, got {ei.value.status_code}"

    def test_5002_extras_populated(self):
        c = Client(api_key="k", fake_mode=True)
        c.register_fake_responder(
            lambda *a: True,
            {"status_code": 402, "body": {
                "status": False, "error": "Insufficient", "code": 5002,
                "available": 100, "required": 500,
            }},
        )
        with pytest.raises(InsufficientBalanceError) as ei:
            c.post("wallet/action/1")
        assert ei.value.available == 100, "available should be populated from body"
        assert ei.value.required == 500, "required should be populated from body"

    def test_5001_message_is_canned(self):
        """WalletInvariantError must never echo the server's error text."""
        c = Client(api_key="k", fake_mode=True)
        c.register_fake_responder(
            lambda *a: True,
            {"status_code": 500, "body": {
                "status": False, "error": "internal diff: SC_REAL mismatch", "code": 5001,
            }},
        )
        with pytest.raises(WalletInvariantError) as ei:
            c.post("wallet/action/1")
        assert "diff" not in ei.value.message, "server detail must be suppressed"
        assert "retry" in ei.value.message.lower(), "canned retry message expected"

    def test_envelope_error_dispatches_before_generic(self):
        """A 200 with status=false + code=5002 raises InsufficientBalanceError, not MojoWalletError."""
        c = Client(api_key="k", fake_mode=True)
        c.register_fake_responder(
            lambda *a: True,
            {"status_code": 200, "body": {"status": False, "error": "no funds", "code": 5002}},
        )
        with pytest.raises(InsufficientBalanceError):
            c.post("wallet/action/1")
```

The existing `test_400_insufficient_balance` / `test_400_session_conflict` / `test_400_wallet_locked` stay as-is — they test the string-heuristic fallback (their bodies carry no `code`). Confirm they still pass after the dispatcher is wired in.

**[tests/test_wallet.py](../tests/test_wallet.py)** — add coverage for the three new methods:

```python
class TestWalletSpend:
    def _w(self, client):
        return Wallet(_wallet_data(), client)

    def test_spend_happy_path(self, client, captured):
        _respond(client, {"transactions": [{"id": 100}, {"id": 101}]})
        result = self._w(client).spend(750, "SC", reference_id="game-bet-001", merchant="Casino")
        p = captured[-1]["payload"]
        assert p["action"] == "spend", "payload should dispatch the spend action"
        assert p["root_code"] == "SC", "root_code passthrough"
        assert p["reference_id"] == "game-bet-001", "reference_id passthrough"
        assert p["merchant"] == "Casino", "merchant passthrough"
        assert len(result.transactions) == 2, "spend returns the transactions envelope"

    def test_spend_rejects_empty_reference(self, client):
        from mojowallet.exceptions import InvalidReferenceError
        with pytest.raises(InvalidReferenceError):
            self._w(client).spend(100, "SC", reference_id="")

    def test_spend_rejects_hash_in_reference(self, client):
        from mojowallet.exceptions import InvalidReferenceError
        with pytest.raises(InvalidReferenceError):
            self._w(client).spend(100, "SC", reference_id="bet#1")


class TestWalletNewQueries:
    def _w(self, client):
        return Wallet(_wallet_data(), client)

    def test_get_holdings_no_filters(self, client, captured):
        _respond(client, {"holdings": [{"id": 1}, {"id": 2}]})
        result = self._w(client).get_holdings()
        assert captured[-1]["payload"] == {"q": "holdings"}, "no filters means just q=holdings"
        assert len(result) == 2, "should unwrap the holdings list"

    def test_get_holdings_with_filters(self, client, captured):
        _respond(client, {"holdings": [{"id": 1}]})
        self._w(client).get_holdings(currency_code="SC_REAL", root_code="SC", include_expired=True)
        p = captured[-1]["payload"]
        assert p["q"] == "holdings"
        assert p["currency_code"] == "SC_REAL", "currency_code passthrough"
        assert p["root_code"] == "SC", "root_code passthrough"
        assert p["include_expired"] is True, "include_expired passthrough"

    def test_get_root_balance(self, client, captured):
        _respond(client, {"root_balance": {"available": 200000, "total": 215000, "by_code": {}}})
        result = self._w(client).get_root_balance("SC")
        assert captured[-1]["payload"] == {"q": "root_balance", "root_code": "SC"}
        assert result.available == 200000, "root_balance dict returned"


class TestBalanceSummaryShape:
    def _w(self, client):
        return Wallet(_wallet_data(), client)

    def test_new_shape_deserializes(self, client):
        _respond(client, {
            "wallet_uuid": "wlt-abc",
            "balances": {
                "SC": {"available": 200000, "total": 215000, "by_code": {
                    "SC_REAL":  {"quantity": 150000, "formatted": "$1500.00"},
                    "SC_BONUS": {"quantity":  50000, "formatted":  "$500.00"},
                }},
            },
            "total_by_currency": {
                "SC_REAL": {"quantity": 150000, "formatted": "$1500.00"},
            },
            "cashable_by_currency": {"SC_REAL": 100000},
            "is_active": True, "is_locked": False, "is_suspended": False,
            "suspended_until": None,
        })
        s = self._w(client).balance_summary()
        assert s.balances.SC.available == 200000, "balances is root-keyed"
        assert s.balances.SC.by_code.SC_REAL.quantity == 150000, "by_code is currency-keyed"
        assert s.total_by_currency.SC_REAL.quantity == 150000, "per-currency rollup preserved"
```

**Run command** (from `mojowallet-python/`): `pytest -v` — unit tests only, no API key required (all use fake mode).

#### Step 8 — Documentation

**[README.md](../README.md)** — add three sections after "Usage Examples":

```markdown
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
`root_code` (was `currency_code`). Callers that read `s.balances["SC_REAL"]`
must switch to `s.total_by_currency["SC_REAL"]` or `s.balances["SC"].by_code["SC_REAL"]`.

### Error codes

Wallet errors carry a numeric `code` (5000-block) and an HTTP status from
the table below. The SDK raises a matching subclass when the response body
includes a `code` in this range — the dispatch is authoritative.

| Code | HTTP | Class |
|---|---|---|
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
```

**[CHANGELOG.md](../CHANGELOG.md)** — prepend a 2.3.0 entry:

```markdown
## v2.3.0 - 2026-05-23

Adds wallet-hardening Phase 2 support (mverify_api@a3f9a57).

### Added
- `Wallet.spend(amount_units, root_code, reference_id, *, merchant="", metadata=None)` —
  typed wrapper for the spend action. Validates `reference_id` client-side
  (non-empty, no `#`) and raises `InvalidReferenceError` locally on violation.
- `Wallet.get_holdings(currency_code=None, root_code=None, include_expired=False)` —
  per-holding list from the new `q=holdings` query.
- `Wallet.get_root_balance(root_code)` — family-aggregated balance from the
  new `q=root_balance` query.
- Exception subclasses: `WalletInvariantError` (5001/500),
  `WalletSuspendedError` (5004/423), `WalletInactiveError` (5005/423),
  `InvalidReferenceError` (5006/400), `IdempotentReplayError` (5007/409).
- Code-based error dispatcher — when the response body carries a 5000-block
  `code`, the SDK raises the matching subclass regardless of HTTP status.

### Changed
- `InsufficientBalanceError` — now `code = 5002`, `status_code = 402` (was 400).
- `WalletLockedError` — now `code = 5003`, `status_code = 423` (was 400).
- `MojoWalletError.code` is now a class-level int (5000-block) instead of an
  unused string slot on the base.

### Breaking
- `balance_summary().balances` is now keyed by `root_code` instead of
  `currency_code`. Per-currency rollups remain available under
  `balance_summary().total_by_currency` (unchanged from 2.2.x). Update any
  code reading `summary.balances["SC_REAL"]` to either
  `summary.total_by_currency["SC_REAL"]` or
  `summary.balances["SC"].by_code["SC_REAL"]`.
```

**[docs/wallet.md](../docs/wallet.md)** — add a "Spend" subsection in the Withdrawals area with `Wallet.spend` reference; add `get_holdings` and `get_root_balance` to Balance Queries; update `balance_summary` to describe the root-keyed shape and link to the breaking-change note.

**[docs/error-handling.md](../docs/error-handling.md)** — replace the hierarchy diagram with the 5000-block table; add a section "Error codes" explaining that `code` is authoritative and listing each subclass with its `code` / `status_code` / extras (`available`/`required`, `suspended_until`).

### Design decisions

1. **Class-level `code` / `status_code`** rather than passing them through every constructor. Mirrors the server-side `WalletError` pattern, keeps subclass `__init__` empty in most cases, and makes the dispatcher implementation trivial (it just calls `cls(message=...)`).
2. **Dispatcher in its own `_errors.py`** rather than inside `_client.py`. The registry is data that belongs next to the exceptions, and `_client.py` is already 200+ lines. A separate module also makes the dispatch path easy to unit-test in isolation.
3. **`WalletInvariantError.__init__` ignores caller-supplied messages**. The spec is explicit: the server masks the cross-check diff, and the SDK should reinforce by refusing to echo anything dynamic. Enforcing this in the constructor — not just in the dispatcher — means callers who instantiate it directly (e.g. in their own retry logic) also get the canned message.
4. **Keep the string-heuristic 400 fallbacks in `_raise_for_status`**. Defensive for endpoints that return phrases like "insufficient balance" without a `code` (other apps, older API versions, future endpoints). The new code-based dispatch runs first, so any response carrying a `code` is handled by the registry; the string heuristic only fires when both `code` is absent and the HTTP status is 400. Existing `test_400_*` tests stay green.
5. **Client-side `reference_id` validation in `Wallet.spend`** matches the server's `wallet_ops.spend.spend` validation (empty / contains `#`). Saves a round-trip on obvious mistakes and gives callers the same `InvalidReferenceError` (code 5006) they'd get from the server — same exception type means a single `except` block works in both cases.
6. **`get_holdings` and `get_root_balance` unwrap their single-key envelopes** to match the existing convention of `balance()` / `cashable()` / `spending_power()`. Callers get the data directly; consistency over literal API mirroring.
7. **No `withdraw` wrapper** added (request explicitly defers it).

### Edge cases & error handling

- **A 500 with `code=5001`** must be dispatched as `WalletInvariantError` BEFORE the generic catch-all. Achieved by calling `dispatch_wallet_error(body)` as the first line of `_raise_for_status`.
- **A 200 OK with `{"status": false, "code": 5002}`** (envelope error, not transport error) must dispatch the same way. Achieved by calling the dispatcher inside `_process_body` before the generic `MojoWalletError`.
- **A response body that is not a dict** (e.g. raw text from a 502): dispatcher returns `None` (the `isinstance(body, dict)` guard), and the existing string-heuristic / generic dispatch handles it.
- **A response with `code` outside the 5000-block** (e.g. a future 6000-block): dispatcher returns `None`, falls through to existing dispatch — generic `MojoWalletError` carries the unknown `code` via the existing `code=body.get("code")` pass-through in `_process_body`.
- **`Wallet.spend` called with `metadata=None`**: passes `metadata=None` through to the action payload. The server's `wallet_ops.spend.spend` defaults `metadata=None`, so this is safe; no need to strip `None` values client-side.
- **`get_holdings` with no filters**: sends `q=holdings` only. The server returns the full unfiltered list.

### Testing plan

- New tests live in the existing `tests/test_exceptions.py`, `tests/test_client.py`, and `tests/test_wallet.py` (see Step 7 for the exact additions).
- All tests use the SDK's `fake_mode` — no live API dependency.
- Every new `assert` carries a descriptive failure message per project convention.
- Run command: `pytest -v` from the SDK root.
- Confirm existing `test_400_insufficient_balance` / `test_400_session_conflict` / `test_400_wallet_locked` still pass — they exercise the string-heuristic fallback that the dispatcher leaves intact.
- Confirm `test_insufficient_balance_error` and `test_wallet_locked_error` updated for the new status codes (402 and 423).

### Documentation plan

- **README.md**: Spend example, Balance reads section with new shape + breaking-change callout, Error codes table.
- **CHANGELOG.md**: 2.3.0 entry covering Added / Changed / Breaking.
- **docs/wallet.md**: reference entries for `spend`, `get_holdings`, `get_root_balance`; updated `balance_summary` shape doc.
- **docs/error-handling.md**: 5000-block table, new subclasses, dispatcher behavior, `WalletInvariantError` UX guidance.
- **pyproject.toml** + **mojowallet/__init__.py**: version bump 2.2.1 → 2.3.0.

(No upstream `mverify_api/docs/` updates needed — those were done in the API hardening Phase 2 work that this SDK update consumes.)

### Out of scope (reaffirmed)

- Portal-side updates ([../mverify_portal](../../mverify_portal), [../wmx_portal](../../wmx_portal)) — separate requests.
- wmx_api updates ([../wmx_api](../../wmx_api)) — separate request.
- Async / Twisted SDK variant — separate request if/when needed.
- `withdraw` typed wrapper — explicitly deferred by the request.
- Per-holding `spend_priority` editing — Phase 4 of API hardening, separate SDK update when it lands.

---
## Resolution

**Status**: Resolved — 2026-05-23
**Released as**: v2.3.0
**Commits**:
- `7d2aa72` — Release v2.3.0 — wallet hardening Phase 2 SDK support (13 files, +747/-75)
- `d32ae77` — docs follow-up — drop duplicate changelog, document IdempotentReplayError (3 files)

### What landed

All five deliverables from the request:

1. **`Wallet.spend(amount_units, root_code, reference_id, *, merchant="", metadata=None)`** — typed wrapper with client-side `reference_id` validation (empty / `'#'`) raising `InvalidReferenceError` locally.
2. **Exception registry** — `InsufficientBalanceError` restamped to 5002/402, `WalletLockedError` to 5003/423; new subclasses `WalletInvariantError` (5001/500), `WalletSuspendedError` (5004/423), `WalletInactiveError` (5005/423), `InvalidReferenceError` (5006/400), `IdempotentReplayError` (5007/409). Base `MojoWalletError` refactored so subclasses own `code`/`status_code` as class attributes; constructors stay minimal.
3. **Response dispatcher** — new `mojowallet/_errors.py` module with `WALLET_CODE_REGISTRY` and `dispatch_wallet_error(body)`. Wired into both `_process_body` (envelope-error path) and `_raise_for_status` (HTTP-error path), running before any transport-level dispatch so a 500 with `code=5001` surfaces as `WalletInvariantError` and a 423 with `code=5003` doesn't fall through. `WalletInvariantError` ignores server-supplied detail at the SDK boundary — the canned "please retry" message is mandatory.
4. **`Wallet.get_holdings(currency_code=None, root_code=None, include_expired=False)`** and **`Wallet.get_root_balance(root_code)`** — thin wrappers over `q=holdings` and `q=root_balance` that unwrap their single-key envelopes to match the existing `balance()` / `cashable()` convention. `get_holdings` skips `None` filters and a default `False` `include_expired` so the wire stays clean.
5. **Docs / version bump** — README gets a Spend example, Balance reads section (with the breaking-change callout for `balances` keying), and an Error codes table. `CHANGELOG.md` and `docs/wallet.md` and `docs/error-handling.md` updated. `docs/changelog.md` (stale duplicate) removed; `docs/README.md` now points at the top-level `CHANGELOG.md`. `pyproject.toml` and `mojowallet/__init__.py` bumped 2.2.1 → 2.3.0.

### Files changed

**Source**
- `mojowallet/exceptions.py` — restructure base + restamp/add 7 subclasses
- `mojowallet/_errors.py` — **new** — registry + dispatcher
- `mojowallet/_client.py` — wire dispatcher into envelope-error and HTTP-error paths
- `mojowallet/wallet.py` — add `spend`, `get_holdings`, `get_root_balance`; update `balance_summary` docstring
- `mojowallet/__init__.py` — export new exceptions, bump `__version__`
- `pyproject.toml` — bump version

**Tests**
- `tests/test_exceptions.py` — rewritten — updated assertions for 402/423, added tests for all five new subclasses, added `test_wallet_invariant_error_ignores_caller_message`
- `tests/test_client.py` — added `TestWalletErrorDispatch` (parametrized per-code dispatch test, extras-population for 5002 and 5004, canned-message enforcement for 5001, envelope-vs-transport ordering, unknown-code fallthrough)
- `tests/test_wallet.py` — added `TestWalletSpend` (happy path, empty/`#` reference rejection, metadata passthrough), `TestWalletNewQueries` (holdings with/without filters, None-skipping, root_balance), `TestBalanceSummaryShape` (new root-keyed shape deserializes correctly)

**Docs**
- `README.md` — Spend example, Balance reads section + breaking-change callout, Error codes table
- `CHANGELOG.md` — 2.3.0 entry (Added / Changed / Breaking)
- `docs/wallet.md` — reference entries for `spend`, `get_holdings`, `get_root_balance`; expanded `balance_summary` shape
- `docs/error-handling.md` — 5000-block table, dispatcher behavior, per-subclass attribute tables (including `WalletInvariantError` and `IdempotentReplayError`), `WalletInvariantError` UX guidance
- `docs/changelog.md` — **deleted** (stale duplicate; top-level `CHANGELOG.md` is canonical)
- `docs/README.md` — Changelog link repointed to `../CHANGELOG.md`

### Validation

- `.venv/bin/pytest -v --ignore=tests/test_integration.py` — **125 passed, 0 failed** (independently verified by test-runner agent). Integration tests in `tests/test_integration.py` need a live API + credentials; they're pre-existing infra and were skipped.
- 19 new tests cover the new functionality: 9 in `test_exceptions.py`, 7 in `test_client.py` (parametrized for 7 codes + 5 specific cases), 8 in `test_wallet.py`.
- Security review (security-review agent): no critical findings. `WalletInvariantError` message suppression confirmed correctly implemented (no bypass via positional `message`, `**kwargs`, or dispatcher). `reference_id` validation deliberately mirrors the server (non-empty + no `'#'`) per the plan — defense-in-depth char restrictions out of scope.
- Docs audit (docs-updater agent): identified the `docs/changelog.md` duplicate and the missing `IdempotentReplayError` attr entry; both fixed in commit `d32ae77`.

### Downstream

`wmx_api` is the immediate consumer. A scoped follow-on request landed at `wmx_api/planning/requests/46-adopt-mojowallet-2.3.0.md` covering the mechanical adoption: rename `spend_group` → `root_code` at the SDK call site in [wallet_service.py:1022-1025](../../wmwx/wmx_api/apps/wmx/wallet/services/wallet_service.py:1022), extend `error_map._MAPPING` with the five new exception classes, and bump the SDK pin. The broader `wmx_api/planning/requests/45-wmx-wallet-contract-hardening.md` initiative builds on top of #46.
