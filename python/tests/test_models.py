"""Tests for the value objects' small amount of behaviour."""

from __future__ import annotations

import pytest

from crawler.models import FetchResult


@pytest.mark.parametrize(
    ("status_code", "error", "expected_ok"),
    [
        (200, None, True),
        (301, None, True),  # redirects are resolved before we see them
        (399, None, True),
        (404, None, False),
        (500, None, False),
        (None, "timeout", False),
        (200, "unexpected", False),  # a transport error trumps any status
    ],
)
def test_fetch_result_ok(status_code: int | None, error: str | None, expected_ok: bool) -> None:
    result = FetchResult(
        requested_url="http://x/",
        final_url="http://x/",
        status_code=status_code,
        error=error,
    )
    assert result.ok is expected_ok
