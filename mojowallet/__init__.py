"""
MojoVerify / MojoWallet Python SDK

Usage::

    import mojowallet

    client = mojowallet.Client("your-api-key")

    # Wallet (prefix=wallet)
    wallet = client.Wallet.get(42)
    wallet.add_funds(1000, "SC_REAL", source="CREDIT_CARD")
    print(wallet.balance("SC_REAL"))

    # Customer / KYC (prefix=verify)
    customer = client.Customer.create(first_name="Bob", last_name="Jones")
    customer.request_kyc(require_ssn=True)

    # Generic — any endpoint on the same upstream by passing prefix=
    client.post("ssn/verify", payload={...}, prefix="comply")
    client.get("apikey", prefix="account/group")
"""

from ._client import Client
from .wallet import Wallet, WalletNamespace
from .session import Session
from .customer import Customer, CustomerNamespace

from .exceptions import (
    MojoWalletError,
    AuthError,
    IdempotentReplayError,
    InsufficientBalanceError,
    InvalidReferenceError,
    SessionConflictError,
    WalletInactiveError,
    WalletInvariantError,
    WalletLockedError,
    WalletSuspendedError,
    RateLimitError,
    NotFoundError,
    PermissionError,
)

__version__ = "2.3.1"
__all__ = [
    "Client",
    "Wallet",
    "WalletNamespace",
    "Session",
    "Customer",
    "CustomerNamespace",
    "MojoWalletError",
    "AuthError",
    "IdempotentReplayError",
    "InsufficientBalanceError",
    "InvalidReferenceError",
    "SessionConflictError",
    "WalletInactiveError",
    "WalletInvariantError",
    "WalletLockedError",
    "WalletSuspendedError",
    "RateLimitError",
    "NotFoundError",
    "PermissionError",
]
