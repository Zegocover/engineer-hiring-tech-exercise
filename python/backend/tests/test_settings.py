import pytest

from crawler_api.settings import Settings


def test_defaults() -> None:
    settings = Settings.from_env({})
    assert settings == Settings()
    assert settings.default_max_pages == 1000
    assert settings.max_pages_limit == 10_000
    assert settings.max_concurrency == 32


def test_environment_overrides() -> None:
    settings = Settings.from_env(
        {
            "CRAWLER_API_DEFAULT_MAX_PAGES": "50",
            "CRAWLER_API_REQUEST_TIMEOUT": "2.5",
            "CRAWLER_API_USER_AGENT": "test-agent",
            "UNRELATED": "ignored",
        }
    )
    assert settings.default_max_pages == 50
    assert settings.request_timeout == 2.5
    assert settings.user_agent == "test-agent"
    assert settings.max_concurrency == Settings().max_concurrency


def test_invalid_value_names_the_variable() -> None:
    with pytest.raises(ValueError, match="CRAWLER_API_MAX_CONNECTIONS"):
        Settings.from_env({"CRAWLER_API_MAX_CONNECTIONS": "lots"})
