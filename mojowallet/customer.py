class Customer:
    """
    Customer KYC resource (upstream prefix: ``verify``).

    Construct via ``client.Customer`` rather than directly::

        client = mojowallet.Client(api_key="...")
        customer = client.Customer.create(first_name="Bob", last_name="Jones", dob="1990-01-30")
        customer.uuid            # "cust-abc123"
        customer.update(email="bob@example.com", phone="+15551234567")

        customer.verify_email()
        customer.verify_phone()

        request_uuid = customer.request_kyc(require_ssn=True, require_gov_id=True)
        status = customer.check_kyc_request(request_uuid)

        kyc = customer.get_kyc_status()
        kyc.kyc_level       # 0=unverified, 1=basic, 2=verified, 3=enhanced
    """

    _PREFIX = "verify"

    def __init__(self, data, client):
        self._data = data
        self._client = client
        self.id = data.id

    def __repr__(self):
        name = f"{self._data.get('first_name', '')} {self._data.get('last_name', '')}".strip()
        return f"Customer(id={self.id}, name={name!r})"

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._data[name]
        except (KeyError, TypeError):
            raise AttributeError(f"Customer has no attribute {name!r}")

    def refresh(self):
        """Reload customer data from the server."""
        data = self._client.get(f"customer/{self.id}", prefix=self._PREFIX)
        self._data = data
        self.id = data.id
        return self

    def update(self, **kwargs):
        """
        Update customer fields.

        Args:
            **kwargs: Fields to update — email, phone, address_line1,
                      address_city, address_state, address_postal_code,
                      address_country, first_name, last_name, etc.
        """
        data = self._client.post(f"customer/{self.id}", payload=kwargs, prefix=self._PREFIX)
        self._data = data
        self.id = data.id
        return self

    def update_meta(self, metadata):
        """Update the customer's metadata JSON field."""
        return self.update(metadata=metadata)

    # ── Email & Phone Verification ───────────────────────────────

    def verify_email(self, email=None, redirect_url=""):
        """
        Send an email verification link. Uses the customer's email if not specified.

        Returns dict with token, expires_at, send_status.
        """
        return self._client.post("email/verify", payload={
            "email": email or self._data.get("email"),
            "redirect_url": redirect_url,
        }, prefix="tools")

    def verify_phone(self, phone=None, redirect_url=""):
        """
        Send an SMS verification link. Uses the customer's phone if not specified.

        Returns dict with token, expires_at, send_status.
        """
        return self._client.post("phone/verify", payload={
            "phone": phone or self._data.get("phone"),
            "redirect_url": redirect_url,
        }, prefix="tools")

    # ── Liveness Check ───────────────────────────────────────────

    def request_liveness_check(self, verification_request_id=None, **config):
        """
        Start a liveness/identity verification session.

        If no verification_request_id is provided, creates a KYC request
        first with require_liveness=True.

        Args:
            verification_request_id: Existing PersonVerificationRequest ID.
            **config: require_barcode, document_types, ttl_hours, etc.

        Returns:
            Session token string.
        """
        if not verification_request_id:
            req = self._client.post("requests", payload={
                "first_name": self._data.get("first_name"),
                "last_name": self._data.get("last_name"),
                "email": self._data.get("email"),
                "require_liveness": True,
                "require_gov_id": config.pop("require_gov_id", False),
                "require_ssn": False,
                "require_ofac": False,
            }, prefix=self._PREFIX)
            verification_request_id = req.id

        payload = {
            "verification_request": verification_request_id,
            "require_liveness": True,
            **config,
        }
        result = self._client.post("sessions", payload=payload, prefix="identity")
        return result.session_token

    def check_liveness_status(self, session_token):
        """
        Check the status of a liveness/identity session.

        Returns dict with status, decision, overall_score, etc.
        """
        return self._client.get("sessions/status",
            params={"session_token": session_token}, prefix="identity")

    # ── KYC Verification ─────────────────────────────────────────

    def request_kyc(self, **kwargs):
        """
        Create a full KYC verification request for this customer.

        Returns:
            UUID string of the created verification request.
        """
        payload = {
            "first_name": self._data.get("first_name"),
            "last_name": self._data.get("last_name"),
            "email": self._data.get("email"),
            "phone": self._data.get("phone"),
            **kwargs,
        }
        result = self._client.post("requests", payload=payload, prefix=self._PREFIX)
        return result.uuid

    def check_kyc_request(self, request_uuid):
        """
        Check the status of a KYC verification request.

        Returns dict with status, kyc_level, risk_level, verification flags, etc.
        """
        return self._client.get(f"requests/uuid/{request_uuid}", prefix=self._PREFIX)

    def get_kyc_status(self):
        """
        Refresh and return the customer's current KYC status.
        """
        self.refresh()
        return self._data


class CustomerNamespace:
    """Reached via ``client.Customer`` — entry point for customer CRUD.
    Constructs ``Customer`` instances bound to ``client``."""

    _PREFIX = "verify"

    def __init__(self, client):
        self._client = client

    def create(self, first_name, last_name, **kwargs):
        """
        Create a new customer in the client's group.

        Args:
            first_name: Customer first name.
            last_name: Customer last name.
            **kwargs: Optional fields — dob, email, phone, address_*, metadata, etc.
        """
        payload = {"first_name": first_name, "last_name": last_name, **kwargs}
        if "dob" in payload:
            payload["date_of_birth"] = payload.pop("dob")
        data = self._client.post("customer", payload=payload, prefix=self._PREFIX)
        return Customer(data, self._client)

    def get(self, id_or_uuid):
        """Get a customer by integer ID or UUID string."""
        data = self._client.get(f"customer/{id_or_uuid}", prefix=self._PREFIX)
        return Customer(data, self._client)

    def list(self, **filters):
        """List customers with optional filtering."""
        data = self._client.get("customer", params=filters, prefix=self._PREFIX)
        if isinstance(data, list):
            return [Customer(c, self._client) for c in data]
        return data
