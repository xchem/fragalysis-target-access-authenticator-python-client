"""A module that provides simplified request access to the TA Authenticator service.
Provides the following functions, that access the authenticator Pod: -

- get_auth_version()
- get_auth_ping()
- get_auth_target_access(username)
- get_auth_users(target_access_string)
"""

import logging
from dataclasses import dataclass, field
import os
from urllib.parse import quote

import requests

# Service location (e.g. "http://auth.ta-authenticator.svc") and request query key
_TA_AUTH_SERVICE: str = os.environ.get("TA_AUTH_SERVICE", "")
_TA_AUTH_QUERY_KEY: str = os.environ.get("TA_AUTH_QUERY_KEY", "")

_URL_TIMEOUT: int = 3
_QUERY_HEADERS: dict[str, str] = {'X-TAAQueryKey': _TA_AUTH_QUERY_KEY}

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class TasAuthVersionGetResponse:
    """The TA authenticator version response (including the base URL)."""

    version: str
    kind: str
    name: str
    location: str = _TA_AUTH_SERVICE


@dataclass
class TasAuthPingGetResponse:
    """The TA authenticator ping response."""

    ping: str


@dataclass(frozen=True)
class TasAuthMember:
    """A member of a target access string. The names are None if the
    authenticator has none for the user (or is older than 1.6.0).
    """

    login: str
    given_name: str | None = None
    family_name: str | None = None


@dataclass
class TasAuthUsersGetResponse:
    """The TA authenticator '/users/{tas}' response.

    Unlike get_auth_target_access(), which cannot fail from the caller's point
    of view, this response separates "the TAS has no members" from "we could
    not find out". 'error' is None when the service answered, in which case an
    empty 'users' genuinely means nobody is a member. Otherwise 'error'
    describes what went wrong and 'users' is empty and must not be relied on.

    'members' holds the same users, sorted by login, with their names. It is
    empty whenever 'users' is.
    """

    users: set[str]
    error: str | None = None
    members: list[TasAuthMember] = field(default_factory=list)


def get_auth_version() -> TasAuthVersionGetResponse:
    """Returns the version reported by the TA authentication service."""
    if not _TA_AUTH_SERVICE:
        return TasAuthVersionGetResponse(
            version='', kind='AUTH_SERVICE_NOT_DEFINED', name=''
        )
    if not _TA_AUTH_QUERY_KEY:
        return TasAuthVersionGetResponse(
            version='', kind='SERVICE_QUERY_KEY_NOT_DEFINED', name=''
        )

    url: str = f'{_TA_AUTH_SERVICE}/version/'
    resp: requests.Response | None = None
    try:
        resp = requests.get(url, timeout=_URL_TIMEOUT)
    except requests.exceptions.RequestException as r_ex:  # pylint: disable=broad-except
        logger.error('TA:GET:%s RequestException (%s)', url, r_ex)
    except Exception as ex:  # pylint: disable=broad-exception-caught
        logger.error('TA:GET:%s Exception (%s)', url, ex)

    if resp is None:
        logger.warning('TA:GET:%s (no response)', url)
        return TasAuthVersionGetResponse(
            version='', kind='ERROR_INTERNAL', name='Null response'
        )
    elif resp.status_code not in (200,):
        logger.warning('TA:GET:%s [%s] (status not 200)', url, resp.status_code)
        return TasAuthVersionGetResponse(
            version='', kind='ERROR_INTERNAL', name='(status not 200)'
        )
    elif 'application/json' not in resp.headers.get('Content-Type', ''):
        logger.warning('TA:GET:%s (empty response)', url)
        return TasAuthVersionGetResponse(
            version='', kind='ERROR_INTERNAL', name='(empty response)'
        )
    elif 'version' not in resp.json():
        logger.warning('TA:GET:%s (no version property)', url)
        return TasAuthVersionGetResponse(
            version='', kind='ERROR_INTERNAL', name='(no version property)'
        )

    logger.info('TA:GET:%s [%s]', url, resp.json())

    return TasAuthVersionGetResponse(
        version=resp.json()['version'],
        kind=resp.json()['kind'],
        name=resp.json()['name'],
    )


def get_auth_ping() -> TasAuthPingGetResponse:
    """Returns the ping reported by the TA authentication service."""
    if not _TA_AUTH_SERVICE:
        return TasAuthPingGetResponse(ping='AUTH_SERVICE_NOT_DEFINED')

    url: str = f'{_TA_AUTH_SERVICE}/ping/'
    resp: requests.Response | None = None
    try:
        resp = requests.get(url, timeout=_URL_TIMEOUT)
    except requests.exceptions.RequestException as r_ex:  # pylint: disable=broad-except
        logger.error('TA:GET:%s RequestException (%s)', url, r_ex)
    except Exception as ex:  # pylint: disable=broad-exception-caught
        logger.error('TA:GET:%s Exception (%s)', url, ex)

    if resp is None:
        logger.warning('TA:GET:%s (no response)', url)
        return TasAuthPingGetResponse('PING response was null')
    elif resp.status_code not in (200,):
        logger.warning('TA:GET:%s [%s] (status not 200)', url, resp.status_code)
        return TasAuthPingGetResponse('PING response status not 200')
    elif 'application/json' not in resp.headers.get('Content-Type', ''):
        logger.warning('TA:GET:%s (empty response)', url)
        return TasAuthPingGetResponse('PING response was empty')
    elif 'ping' not in resp.json():
        logger.warning('TA:GET:%s (no ping property)', url)
        return TasAuthPingGetResponse('PING response has no ping property')

    ping: str = resp.json()['ping']
    logger.info('TA:GET:%s [%s]', url, ping)

    return TasAuthPingGetResponse(ping=ping)


def get_auth_target_access(username: str) -> set[str]:
    """Returns the set of target access strings a user is entitled to
    as reported by the TA authentication service."""
    assert username

    empty_target_access: set[str] = set()

    if not _TA_AUTH_QUERY_KEY:
        logger.debug('Skipping query - query key is not set (TA_AUTH_QUERY_KEY)')
        return empty_target_access

    url: str = f'{_TA_AUTH_SERVICE}/target-access/{quote(username)}'
    resp: requests.Response | None = None
    try:
        resp = requests.get(url, headers=_QUERY_HEADERS, timeout=_URL_TIMEOUT)
    except requests.exceptions.RequestException as ex:  # pylint: disable=broad-except
        logger.error('TA:GET:%s RequestException (%s)', url, ex)
    except Exception as ex:  # pylint: disable=broad-exception-caught
        logger.error('TA:GET:%s Exception (%s)', url, ex)

    if resp is None:
        logger.warning('TA:GET:%s (no response)', url)
        return empty_target_access
    if resp.status_code not in (200,):
        logger.warning('TA:GET:%s [%s] (status not 200)', url, resp.status_code)
        return empty_target_access
    elif 'application/json' not in resp.headers.get('Content-Type', ''):
        logger.warning('TA:GET:%s (empty response)', url)
        return empty_target_access
    elif 'count' not in resp.json():
        logger.warning('TA:GET:%s (no count)', url)
        return empty_target_access
    elif 'target_access' not in resp.json():
        logger.warning('TA:GET:%s (no target_access)', url)
        return empty_target_access

    target_access: set[str] = set(resp.json()['target_access'])
    logger.info('TA:GET:%s (got %d for %s)', url, len(target_access), username)

    return target_access


def get_auth_users(target_access_string: str) -> TasAuthUsersGetResponse:
    """Returns the set of users (logins) that are members of the given target
    access string, as reported by the TA authentication service.

    An empty set of users is only meaningful when the response carries no
    error - see TasAuthUsersGetResponse.
    """
    assert target_access_string

    no_users: set[str] = set()

    if not _TA_AUTH_SERVICE:
        logger.debug('Skipping query - service is not set (TA_AUTH_SERVICE)')
        return TasAuthUsersGetResponse(
            users=no_users, error='AUTH_SERVICE_NOT_DEFINED'
        )
    if not _TA_AUTH_QUERY_KEY:
        logger.debug('Skipping query - query key is not set (TA_AUTH_QUERY_KEY)')
        return TasAuthUsersGetResponse(
            users=no_users, error='SERVICE_QUERY_KEY_NOT_DEFINED'
        )

    url: str = f'{_TA_AUTH_SERVICE}/users/{quote(target_access_string, safe="")}'
    resp: requests.Response | None = None
    try:
        resp = requests.get(url, headers=_QUERY_HEADERS, timeout=_URL_TIMEOUT)
    except requests.exceptions.RequestException as ex:  # pylint: disable=broad-except
        logger.error('TA:GET:%s RequestException (%s)', url, ex)
    except Exception as ex:  # pylint: disable=broad-exception-caught
        logger.error('TA:GET:%s Exception (%s)', url, ex)

    if resp is None:
        logger.warning('TA:GET:%s (no response)', url)
        return TasAuthUsersGetResponse(users=no_users, error='No response')
    if resp.status_code not in (200,):
        logger.warning('TA:GET:%s [%s] (status not 200)', url, resp.status_code)
        return TasAuthUsersGetResponse(
            users=no_users, error=f'Status was {resp.status_code} (not 200)'
        )
    elif 'application/json' not in resp.headers.get('Content-Type', ''):
        logger.warning('TA:GET:%s (empty response)', url)
        return TasAuthUsersGetResponse(users=no_users, error='Response was not JSON')
    elif 'count' not in resp.json():
        logger.warning('TA:GET:%s (no count)', url)
        return TasAuthUsersGetResponse(users=no_users, error='Response had no count')
    elif 'users' not in resp.json():
        logger.warning('TA:GET:%s (no users)', url)
        return TasAuthUsersGetResponse(users=no_users, error='Response had no users')

    users: set[str] = set(resp.json()['users'])

    # Authenticators from 1.6.0 also return 'members' (the users with their names).
    # For older authenticators the members are the users without names.
    members: list[TasAuthMember] = []
    if 'members' in resp.json():
        for member in resp.json()['members']:
            if not member.get('login'):
                logger.warning('TA:GET:%s (member without a login)', url)
                return TasAuthUsersGetResponse(
                    users=no_users, error='Response had a member without a login'
                )
            members.append(
                TasAuthMember(
                    login=member['login'],
                    given_name=member.get('given_name'),
                    family_name=member.get('family_name'),
                )
            )
    else:
        members = [TasAuthMember(login=login) for login in sorted(users)]

    logger.info(
        'TA:GET:%s (got %d for %s)', url, len(users), target_access_string
    )

    return TasAuthUsersGetResponse(users=users, members=members)
