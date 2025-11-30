"""Authentication provider implementations for pytest-routes.

This module provides various authentication strategies for route testing,
including Bearer tokens, API keys, and composite authentication.

Example:
    Basic usage with Bearer token::

        from pytest_routes.auth import BearerTokenAuth

        auth = BearerTokenAuth("my-secret-token")
        headers = auth.get_headers()
        # {"Authorization": "Bearer my-secret-token"}

    Using API key authentication::

        from pytest_routes.auth import APIKeyAuth

        # Header-based API key
        auth = APIKeyAuth("my-api-key", header_name="X-API-Key")
        headers = auth.get_headers()
        # {"X-API-Key": "my-api-key"}

        # Query parameter-based API key
        auth = APIKeyAuth("my-api-key", query_param="api_key")
        params = auth.get_query_params()
        # {"api_key": "my-api-key"}

    Combining multiple authentication methods::

        from pytest_routes.auth import BearerTokenAuth, APIKeyAuth, CompositeAuth

        auth = CompositeAuth(
            [
                BearerTokenAuth("token"),
                APIKeyAuth("key", header_name="X-Tenant-ID"),
            ]
        )
        headers = auth.get_headers()
        # {"Authorization": "Bearer token", "X-Tenant-ID": "key"}
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class AuthProvider(ABC):
    """Abstract base class for authentication providers.

    Authentication providers are responsible for generating the headers
    and/or query parameters needed to authenticate requests during
    route smoke testing.

    Subclasses must implement:
        - get_headers(): Return authentication headers
        - get_query_params(): Return authentication query parameters

    Example:
        Creating a custom auth provider::

            class CustomAuth(AuthProvider):
                def __init__(self, secret: str) -> None:
                    self.secret = secret

                def get_headers(self) -> dict[str, str]:
                    return {"X-Custom-Auth": self.secret}

                def get_query_params(self) -> dict[str, str]:
                    return {}
    """

    @abstractmethod
    def get_headers(self) -> dict[str, str]:
        """Get authentication headers.

        Returns:
            Dictionary of header name to header value.
        """
        ...

    @abstractmethod
    def get_query_params(self) -> dict[str, str]:
        """Get authentication query parameters.

        Returns:
            Dictionary of query parameter name to value.
        """
        ...


class NoAuth(AuthProvider):
    """No authentication provider.

    This is the default authentication provider that adds no
    authentication headers or query parameters.

    Example:
        >>> auth = NoAuth()
        >>> auth.get_headers()
        {}
        >>> auth.get_query_params()
        {}
    """

    def get_headers(self) -> dict[str, str]:
        """Return empty headers dict."""
        return {}

    def get_query_params(self) -> dict[str, str]:
        """Return empty query params dict."""
        return {}


class BearerTokenAuth(AuthProvider):
    """Bearer token authentication provider.

    Adds an Authorization header with a Bearer token. The token can be
    provided directly or read from an environment variable.

    Args:
        token: The bearer token value. If it starts with "$", it will be
            treated as an environment variable name.

    Example:
        Direct token::

            auth = BearerTokenAuth("my-secret-token")
            auth.get_headers()
            # {"Authorization": "Bearer my-secret-token"}

        Environment variable::

            # Set API_TOKEN=my-secret-token
            auth = BearerTokenAuth("$API_TOKEN")
            auth.get_headers()
            # {"Authorization": "Bearer my-secret-token"}
    """

    def __init__(self, token: str) -> None:
        """Initialize Bearer token authentication.

        Args:
            token: The bearer token. If prefixed with "$", reads from
                environment variable.
        """
        self._token_spec = token

    @property
    def token(self) -> str:
        """Resolve the token value.

        Returns:
            The actual token value, resolving environment variables if needed.

        Raises:
            ValueError: If an environment variable is specified but not set.
        """
        if self._token_spec.startswith("$"):
            env_var = self._token_spec[1:]
            value = os.environ.get(env_var)
            if value is None:
                msg = f"Environment variable '{env_var}' is not set"
                raise ValueError(msg)
            return value
        return self._token_spec

    def get_headers(self) -> dict[str, str]:
        """Get Authorization header with Bearer token.

        Returns:
            Dictionary with Authorization header.
        """
        return {"Authorization": f"Bearer {self.token}"}

    def get_query_params(self) -> dict[str, str]:
        """Return empty query params dict."""
        return {}


class APIKeyAuth(AuthProvider):
    """API key authentication provider.

    Adds an API key either as a header or query parameter. The key can be
    provided directly or read from an environment variable.

    Args:
        key: The API key value. If it starts with "$", it will be
            treated as an environment variable name.
        header_name: Name of the header to use (e.g., "X-API-Key").
            If provided, the key is sent as a header.
        query_param: Name of the query parameter to use (e.g., "api_key").
            If provided, the key is sent as a query parameter.

    Note:
        Either header_name or query_param should be specified, not both.
        If both are specified, the key is sent in both places.
        If neither is specified, header_name defaults to "X-API-Key".

    Example:
        Header-based API key::

            auth = APIKeyAuth("my-key", header_name="X-API-Key")
            auth.get_headers()
            # {"X-API-Key": "my-key"}

        Query parameter-based API key::

            auth = APIKeyAuth("my-key", query_param="api_key")
            auth.get_query_params()
            # {"api_key": "my-key"}
    """

    def __init__(
        self,
        key: str,
        *,
        header_name: str | None = None,
        query_param: str | None = None,
    ) -> None:
        """Initialize API key authentication.

        Args:
            key: The API key. If prefixed with "$", reads from environment variable.
            header_name: Header name to use (e.g., "X-API-Key").
            query_param: Query parameter name to use (e.g., "api_key").
        """
        self._key_spec = key
        self.header_name = header_name
        self.query_param = query_param

        # Default to header if neither specified
        if header_name is None and query_param is None:
            self.header_name = "X-API-Key"

    @property
    def key(self) -> str:
        """Resolve the API key value.

        Returns:
            The actual key value, resolving environment variables if needed.

        Raises:
            ValueError: If an environment variable is specified but not set.
        """
        if self._key_spec.startswith("$"):
            env_var = self._key_spec[1:]
            value = os.environ.get(env_var)
            if value is None:
                msg = f"Environment variable '{env_var}' is not set"
                raise ValueError(msg)
            return value
        return self._key_spec

    def get_headers(self) -> dict[str, str]:
        """Get API key header if configured.

        Returns:
            Dictionary with API key header, or empty dict if using query param.
        """
        if self.header_name:
            return {self.header_name: self.key}
        return {}

    def get_query_params(self) -> dict[str, str]:
        """Get API key query parameter if configured.

        Returns:
            Dictionary with API key query param, or empty dict if using header.
        """
        if self.query_param:
            return {self.query_param: self.key}
        return {}


class CompositeAuth(AuthProvider):
    """Composite authentication provider that combines multiple providers.

    Useful when multiple authentication mechanisms are required (e.g.,
    Bearer token plus tenant ID header).

    Args:
        providers: Sequence of authentication providers to combine.

    Note:
        Headers and query parameters from later providers will override
        those from earlier providers if they have the same names.

    Example:
        Combining Bearer token with tenant header::

            auth = CompositeAuth(
                [
                    BearerTokenAuth("my-token"),
                    APIKeyAuth("tenant-123", header_name="X-Tenant-ID"),
                ]
            )
            auth.get_headers()
            # {"Authorization": "Bearer my-token", "X-Tenant-ID": "tenant-123"}
    """

    def __init__(self, providers: Sequence[AuthProvider]) -> None:
        """Initialize composite authentication.

        Args:
            providers: Sequence of auth providers to combine.
        """
        self.providers = list(providers)

    def get_headers(self) -> dict[str, str]:
        """Get combined headers from all providers.

        Returns:
            Merged dictionary of headers from all providers.
        """
        headers: dict[str, str] = {}
        for provider in self.providers:
            headers.update(provider.get_headers())
        return headers

    def get_query_params(self) -> dict[str, str]:
        """Get combined query parameters from all providers.

        Returns:
            Merged dictionary of query params from all providers.
        """
        params: dict[str, str] = {}
        for provider in self.providers:
            params.update(provider.get_query_params())
        return params
