# Getting Started

## Installation

```bash
pip install mojowallet
```

## Configuration

```python
import mojowallet

mojowallet.configure("your-api-key", base_url="https://api.example.com")
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `api_key` | `str` | Yes | — | Your API key |
| `base_url` | `str` | No | `https://api.mojowallet.com` | API base URL |

## First Request

```python
wallet = mojowallet.Wallet.get(42)
print(wallet.id, wallet.uuid, wallet.name)
print(wallet.balance("SC_REAL"))
```

## Response Format

All responses are `objict` objects (dict subclass with attribute access):

```python
result = wallet.add_funds(1000, "SC_REAL", source="CREDIT_CARD")

# Both work:
print(result.id)       # attribute access
print(result["id"])    # dict access
```

## Authentication

All requests require an API key passed via `configure()`. The key is sent as:

```
Authorization: apikey your-api-key
```

If no key is configured, an `AuthError` is raised on the first API call.
