# fragalysis-target-access-authenticator-python-client

![PyPI - Version](https://img.shields.io/pypi/v/xchem-fragalysis-auth-client)

![release](https://github.com/xchem/fragalysis-target-access-authenticator-python-client/actions/workflows/release.yaml/badge.svg)


A simple Python 3 client to simplify access to the authenticator,
providing the following functions: -

```python
def get_auth_target_access(username: str) -> set[str]:
    [...]
def get_auth_version() -> TasAuthVersionGetResponse:
    [...]
def get_auth_ping() -> TasAuthPingGetResponse:
    [...]
```

The module requires two items, extracted from the environment: -

-   `TA_AUTH_SERVICE` - The service hostname. In cluster this might be
    `http://auth.ta-authenticator.svc` (an internal connection that is expected to
    comply with http:// protocol)
-   `TA_AUTH_QUERY_KEY` - A 'secret' key the service expects in request headers.

## The authenticator service
See: -

-   https://github.com/xchem/fragalysis-ispyb-target-access-authenticator
-   https://github.com/xchem/fragalysis-mock-target-access-authenticator

---
