# fragalysis-target-access-authenticator-python-client

![PyPI - Version](https://img.shields.io/pypi/v/xchem-ta-auth-client)

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

## Usage
After installing from PyPI, access the `ta_auth_connector` functions directly
via the connector module: -

    import ta_auth_connector

    ping_response: TasAuthPingGetResponse = ta_auth_connector.get_auth_ping()

## Target access strings
A _Target Access String_ (**TAS**) is the concatenation of a two-character **code**
(lower case), **proposal number**, and **visit number** formatted
as `<code><proposal>-<visit>`: -

-   lb12345-1
-   lb32627-66

## Rules
Access to non-public Fragalysis Targets is limited to users who are members
of the associated TAS. If a target belongs to `lb32627-66` (and `lb32627-66` is not
a publicly visible target) you will not be permitted access to the material
unless, according to ISPyB, you are a member of proposal `32627` and visit `66`.

Also, although everyone can _view_ publicly visible targets you are not permitted
to alter or add material to the target unless you are a member of the proposal `32627`
and visit `66`. Everyone can _see_ public targets, but only members of the TAS can edit.

## The authenticator service
See: -

-   https://github.com/xchem/fragalysis-ispyb-target-access-authenticator
-   https://github.com/xchem/fragalysis-mock-target-access-authenticator

---
