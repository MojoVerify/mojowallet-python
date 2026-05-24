## v2.3.0 - May 23, 2026

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
- Code-based error dispatcher (`mojowallet._errors.dispatch_wallet_error`).
  When the response body carries a 5000-block `code`, the SDK raises the
  matching subclass regardless of HTTP status.

### Changed
- `InsufficientBalanceError` — now `code = 5002`, `status_code = 402` (was 400).
- `WalletLockedError` — now `code = 5003`, `status_code = 423` (was 400).
- `MojoWalletError.code` is now a class-level int (5000-block) instead of an
  unused slot on the base.

### Breaking
- `balance_summary().balances` is now keyed by `root_code` instead of
  `currency_code`. Per-currency rollups remain available under
  `balance_summary().total_by_currency` (unchanged from 2.2.x). Update any
  code reading `summary.balances["SC_REAL"]` to either
  `summary.total_by_currency["SC_REAL"]` or
  `summary.balances["SC"].by_code["SC_REAL"]`.

## v2.2.0 - May 22, 2026

## v2.2.1 - May 23, 2026

publish latest


- `Wallet.action(name, **params)` / `Wallet.query(name, **params)` — public
  generic passthroughs for any wallet action/query without a dedicated method
  (e.g. `wallet.action("record_event", event_key=..., idempotency_key=...)`).

## v1.0.0 - May 15, 2026

## v2.1.1 - May 19, 2026



## v2.0.1 - May 19, 2026

new client


Initial release