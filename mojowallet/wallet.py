from . import _client
from .session import Session


class Wallet:
    """
    OO wrapper for a MojoWallet wallet instance.

    All wallet operations are methods on this object. Get a wallet with::

        wallet = mojowallet.Wallet.get(42)
        wallet.add_funds(1000, "SC_REAL", source="CREDIT_CARD")
    """

    def __init__(self, data):
        self._data = data
        self.id = data.id

    def __repr__(self):
        return f"Wallet(id={self.id}, name={self.name!r})"

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        try:
            return self._data[name]
        except (KeyError, TypeError):
            raise AttributeError(f"Wallet has no attribute {name!r}")

    # ── CRUD / Retrieval ───────────────────────────────────────

    @classmethod
    def get(cls, id):
        """Get a wallet by integer ID."""
        data = _client.get(f"wallet/{id}")
        return cls(data)

    @classmethod
    def get_by_customer(cls, customer_uuid):
        """Get a wallet by customer UUID (e.g. 'cust-abc123')."""
        data = _client.get(f"wallet/{customer_uuid}")
        return cls(data)

    @classmethod
    def list(cls, **filters):
        """List wallets with optional filtering."""
        data = _client.get("wallet", params=filters)
        return [cls(w) for w in data] if isinstance(data, list) else data

    def refresh(self):
        """Reload wallet data from the server."""
        data = _client.get(f"wallet/{self.id}")
        self.__init__(data)
        return self

    # ── Internal Helpers ───────────────────────────────────────

    def _action(self, action_name, **params):
        """POST to wallet/action/<pk> (mutations)."""
        return _client.post(f"wallet/action/{self.id}", payload={"action": action_name, **params})

    def _query(self, query_name, **params):
        """GET from wallet/query/<pk> (reads)."""
        return _client.get(f"wallet/query/{self.id}", params={"q": query_name, **params})

    def _save_action(self, action_name, params=None):
        """POST to wallet/<pk> with POST_SAVE_ACTIONS key."""
        return _client.post(f"wallet/{self.id}", payload={action_name: params or True})

    # ── Funds ──────────────────────────────────────────────────

    def add_funds(self, amount_units, currency_code, source, **kwargs):
        """Add funds to the wallet (deposit)."""
        return self._action("add_funds",
            amount_units=amount_units, currency_code=currency_code,
            source=source, **kwargs)

    def award_reward(self, amount_units, currency_code, reward_type, **kwargs):
        """Award reward/bonus funds."""
        return self._action("award_reward",
            amount_units=amount_units, currency_code=currency_code,
            reward_type=reward_type, **kwargs)

    def admin_adjust(self, amount_units, currency_code, direction, reason, **kwargs):
        """Admin balance adjustment (credit or debit)."""
        return self._action("admin_adjust",
            amount_units=amount_units, currency_code=currency_code,
            direction=direction, reason=reason, **kwargs)

    def refund(self, original_txn, amount_units=None, reason="", **kwargs):
        """Refund a previous transaction."""
        return self._action("refund",
            original_txn=original_txn, amount_units=amount_units,
            reason=reason, **kwargs)

    # ── Withdrawals ────────────────────────────────────────────

    def purchase(self, amount_units, currency_code, merchant, **kwargs):
        """Make a purchase (debit)."""
        return self._action("purchase",
            amount_units=amount_units, currency_code=currency_code,
            merchant=merchant, **kwargs)

    def cashout(self, amount_units, currency_code, reference_id, **kwargs):
        """Cash out funds (withdrawal to external)."""
        return self._action("cashout",
            amount_units=amount_units, currency_code=currency_code,
            reference_id=reference_id, **kwargs)

    def transfer(self, to_wallet_id, amount_units, currency_code, **kwargs):
        """Transfer funds to another wallet."""
        return self._action("transfer",
            to_wallet=to_wallet_id, amount_units=amount_units,
            currency_code=currency_code, **kwargs)

    # ── Reserve Flow ───────────────────────────────────────────

    def reserve(self, amount_units, currency_code, hold_currency_code, reference_id, **kwargs):
        """Reserve funds (move to hold currency)."""
        return self._action("reserve",
            amount_units=amount_units, currency_code=currency_code,
            hold_currency_code=hold_currency_code,
            reference_id=reference_id, **kwargs)

    def confirm_reservation(self, reference_id):
        """Confirm a pending reservation (finalize the hold)."""
        return self._action("confirm_reservation", reference_id=reference_id)

    def release_reservation(self, reference_id):
        """Release a reservation (return held funds)."""
        return self._action("release_reservation", reference_id=reference_id)

    # ── Balance Queries ────────────────────────────────────────

    def balance(self, currency_code):
        """Get balance for a currency. Returns integer (units)."""
        result = self._query("balance", currency_code=currency_code)
        return result.balance if hasattr(result, 'balance') else result

    def balance_summary(self):
        """Get full balance summary across all currencies."""
        return self._query("balance_summary")

    def cashable(self, currency_code):
        """Get cashable (withdrawable) balance. Returns integer (units)."""
        result = self._query("cashable", currency_code=currency_code)
        return result.cashable if hasattr(result, 'cashable') else result

    def spending_power(self, currency_code):
        """Get spending power (balance minus limits). Returns integer (units)."""
        result = self._query("spending_power", currency_code=currency_code)
        return result.spending_power if hasattr(result, 'spending_power') else result

    def transactions(self, **kwargs):
        """Get transaction history with optional filters."""
        return self._query("transactions", **kwargs)

    def balance_at(self, currency_code, timestamp):
        """Get historical balance at a specific timestamp."""
        return self._query("balance_at", currency_code=currency_code, timestamp=timestamp)

    def transaction_aggregation(self, currency_code, **kwargs):
        """Get aggregated transaction data."""
        return self._query("transaction_aggregation", currency_code=currency_code, **kwargs)

    # ── Lock / Unlock (POST_SAVE_ACTIONS) ──────────────────────

    def lock(self, reason=""):
        """Lock the wallet. All operations will be blocked."""
        return self._save_action("lock", {"reason": reason})

    def unlock(self, reason=""):
        """Unlock the wallet."""
        return self._save_action("unlock", {"reason": reason})

    # ── Promo (POST_SAVE_ACTIONS) ──────────────────────────────

    def redeem_promo(self, code, reference_id=None, **kwargs):
        """Redeem a promo code."""
        params = {"code": code}
        if reference_id:
            params["reference_id"] = reference_id
        params.update(kwargs)
        return self._save_action("redeem_promo", params)

    # ── Sessions ───────────────────────────────────────────────

    def session(self, session_id, **kwargs):
        """
        Start a session and return it as a context manager.

        Usage::

            with wallet.session("game-xyz", expires_in_seconds=3600) as s:
                s.withdraw(500, "SC_REAL", reference_id="bet-001")
        """
        return Session._start(self, session_id, **kwargs)

    def start_session(self, session_id, **kwargs):
        """
        Start a session (manual lifecycle — caller must close).

        Usage::

            session = wallet.start_session("game-xyz")
            session.withdraw(500, "SC_REAL", reference_id="bet-001")
            session.close()
        """
        data = self._action("start_session", session_id=session_id, **kwargs)
        return Session(data, self)

    # ── Metrics ────────────────────────────────────────────────

    def record_metric(self, key, **kwargs):
        """Record a counter metric."""
        return self._action("record_metric", key=key, **kwargs)

    def set_gauge(self, key, value):
        """Set a gauge metric value."""
        return self._action("set_gauge", key=key, value=value)

    def get_metric(self, key, **kwargs):
        """Get a counter metric's data."""
        return self._query("metric", key=key, **kwargs)

    def get_gauge(self, key, **kwargs):
        """Get a gauge metric value."""
        return self._query("gauge", key=key, **kwargs)

    # ── Batch (class methods) ──────────────────────────────────

    @classmethod
    def batch_balances(cls, wallet_ids, currency_code=None):
        """Get balances for multiple wallets at once."""
        payload = {"action": "batch_balances", "wallet_ids": wallet_ids}
        if currency_code:
            payload["currency_code"] = currency_code
        return _client.post("wallet/batch", payload=payload)
