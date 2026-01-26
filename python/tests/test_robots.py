"""Tests for robots.txt helpers."""

import pytest

from crawler import robots


@pytest.mark.parametrize(
    ("robots_txt", "url", "expected"),
    [
        pytest.param(
            "User-agent: *\nDisallow: /private\n",
            "https://example.com/public/page",
            True,
            id="allow-public",
        ),
        pytest.param(
            "User-agent: *\nDisallow: /private\n",
            "https://example.com/private/page",
            False,
            id="disallow-private",
        ),
        pytest.param(
            "User-agent: *\nAllow: /private/page\nDisallow: /private\n",
            "https://example.com/private/page",
            True,
            id="allow-overrides",
        ),
    ],
)
def test_parse_robots_txt_and_is_allowed(
    robots_txt: str, url: str, expected: bool
) -> None:
    policy = robots.parse_robots_txt(robots_txt)
    assert policy.is_allowed(url) is expected


def test_robots_url_for() -> None:
    assert (
        robots.robots_url_for("https://example.com/path")
        == "https://example.com/robots.txt"
    )

    with pytest.raises(ValueError):
        robots.robots_url_for("not-a-url")


@pytest.mark.parametrize(
    ("robots_txt", "url", "expected"),
    [
        pytest.param(
            "#comment\nNOPE\nUser-agent: *\nAllow: /public\n",
            "https://example.com/public/page",
            True,
            id="ignores-comments-and-invalid-lines",
        ),
        pytest.param(
            "User-agent: Googlebot\nDisallow: /private\n",
            "https://example.com/private/page",
            True,
            id="ignores-other-user-agent",
        ),
    ],
)
def test_parse_robots_txt_edge_cases(
    robots_txt: str, url: str, expected: bool
) -> None:
    policy = robots.parse_robots_txt(robots_txt)
    assert policy.is_allowed(url) is expected


@pytest.mark.parametrize(
    ("fake_urlopen", "label"),
    [
        pytest.param(
            lambda req, timeout: type(
                "DummyResponse",
                (),
                {
                    "status": 404,
                    "__enter__": lambda self: self,
                    "__exit__": lambda self, exc_type, exc, tb: False,
                },
            )(),
            "non-200-response",
            id="non-200-response",
        ),
        pytest.param(
            lambda req, timeout: (_ for _ in ()).throw(RuntimeError("boom")),
            "exception",
            id="exception",
        ),
    ],
)
def test_fetch_robots_policy_fallbacks(
    monkeypatch, fake_urlopen, label
) -> None:
    monkeypatch.setattr(robots.request, "urlopen", fake_urlopen)
    policy = robots.fetch_robots_policy(
        "https://example.com", user_agent="test", timeout_s=1
    )

    assert policy.is_allowed("https://example.com/anything") is True


def test_robots_policy_defaults_to_allow() -> None:
    policy = robots.RobotsPolicy(allow=(), disallow=())

    assert policy.is_allowed("https://example.com/anything") is True
