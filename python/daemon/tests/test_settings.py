from pathlib import Path

import pytest

from crawl_daemon.settings import Settings, default_data_dir


def test_defaults() -> None:
    settings = Settings.from_env({})
    assert settings == Settings()
    assert settings.max_parallel_jobs == 2
    assert settings.parse_cache is True


def test_env_overrides() -> None:
    settings = Settings.from_env(
        {
            "CRAWLD_DEFAULT_MAX_PAGES": "50",
            "CRAWLD_REQUEST_TIMEOUT": "2.5",
            "CRAWLD_PARSE_CACHE": "off",
            "CRAWLD_DATABASE_URL": "postgresql://localhost/crawls",
            "CRAWLD_PORT": "9000",
            "UNRELATED": "x",
        }
    )
    assert settings.default_max_pages == 50
    assert settings.request_timeout == 2.5
    assert settings.parse_cache is False
    assert settings.database_url == "postgresql://localhost/crawls"
    assert settings.port == 9000


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CRAWLD_MAX_CONCURRENCY", "lots"),
        ("CRAWLD_PARSE_CACHE", "maybe"),
        ("CRAWLD_REQUEST_TIMEOUT", "soon"),
    ],
)
def test_invalid_env_value(name: str, value: str) -> None:
    with pytest.raises(ValueError, match=name):
        Settings.from_env({name: value})


@pytest.mark.parametrize(
    "overrides",
    [{"max_parallel_jobs": 0}, {"request_timeout": 0}, {"port": 70000}, {"default_max_pages": 0}],
)
def test_out_of_range(overrides: dict[str, int]) -> None:
    with pytest.raises(ValueError):  # noqa: PT011
        Settings(**overrides)  # type: ignore[arg-type]


def test_data_dir_setting_wins(tmp_path: Path) -> None:
    assert Settings(data_dir=str(tmp_path)).resolved_data_dir == tmp_path


HOME = Path("/home/me")


@pytest.mark.parametrize(
    ("platform", "env", "expected"),
    [
        ("win32", {"LOCALAPPDATA": "C:/Users/me/AppData/Local"}, Path("C:/Users/me/AppData/Local")),
        ("win32", {}, HOME / "AppData" / "Local"),
        ("darwin", {}, HOME / "Library" / "Application Support"),
        ("linux", {"XDG_STATE_HOME": "/xdg/state"}, Path("/xdg/state")),
        ("linux", {}, HOME / ".local" / "state"),
    ],
)
def test_default_data_dir(platform: str, env: dict[str, str], expected: Path) -> None:
    assert default_data_dir(platform, env, HOME) == expected / "crawld"


def test_default_data_dir_env_override() -> None:
    assert default_data_dir("linux", {"CRAWLD_DATA_DIR": "/srv/crawld"}, HOME) == Path(
        "/srv/crawld"
    )
