"""Header generation strategies for HTTP requests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hypothesis import strategies as st

if TYPE_CHECKING:
    from hypothesis.strategies import SearchStrategy

# Registry for custom header strategies
_HEADER_STRATEGIES: dict[str, SearchStrategy[str]] = {}

# Common header value strategies
CONTENT_TYPE_STRATEGY = st.sampled_from(
    [
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain",
        "text/html",
        "application/xml",
    ]
)

ACCEPT_STRATEGY = st.sampled_from(
    [
        "application/json",
        "*/*",
        "text/html",
        "application/xml",
        "text/plain",
    ]
)

AUTHORIZATION_STRATEGY = st.builds(
    lambda token: f"Bearer {token}",
    st.text(
        alphabet=st.characters(
            blacklist_categories=("Cc", "Cs"),
            blacklist_characters=(" ", "\t", "\n", "\r"),
        ),
        min_size=20,
        max_size=64,
    ),
)

USER_AGENT_STRATEGY = st.sampled_from(
    [
        "pytest-routes/1.0",
        "Mozilla/5.0 (compatible; pytest-routes/1.0)",
        "python-httpx/0.27.0",
    ]
)

# Default strategies for common headers
_DEFAULT_HEADER_STRATEGIES: dict[str, SearchStrategy[str]] = {
    "content-type": CONTENT_TYPE_STRATEGY,
    "accept": ACCEPT_STRATEGY,
    "authorization": AUTHORIZATION_STRATEGY,
    "user-agent": USER_AGENT_STRATEGY,
}


def register_header_strategy(header_name: str, strategy: SearchStrategy[str]) -> None:
    """Register a custom strategy for a specific HTTP header.

    This allows users to override default header generation or add
    strategies for custom headers.

    Args:
        header_name: The HTTP header name (case-insensitive).
        strategy: A Hypothesis strategy that generates string values.

    Example:
        >>> from hypothesis import strategies as st
        >>> register_header_strategy("X-Custom-ID", st.uuids().map(str))
    """
    _HEADER_STRATEGIES[header_name.lower()] = strategy


def _get_strategy_for_header(
    header_name: str,
    header_type: type | None = None,  # noqa: ARG001
) -> SearchStrategy[str]:
    """Get the strategy for a specific header.

    Args:
        header_name: The HTTP header name (case-insensitive).
        header_type: Optional type hint for the header value (reserved for future use).

    Returns:
        A Hypothesis strategy that generates string values.
    """
    normalized_name = header_name.lower()

    # Check custom registry first
    if normalized_name in _HEADER_STRATEGIES:
        return _HEADER_STRATEGIES[normalized_name]

    # Check default strategies
    if normalized_name in _DEFAULT_HEADER_STRATEGIES:
        return _DEFAULT_HEADER_STRATEGIES[normalized_name]

    # Fallback to generic text strategy for HTTP headers
    # HTTP headers should be printable ASCII, no control chars
    return st.text(
        alphabet=st.characters(
            min_codepoint=32,  # Space
            max_codepoint=126,  # Tilde (printable ASCII)
            blacklist_characters=("\r", "\n"),
        ),
        min_size=1,
        max_size=100,
    )


def generate_headers(
    header_specs: dict[str, type] | None = None,
    *,
    include_content_type: bool = False,
    include_accept: bool = False,
    include_authorization: bool = False,
) -> SearchStrategy[dict[str, str]]:
    """Generate HTTP headers based on specifications.

    All header values are generated as strings to comply with HTTP standards.

    Args:
        header_specs: Mapping of header names to their types. If None, only
            optional headers based on flags will be included.
        include_content_type: Whether to include Content-Type header.
        include_accept: Whether to include Accept header.
        include_authorization: Whether to include Authorization header.

    Returns:
        A Hypothesis strategy that generates dictionaries of HTTP headers.

    Example:
        >>> from hypothesis import strategies as st
        >>> # Generate custom headers
        >>> header_strategy = generate_headers(
        ...     header_specs={"X-Request-ID": str, "X-Trace-ID": str},
        ...     include_accept=True,
        ... )
        >>> # Generate only standard headers
        >>> standard_headers = generate_headers(
        ...     include_content_type=True,
        ...     include_accept=True,
        ... )
    """
    strategies: dict[str, SearchStrategy[str]] = {}

    # Add specified headers
    if header_specs:
        for header_name, header_type in header_specs.items():
            strategies[header_name] = _get_strategy_for_header(header_name, header_type)

    # Add optional standard headers (check custom registry for overrides)
    if include_content_type:
        strategies["Content-Type"] = _get_strategy_for_header("Content-Type")

    if include_accept:
        strategies["Accept"] = _get_strategy_for_header("Accept")

    if include_authorization:
        strategies["Authorization"] = _get_strategy_for_header("Authorization")

    # If no headers specified, return empty dict
    if not strategies:
        return st.just({})

    # Build a strategy that generates a dict with all specified headers
    return st.fixed_dictionaries(strategies)


def generate_optional_headers(
    required_headers: dict[str, type] | None = None,
    optional_headers: dict[str, type] | None = None,
) -> SearchStrategy[dict[str, str]]:
    """Generate headers with required and optional fields.

    This is useful for testing routes where some headers are mandatory
    and others are optional.

    Args:
        required_headers: Headers that must always be present.
        optional_headers: Headers that may or may not be included.

    Returns:
        A Hypothesis strategy that generates dictionaries of HTTP headers.

    Example:
        >>> header_strategy = generate_optional_headers(
        ...     required_headers={"Authorization": str},
        ...     optional_headers={"X-Request-ID": str, "X-Trace-ID": str},
        ... )
    """
    required = required_headers or {}
    optional = optional_headers or {}

    # Build strategies for required headers
    required_strategies: dict[str, SearchStrategy[str]] = {
        header_name: _get_strategy_for_header(header_name, header_type) for header_name, header_type in required.items()
    }

    # Build strategies for optional headers
    optional_strategies: dict[str, SearchStrategy[str]] = {
        header_name: _get_strategy_for_header(header_name, header_type) for header_name, header_type in optional.items()
    }

    if not required_strategies and not optional_strategies:
        return st.just({})

    # Generate required headers
    required_dict_strategy = st.just({}) if not required_strategies else st.fixed_dictionaries(required_strategies)

    # Generate optional headers (some may be omitted)
    if not optional_strategies:
        return required_dict_strategy

    # Use fixed_dictionaries with optional parameter
    # Pass empty dict for required (already handled above) and optionals in optional param
    if not required_strategies:
        # Only optional headers
        return st.fixed_dictionaries({}, optional=optional_strategies)

    # Both required and optional headers
    return st.fixed_dictionaries(required_strategies, optional=optional_strategies)
