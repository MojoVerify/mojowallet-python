"""
MojoWallet Python SDK

Usage::

    import mojowallet

    mojowallet.configure("your-api-key", base_url="https://api.example.com")

    wallet = mojowallet.Wallet.get(42)
    wallet.add_funds(1000, "SC_REAL", source="CREDIT_CARD")
    print(wallet.balance("SC_REAL"))
"""

from ._client import configure

from .wallet import Wallet
from .session import Session
from .customer import Customer

from .exceptions import (
    MojoWalletError,
    AuthError,
    InsufficientBalanceError,
    SessionConflictError,
    WalletLockedError,
    RateLimitError,
    NotFoundError,
    PermissionError,
)

__version__ = "0.1.0"
__all__ = [
    "configure",
    "Wallet",
    "Session",
    "Customer",
    "MojoWalletError",
    "AuthError",
    "InsufficientBalanceError",
    "SessionConflictError",
    "WalletLockedError",
    "RateLimitError",
    "NotFoundError",
    "PermissionError",
]
