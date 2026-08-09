---
id: language-python-example-segmented-api-client
title: Python Segmented API Client Example
description: Example shared requests session with focused endpoint segments layered on top.
kind: example
scope: language
name: python
tags:
  - example
  - python
  - clients
applies_to:
  - python
status: active
order: 5
---

# Python Segmented API Client Example

## Scenario

- Use this pattern when one external API has multiple endpoint families but should still share auth, retries, and timeout behavior.

## Recommended Shape

### Good Example

```python
class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, **kwargs):
        self.timeout = timeout
        super().__init__(**kwargs)


class ExternalApiConfig:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url
        self.api_token = api_token


def _build_session(config: ExternalApiConfig) -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(total=3, status_forcelist=[], allowed_methods=['HEAD', 'GET', 'OPTIONS', 'TRACE'], raise_on_status=False)
    adapter = TimeoutHTTPAdapter(max_retries=retry_strategy)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({'Authorization': f'Bearer {config.api_token}', 'Content-Type': 'application/json'})
    return session


class OrdersClient:
    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url

    def list_orders(self):
        return self.session.get(f'{self.base_url}/orders').json()


class CustomersClient:
    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url

    def list_customers(self):
        return self.session.get(f'{self.base_url}/customers').json()


class ExternalApiClient:
    def __init__(self, config: ExternalApiConfig):
        self.session = _build_session(config)
        self.orders = OrdersClient(self.session, config.base_url)
        self.customers = CustomersClient(self.session, config.base_url)
```

### Things To Notice

- Shared timeout, retry, and auth setup live in one session builder.
- Each segment stays small and domain-focused.
- The top-level client owns lifecycle cleanup and exposes segments as clear entry points.

## Why It Helps

- Endpoint-specific code stays readable without repeating connection boilerplate.
