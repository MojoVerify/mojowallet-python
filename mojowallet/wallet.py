from .exceptions import InvalidReferenceError
from .session import Session


class Wallet:
    """
    OO wrapper for a MojoWallet wallet instance.

    Construct via ``client.Wallet.get(...)`` rather than directly::

        client = mojowallet.Client(api_key="...")
        wallet = client.Wallet.get(42)
        wallet.add_funds(1000, "SC_REAL", source="CREDIT_CARD")
    """

    def __init__(self, data, client):
        self._data = data
        self._client = client
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

    def refresh(self):
        """Reload wallet data from the server."""
        data = self._client.get(f"wallet/{self.id}")
        self._data = data
        self.id = data.id
        return self

    # ── Internal Helpers ───────────────────────────────────────

    def _action(self, action_name, **params):
        """POST to wallet/action/<pk> (mutations)."""
        return self._client.post(
            f"wallet/action/{self.id}",
            payload={"action": action_name, **params},
        )

    def _query(self, query_name, **params):
        """GET from wallet/query/<pk> (reads)."""
        return self._client.get(
            f"wallet/query/{self.id}",
            params={"q": query_name, **params},
        )

    def _save_action(self, action_name, params=None):
        """POST to wallet/<pk> with POST_SAVE_ACTIONS key."""
        return self._client.post(
            f"wallet/{self.id}",
            payload={action_name: params or True},
        )

    # ── Generic Passthrough ────────────────────────────────────

    def action(self, name, **params):
        """Invoke any wallet action by name — POST wallet/action/<pk>.

        Use for actions without a dedicated method, e.g.::

            wallet.action("record_event", event_key="player.registered",
                          idempotency_key="evt-123")
        """
        return self._action(name, **params)

    def query(self, name, **params):
        """Run any wallet query by name — GET wallet/query/<pk>."""
        return self._query(name, **params)

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

    def spend(self, amount_units, root_code, reference_id, *, merchant="", metadata=None):
        """Spend funds from a currency family (e.g. ``"SC"``).

        The server walks the family's holdings in priority order — currency
        ``spend_priority`` ascending, then holding ``created`` ascending — and
        debits across as many holdings as needed.

        Idempotent on ``reference_id``: a replay returns the original
        transactions instead of double-debiting. Child transactions are keyed
        ``f"{reference_id}#{i}"`` server-side, so ``reference_id`` itself must
        not contain ``'#'``.

        Raises ``InvalidReferenceError`` (code 5006) locally if
        ``reference_id`` is empty or contains ``'#'`` — same constraint the
        server enforces.
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
        moved to ``total_by_currency`` (which existed before and is preserved).
        """
        return self._query("balance_summary")

    def cashable(self, currency_code):
        """Get cashable (withdrawable) balance. Returns integer (units)."""
        result = self._query("cashable", currency_code=currency_code)
        return result.cashable if hasattr(result, 'cashable') else result

    def spending_power(self, currency_code):
        """Get spending power (balance minus limits). Returns integer (units)."""
        result = self._query("spending_power", currency_code=currency_code)
        return result.spending_power if hasattr(result, 'spending_power') else result

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
        return result.holdings if hasattr(result, 'holdings') else result

    def get_root_balance(self, root_code):
        """Get aggregated balance for a currency family (e.g. ``"SC"``).

        Returns a dict with ``available``, ``total``, and ``by_code`` (the
        per-currency breakdown within the family).
        """
        result = self._query("root_balance", root_code=root_code)
        return result.root_balance if hasattr(result, 'root_balance') else result

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

        This is a strict concurrency guard: it raises ``SessionConflictError``
        if the wallet already has an active withdraw session — even one with
        the same ``session_id``. To operate inside an already-open session
        use ``attach_session``; to close one use ``close_session``.

        Usage::

            session = wallet.start_session("game-xyz")
            session.withdraw(500, "SC_REAL", reference_id="bet-001")
            session.close()
        """
        data = self._action("start_session", session_id=session_id, **kwargs)
        return Session(data, self)

    def attach_session(self, session_id):
        """
        Return a Session bound to an already-open ``session_id``, with no
        server round-trip. Use to operate inside a session a different
        request opened (launch opens it; later bets withdraw inside it).

        The handle supports ``withdraw``; ``close`` / ``extend`` are not
        available on it (use ``close_session`` to close by id).
        """
        return Session.attach(self, session_id)

    def close_session(self, session_id):
        """
        Close an active session by its external ``session_id``.

        Closes by id with no Session object, so a process that did not open
        the session (a reaper, a force-close, a webhook handler) can still
        close it. ``start_session`` cannot be re-used for this — it is a
        strict guard that rejects a second start while a session is active.
        """
        return self._action("close_session", session_id=session_id)

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


class WalletNamespace:
    """Reached via ``client.Wallet`` — entry point for wallet retrieval and
    batch operations. Constructs ``Wallet`` instances bound to ``client``."""

    def __init__(self, client):
        self._client = client

    def get(self, id):
        """Get a wallet by integer ID."""
        data = self._client.get(f"wallet/{id}")
        return Wallet(data, self._client)

    def get_by_customer(self, customer_uuid):
        """Get a wallet by customer UUID (e.g. 'cust-abc123')."""
        data = self._client.get(f"wallet/{customer_uuid}")
        return Wallet(data, self._client)

    def list(self, **filters):
        """List wallets with optional filtering."""
        data = self._client.get("wallet", params=filters)
        if isinstance(data, list):
            return [Wallet(w, self._client) for w in data]
        return data

    def batch_balances(self, wallet_ids, currency_code=None):
        """Get balances for multiple wallets at once."""
        payload = {"action": "batch_balances", "wallet_ids": wallet_ids}
        if currency_code:
            payload["currency_code"] = currency_code
        return self._client.post("wallet/batch", payload=payload)
