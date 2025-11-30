"""Tests for authentication providers."""

from __future__ import annotations

import os
from unittest import mock

import pytest

from pytest_routes.auth import (
    APIKeyAuth,
    AuthProvider,
    BearerTokenAuth,
    CompositeAuth,
    NoAuth,
)


class TestNoAuth:
    """Tests for NoAuth provider."""

    def test_get_headers_returns_empty_dict(self) -> None:
        auth = NoAuth()
        assert auth.get_headers() == {}

    def test_get_query_params_returns_empty_dict(self) -> None:
        auth = NoAuth()
        assert auth.get_query_params() == {}

    def test_is_auth_provider(self) -> None:
        auth = NoAuth()
        assert isinstance(auth, AuthProvider)


class TestBearerTokenAuth:
    """Tests for BearerTokenAuth provider."""

    def test_direct_token(self) -> None:
        auth = BearerTokenAuth("my-secret-token")
        headers = auth.get_headers()
        assert headers == {"Authorization": "Bearer my-secret-token"}

    def test_token_property(self) -> None:
        auth = BearerTokenAuth("test-token")
        assert auth.token == "test-token"

    def test_get_query_params_returns_empty(self) -> None:
        auth = BearerTokenAuth("token")
        assert auth.get_query_params() == {}

    def test_environment_variable_token(self) -> None:
        with mock.patch.dict(os.environ, {"API_TOKEN": "env-secret-token"}):
            auth = BearerTokenAuth("$API_TOKEN")
            headers = auth.get_headers()
            assert headers == {"Authorization": "Bearer env-secret-token"}

    def test_environment_variable_not_set_raises(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MISSING_TOKEN", None)
            auth = BearerTokenAuth("$MISSING_TOKEN")
            with pytest.raises(ValueError, match="Environment variable 'MISSING_TOKEN' is not set"):
                auth.get_headers()

    def test_is_auth_provider(self) -> None:
        auth = BearerTokenAuth("token")
        assert isinstance(auth, AuthProvider)


class TestAPIKeyAuth:
    """Tests for APIKeyAuth provider."""

    def test_header_based_api_key(self) -> None:
        auth = APIKeyAuth("my-api-key", header_name="X-API-Key")
        headers = auth.get_headers()
        assert headers == {"X-API-Key": "my-api-key"}
        assert auth.get_query_params() == {}

    def test_query_param_based_api_key(self) -> None:
        auth = APIKeyAuth("my-api-key", query_param="api_key")
        params = auth.get_query_params()
        assert params == {"api_key": "my-api-key"}
        assert auth.get_headers() == {}

    def test_both_header_and_query(self) -> None:
        auth = APIKeyAuth("my-api-key", header_name="X-API-Key", query_param="api_key")
        headers = auth.get_headers()
        params = auth.get_query_params()
        assert headers == {"X-API-Key": "my-api-key"}
        assert params == {"api_key": "my-api-key"}

    def test_default_to_header_if_neither_specified(self) -> None:
        auth = APIKeyAuth("my-api-key")
        headers = auth.get_headers()
        assert headers == {"X-API-Key": "my-api-key"}
        assert auth.get_query_params() == {}

    def test_key_property(self) -> None:
        auth = APIKeyAuth("test-key")
        assert auth.key == "test-key"

    def test_environment_variable_key(self) -> None:
        with mock.patch.dict(os.environ, {"API_KEY": "env-api-key"}):
            auth = APIKeyAuth("$API_KEY", header_name="X-Custom-Key")
            headers = auth.get_headers()
            assert headers == {"X-Custom-Key": "env-api-key"}

    def test_environment_variable_not_set_raises(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MISSING_KEY", None)
            auth = APIKeyAuth("$MISSING_KEY")
            with pytest.raises(ValueError, match="Environment variable 'MISSING_KEY' is not set"):
                auth.get_headers()

    def test_is_auth_provider(self) -> None:
        auth = APIKeyAuth("key")
        assert isinstance(auth, AuthProvider)


class TestCompositeAuth:
    """Tests for CompositeAuth provider."""

    def test_combines_headers(self) -> None:
        auth = CompositeAuth(
            [
                BearerTokenAuth("my-token"),
                APIKeyAuth("tenant-123", header_name="X-Tenant-ID"),
            ]
        )
        headers = auth.get_headers()
        assert headers == {
            "Authorization": "Bearer my-token",
            "X-Tenant-ID": "tenant-123",
        }

    def test_combines_query_params(self) -> None:
        auth = CompositeAuth(
            [
                APIKeyAuth("key1", query_param="api_key"),
                APIKeyAuth("key2", query_param="tenant_key"),
            ]
        )
        params = auth.get_query_params()
        assert params == {"api_key": "key1", "tenant_key": "key2"}

    def test_later_providers_override(self) -> None:
        auth = CompositeAuth(
            [
                APIKeyAuth("first-key", header_name="X-Key"),
                APIKeyAuth("second-key", header_name="X-Key"),
            ]
        )
        headers = auth.get_headers()
        assert headers == {"X-Key": "second-key"}

    def test_empty_providers_list(self) -> None:
        auth = CompositeAuth([])
        assert auth.get_headers() == {}
        assert auth.get_query_params() == {}

    def test_mixed_headers_and_query_params(self) -> None:
        auth = CompositeAuth(
            [
                BearerTokenAuth("token"),
                APIKeyAuth("key", query_param="api_key"),
            ]
        )
        headers = auth.get_headers()
        params = auth.get_query_params()
        assert headers == {"Authorization": "Bearer token"}
        assert params == {"api_key": "key"}

    def test_is_auth_provider(self) -> None:
        auth = CompositeAuth([])
        assert isinstance(auth, AuthProvider)
