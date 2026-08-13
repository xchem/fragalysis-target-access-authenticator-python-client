"""Tests for ``ta_auth_connector.get_auth_users()``.

The module binds the service location and query key at *import* time, so the
tests set the module-level values directly rather than the environment.
``requests.get`` is replaced throughout - no test contacts a real service.
"""

from typing import Any

import pytest
import requests

import ta_auth_connector

_SERVICE: str = "http://auth.example.svc"
_QUERY_KEY: str = "query-key"
_TAS: str = "lb32627-66"


class _FakeResponse:
    """The parts of a ``requests.Response`` the connector actually reads."""

    def __init__(
        self,
        status_code: int = 200,
        json_body: Any = None,
        content_type: str = "application/json",
    ):
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        self._json_body = json_body

    def json(self) -> Any:
        return self._json_body


@pytest.fixture(name="configured")
def fixture_configured(monkeypatch):
    """A connector configured with a service location and a query key."""
    monkeypatch.setattr(ta_auth_connector, "_TA_AUTH_SERVICE", _SERVICE)
    monkeypatch.setattr(ta_auth_connector, "_TA_AUTH_QUERY_KEY", _QUERY_KEY)
    monkeypatch.setattr(
        ta_auth_connector, "_QUERY_HEADERS", {"X-TAAQueryKey": _QUERY_KEY}
    )


@pytest.fixture(name="record_get")
def fixture_record_get(monkeypatch):
    """Replaces ``requests.get``, recording the call and returning a response.

    The returned setter takes the response (or an exception to raise) and
    hands back a dict that is populated with the call's ``url``, ``headers``
    and ``timeout`` once the connector makes its request.
    """

    def _set(response: Any) -> dict[str, Any]:
        call: dict[str, Any] = {}

        def _get(url: str, **kwargs) -> Any:
            call["url"] = url
            call.update(kwargs)
            if isinstance(response, Exception):
                raise response
            return response

        monkeypatch.setattr(requests, "get", _get)
        return call

    return _set


def test_returns_the_users_the_service_reports(configured, record_get):
    """A 200 response yields its users, and no error."""
    record_get(_FakeResponse(json_body={"count": 2, "users": ["abc12345", "xyz98765"]}))

    response = ta_auth_connector.get_auth_users(_TAS)

    assert response.users == {"abc12345", "xyz98765"}
    assert response.error is None


def test_no_members_is_not_an_error(configured, record_get):
    """An empty user set means "nobody", which is a valid answer.

    This is the distinction the '/users/{tas}' endpoint goes out of its way to
    preserve, so the client must preserve it too: no error, no users.
    """
    record_get(_FakeResponse(json_body={"count": 0, "users": []}))

    response = ta_auth_connector.get_auth_users(_TAS)

    assert response.users == set()
    assert response.error is None


def test_queries_the_users_endpoint_with_the_query_key(configured, record_get):
    """The request goes to '/users/{tas}' and carries the query-key header."""
    call = record_get(_FakeResponse(json_body={"count": 0, "users": []}))

    ta_auth_connector.get_auth_users(_TAS)

    assert call["url"] == f"{_SERVICE}/users/{_TAS}"
    assert call["headers"]["X-TAAQueryKey"] == _QUERY_KEY
    assert call["timeout"] > 0


def test_target_access_string_is_url_quoted(configured, record_get):
    """A TAS is interpolated into the path, so it must be quoted."""
    call = record_get(_FakeResponse(json_body={"count": 0, "users": []}))

    ta_auth_connector.get_auth_users("lb32627-66/../ping")

    assert call["url"] == f"{_SERVICE}/users/lb32627-66/../ping".replace("/../", "%2F..%2F")


def test_service_unavailable_is_an_error_not_an_empty_set(configured, record_get):
    """A 503 (ISPyB unreachable) must not be reported as "no members"."""
    record_get(_FakeResponse(status_code=503))

    response = ta_auth_connector.get_auth_users(_TAS)

    assert response.users == set()
    assert response.error is not None
    assert "503" in response.error


def test_rejected_target_access_string_is_an_error(configured, record_get):
    """The service answers 400 when the string is not a TAS."""
    record_get(_FakeResponse(status_code=400))

    response = ta_auth_connector.get_auth_users("not-a-tas")

    assert response.users == set()
    assert response.error is not None


def test_request_exception_is_an_error(configured, record_get):
    """A connection failure is reported, not swallowed as an empty set."""
    record_get(requests.exceptions.ConnectTimeout("no route to host"))

    response = ta_auth_connector.get_auth_users(_TAS)

    assert response.users == set()
    assert response.error is not None


def test_non_json_response_is_an_error(configured, record_get):
    """An HTML error page from a proxy is not a user set."""
    record_get(_FakeResponse(content_type="text/html", json_body=None))

    response = ta_auth_connector.get_auth_users(_TAS)

    assert response.users == set()
    assert response.error is not None


def test_response_without_users_property_is_an_error(configured, record_get):
    """A 200 whose body lacks 'users' is a malformed answer."""
    record_get(_FakeResponse(json_body={"count": 0}))

    response = ta_auth_connector.get_auth_users(_TAS)

    assert response.users == set()
    assert response.error is not None


def test_missing_query_key_is_an_error(monkeypatch, record_get):
    """Without a query key the service would refuse us - do not even ask."""
    monkeypatch.setattr(ta_auth_connector, "_TA_AUTH_SERVICE", _SERVICE)
    monkeypatch.setattr(ta_auth_connector, "_TA_AUTH_QUERY_KEY", "")
    call = record_get(_FakeResponse(json_body={"count": 0, "users": []}))

    response = ta_auth_connector.get_auth_users(_TAS)

    assert response.users == set()
    assert response.error is not None
    assert call == {}


def test_missing_service_is_an_error(monkeypatch, record_get):
    """Without a service location there is nothing to query."""
    monkeypatch.setattr(ta_auth_connector, "_TA_AUTH_SERVICE", "")
    monkeypatch.setattr(ta_auth_connector, "_TA_AUTH_QUERY_KEY", _QUERY_KEY)
    call = record_get(_FakeResponse(json_body={"count": 0, "users": []}))

    response = ta_auth_connector.get_auth_users(_TAS)

    assert response.users == set()
    assert response.error is not None
    assert call == {}


def test_empty_target_access_string_is_rejected(configured, record_get):
    """An empty TAS is a programming error, caught before any request."""
    call = record_get(_FakeResponse(json_body={"count": 0, "users": []}))

    with pytest.raises(AssertionError):
        ta_auth_connector.get_auth_users("")

    assert call == {}
