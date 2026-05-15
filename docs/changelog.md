# Changelog

## v0.1.0 (2026-03-08)

Initial release.

- `Wallet` class with full OO API
- Funds operations: `add_funds`, `award_reward`, `admin_adjust`, `refund`, `purchase`, `cashout`, `transfer`
- Reserve flow: `reserve`, `confirm_reservation`, `release_reservation`
- Balance queries: `balance`, `balance_summary`, `cashable`, `spending_power`, `transactions`, `balance_at`, `transaction_aggregation`
- Session support with context manager: `session()`, `start_session()`
- Session operations: `withdraw`, `extend`, `close`
- Lock/unlock: `lock`, `unlock`
- Promo codes: `redeem_promo`
- Metrics: `record_metric`, `set_gauge`, `get_metric`, `get_gauge`
- Batch operations: `batch_balances`
- Customer CRUD: `customer.list`, `customer.get`, `customer.create`, `customer.update`
- Exception hierarchy: `MojoWalletError`, `AuthError`, `InsufficientBalanceError`, `SessionConflictError`, `WalletLockedError`, `PermissionError`, `NotFoundError`, `RateLimitError`
