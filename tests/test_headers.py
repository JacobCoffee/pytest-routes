"""Tests for HTTP header generation strategies."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from pytest_routes.generation.headers import (
    ACCEPT_STRATEGY,
    AUTHORIZATION_STRATEGY,
    CONTENT_TYPE_STRATEGY,
    USER_AGENT_STRATEGY,
    generate_headers,
    generate_optional_headers,
    register_header_strategy,
)


class TestHeaderStrategies:
    """Tests for predefined header strategies."""

    def test_content_type_strategy(self):
        """Test Content-Type header strategy generates valid values."""

        @given(value=CONTENT_TYPE_STRATEGY)
        def check(value):
            assert isinstance(value, str)
            assert len(value) > 0
            # Should be valid MIME types
            assert "/" in value

        check()

    def test_accept_strategy(self):
        """Test Accept header strategy generates valid values."""

        @given(value=ACCEPT_STRATEGY)
        def check(value):
            assert isinstance(value, str)
            assert len(value) > 0

        check()

    def test_authorization_strategy(self):
        """Test Authorization header strategy generates Bearer tokens."""

        @given(value=AUTHORIZATION_STRATEGY)
        def check(value):
            assert isinstance(value, str)
            assert value.startswith("Bearer ")
            # Token should be reasonable length
            token = value.removeprefix("Bearer ")
            assert 20 <= len(token) <= 64

        check()

    def test_user_agent_strategy(self):
        """Test User-Agent header strategy generates valid values."""

        @given(value=USER_AGENT_STRATEGY)
        def check(value):
            assert isinstance(value, str)
            assert len(value) > 0

        check()


class TestGenerateHeaders:
    """Tests for header generation function."""

    def test_empty_headers(self):
        """Test generating empty headers when nothing specified."""
        strategy = generate_headers()

        @given(headers=strategy)
        def check(headers):
            assert isinstance(headers, dict)
            assert len(headers) == 0

        check()

    def test_include_content_type(self):
        """Test including Content-Type header."""
        strategy = generate_headers(include_content_type=True)

        @given(headers=strategy)
        def check(headers):
            assert isinstance(headers, dict)
            assert "Content-Type" in headers
            assert isinstance(headers["Content-Type"], str)

        check()

    def test_include_accept(self):
        """Test including Accept header."""
        strategy = generate_headers(include_accept=True)

        @given(headers=strategy)
        def check(headers):
            assert isinstance(headers, dict)
            assert "Accept" in headers
            assert isinstance(headers["Accept"], str)

        check()

    def test_include_authorization(self):
        """Test including Authorization header."""
        strategy = generate_headers(include_authorization=True)

        @given(headers=strategy)
        def check(headers):
            assert isinstance(headers, dict)
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Bearer ")

        check()

    def test_custom_header_specs(self):
        """Test generating custom headers from specs."""
        strategy = generate_headers(
            header_specs={
                "X-Request-ID": str,
                "X-Trace-ID": str,
            }
        )

        @given(headers=strategy)
        def check(headers):
            assert isinstance(headers, dict)
            assert "X-Request-ID" in headers
            assert "X-Trace-ID" in headers
            assert isinstance(headers["X-Request-ID"], str)
            assert isinstance(headers["X-Trace-ID"], str)

        check()

    def test_combined_standard_and_custom_headers(self):
        """Test generating both standard and custom headers."""
        strategy = generate_headers(
            header_specs={"X-Custom": str},
            include_accept=True,
            include_content_type=True,
        )

        @given(headers=strategy)
        def check(headers):
            assert isinstance(headers, dict)
            assert "X-Custom" in headers
            assert "Accept" in headers
            assert "Content-Type" in headers
            assert len(headers) == 3

        check()

    def test_all_header_values_are_strings(self):
        """Test that all generated header values are strings (HTTP requirement)."""
        strategy = generate_headers(
            header_specs={
                "X-Custom-1": str,
                "X-Custom-2": str,
            },
            include_accept=True,
            include_content_type=True,
            include_authorization=True,
        )

        @given(headers=strategy)
        def check(headers):
            assert isinstance(headers, dict)
            for key, value in headers.items():
                assert isinstance(key, str), f"Header name {key} must be string"
                assert isinstance(value, str), f"Header value for {key} must be string"

        check()


class TestGenerateOptionalHeaders:
    """Tests for optional header generation."""

    def test_only_required_headers(self):
        """Test generating only required headers."""
        strategy = generate_optional_headers(
            required_headers={"Authorization": str},
        )

        @given(headers=strategy)
        def check(headers):
            assert isinstance(headers, dict)
            assert "Authorization" in headers
            assert isinstance(headers["Authorization"], str)

        check()

    def test_required_and_optional_headers(self):
        """Test generating required and optional headers."""
        strategy = generate_optional_headers(
            required_headers={"Authorization": str},
            optional_headers={"X-Request-ID": str, "X-Trace-ID": str},
        )

        @given(headers=strategy)
        def check(headers):
            assert isinstance(headers, dict)
            # Required header always present
            assert "Authorization" in headers
            # Optional headers may or may not be present
            # (can't assert specific presence, but types should be correct if present)
            for key, value in headers.items():
                assert isinstance(key, str)
                assert isinstance(value, str)

        check()

    def test_only_optional_headers(self):
        """Test generating only optional headers."""
        strategy = generate_optional_headers(
            optional_headers={"X-Request-ID": str},
        )

        @given(headers=strategy)
        def check(headers):
            assert isinstance(headers, dict)
            # Header may or may not be present
            if "X-Request-ID" in headers:
                assert isinstance(headers["X-Request-ID"], str)

        check()

    def test_empty_optional_headers(self):
        """Test generating with no headers specified."""
        strategy = generate_optional_headers()

        @given(headers=strategy)
        def check(headers):
            assert isinstance(headers, dict)
            assert len(headers) == 0

        check()

    def test_optional_headers_sometimes_omitted(self):
        """Test that optional headers are sometimes omitted."""
        from hypothesis import settings

        strategy = generate_optional_headers(
            optional_headers={
                "X-Header-1": str,
                "X-Header-2": str,
                "X-Header-3": str,
            },
        )

        # Track whether we see different combinations
        seen_header_counts = set()

        @given(headers=strategy)
        @settings(max_examples=100)
        def check(headers):
            assert isinstance(headers, dict)
            seen_header_counts.add(len(headers))
            # All present headers should be strings
            for key, value in headers.items():
                assert isinstance(key, str)
                assert isinstance(value, str)

        check()

        # We should see variation in header presence
        # (with 3 optional headers and 100 examples, very likely to see different counts)
        assert len(seen_header_counts) > 1, "Optional headers should vary in presence"


class TestRegisterHeaderStrategy:
    """Tests for custom header strategy registration."""

    def test_register_custom_header_strategy(self):
        """Test registering a custom strategy for a header."""
        # Register custom strategy for X-Custom-ID that generates UUIDs
        custom_strategy = st.uuids().map(str)
        register_header_strategy("X-Custom-ID", custom_strategy)

        # Generate headers using the custom strategy
        strategy = generate_headers(header_specs={"X-Custom-ID": str})

        @given(headers=strategy)
        def check(headers):
            assert "X-Custom-ID" in headers
            # Should be UUID format (has hyphens)
            assert "-" in headers["X-Custom-ID"]

        check()

    def test_custom_strategy_overrides_default(self):
        """Test that custom strategies override defaults."""
        # Register custom Content-Type strategy
        custom_strategy = st.just("application/custom")
        register_header_strategy("content-type", custom_strategy)

        # Generate headers
        strategy = generate_headers(include_content_type=True)

        @given(headers=strategy)
        def check(headers):
            assert headers["Content-Type"] == "application/custom"

        check()

    def test_header_name_case_insensitive(self):
        """Test that header name registration is case-insensitive."""
        # Register with mixed case
        custom_strategy = st.just("test-value")
        register_header_strategy("X-Custom-Header", custom_strategy)

        # Use with different case
        strategy = generate_headers(header_specs={"x-custom-header": str})

        @given(headers=strategy)
        def check(headers):
            assert headers["x-custom-header"] == "test-value"

        check()


class TestHeaderValueConstraints:
    """Tests for HTTP header value constraints."""

    def test_headers_no_control_characters(self):
        """Test that generated headers don't contain control characters."""
        strategy = generate_headers(
            header_specs={
                "X-Custom-1": str,
                "X-Custom-2": str,
            }
        )

        @given(headers=strategy)
        def check(headers):
            for key, value in headers.items():
                # Should not contain control characters
                for char in value:
                    # Printable or whitespace (but not \r\n)
                    assert char.isprintable() or char in (" ", "\t"), (
                        f"Header {key} contains invalid character: {char!r}"
                    )
                # Should not contain CR or LF (HTTP header injection)
                assert "\r" not in value, f"Header {key} contains CR"
                assert "\n" not in value, f"Header {key} contains LF"

        check()

    def test_headers_reasonable_length(self):
        """Test that generated headers have reasonable lengths."""
        strategy = generate_headers(
            header_specs={"X-Custom": str},
        )

        @given(headers=strategy)
        def check(headers):
            for key, value in headers.items():
                # Should have reasonable length (not empty, not too long)
                assert 1 <= len(value) <= 100, f"Header {key} has invalid length: {len(value)}"

        check()
