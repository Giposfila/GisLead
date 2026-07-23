from __future__ import annotations

import anthropic
import httpx
import pytest

from leadgis.llm.anthropic_provider import _translate
from leadgis.llm.base import (
    AuthError,
    GenerationError,
    ModelNotFoundError,
    ProviderUnavailable,
    RateLimitError,
)

_REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _status_error(
    cls: type[anthropic.APIStatusError], status_code: int
) -> anthropic.APIStatusError:
    response = httpx.Response(status_code, request=_REQUEST, headers={"retry-after": "30"})
    return cls("boom", response=response, body=None)


def test_authentication_error_maps_to_auth_error() -> None:
    exc = _status_error(anthropic.AuthenticationError, 401)
    assert isinstance(_translate(exc), AuthError)


def test_permission_denied_error_maps_to_auth_error() -> None:
    exc = _status_error(anthropic.PermissionDeniedError, 403)
    assert isinstance(_translate(exc), AuthError)


def test_not_found_error_maps_to_model_not_found() -> None:
    exc = _status_error(anthropic.NotFoundError, 404)
    assert isinstance(_translate(exc), ModelNotFoundError)


def test_rate_limit_error_maps_and_carries_retry_after() -> None:
    exc = _status_error(anthropic.RateLimitError, 429)
    translated = _translate(exc)
    assert isinstance(translated, RateLimitError)
    assert translated.retry_after == 30.0


def test_internal_server_error_maps_to_provider_unavailable() -> None:
    exc = _status_error(anthropic.InternalServerError, 500)
    assert isinstance(_translate(exc), ProviderUnavailable)


def test_connection_error_maps_to_provider_unavailable() -> None:
    exc = anthropic.APIConnectionError(request=_REQUEST)
    assert isinstance(_translate(exc), ProviderUnavailable)


def test_bad_request_error_maps_to_generation_error() -> None:
    exc = _status_error(anthropic.BadRequestError, 400)
    assert isinstance(_translate(exc), GenerationError)


@pytest.mark.parametrize(
    ("cls", "status"),
    [(anthropic.UnprocessableEntityError, 422), (anthropic.ConflictError, 409)],
)
def test_other_status_errors_map_to_generation_error(
    cls: type[anthropic.APIStatusError], status: int
) -> None:
    exc = _status_error(cls, status)
    assert isinstance(_translate(exc), GenerationError)
