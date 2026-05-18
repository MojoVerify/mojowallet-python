class Session:
    """
    Wallet session for concurrency control.

    Sessions ensure only one withdraw operation happens at a time.
    Use as a context manager for automatic cleanup::

        with wallet.session("game-xyz", expires_in_seconds=3600) as s:
            s.withdraw(500, "SC_REAL", reference_id="bet-001")
            s.withdraw(300, "SC_REAL", reference_id="bet-002")
            s.extend(1800)
        # session auto-closed on exit

    Or manage the lifecycle manually::

        session = wallet.start_session("game-xyz")
        session.withdraw(500, "SC_REAL", reference_id="bet-001")
        session.close()
    """

    def __init__(self, data, wallet):
        self._data = data
        self.id = data.id
        self.uuid = data.uuid
        self.session_id = data.session_id
        self._wallet = wallet
        self._closed = False

    def __repr__(self):
        status = "closed" if self._closed else "active"
        return f"Session(id={self.id}, session_id={self.session_id!r}, {status})"

    @classmethod
    def _start(cls, wallet, session_id, **kwargs):
        """Start a session and return a context-manager-ready Session."""
        data = wallet._action("start_session", session_id=session_id, **kwargs)
        return cls(data, wallet)

    def withdraw(self, amount_units, currency_code, reference_id, **kwargs):
        """Withdraw funds within this session."""
        return self._wallet._action("withdraw",
            amount_units=amount_units, currency_code=currency_code,
            session_id=self.session_id, reference_id=reference_id, **kwargs)

    def extend(self, duration):
        """Extend the session expiry by `duration` seconds."""
        return self._wallet._client.post(
            f"session/{self.id}",
            payload={"extend": {"duration": duration}},
        )

    def close(self):
        """Close the session. Idempotent — safe to call multiple times."""
        if not self._closed:
            result = self._wallet._client.post(
                f"session/{self.id}",
                payload={"close": True},
            )
            self._closed = True
            return result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
