import ast
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

import site_crawler

PUBLIC_API = {
    # engine
    "Crawler",
    # models
    "ConfigError",
    "CrawlConfig",
    "CrawlStats",
    "FetchError",
    "FetchResult",
    "PageResult",
    # interfaces
    "Fetcher",
    "Parser",
    "Writer",
    # default implementations
    "DefaultHttpxFetcher",
    "DefaultSelectolaxParser",
    "TextWriter",
    "JsonLinesWriter",
}

SUBPACKAGES = ["models", "interfaces", "fetchers", "parsers", "writers", "core"]


def test_public_api_is_exported() -> None:
    assert set(site_crawler.__all__) == PUBLIC_API
    for name in PUBLIC_API:
        assert getattr(site_crawler, name) is not None


@pytest.mark.parametrize("subpackage", SUBPACKAGES)
def test_subpackage_imports_on_its_own(subpackage: str) -> None:
    # A fresh interpreter catches import cycles that a warm module cache hides.
    result = subprocess.run(
        [sys.executable, "-c", f"import site_crawler.{subpackage}"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _package_imports(subpackage: str) -> set[str]:
    """``site_crawler.*`` modules imported by the source files of ``subpackage``."""
    root = Path(site_crawler.__file__).parent / subpackage
    found: set[str] = set()
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)
            elif isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
    return {m for m in found if m == "site_crawler" or m.startswith("site_crawler.")}


# Layering: models <- interfaces <- fetchers/parsers/writers <- core
ALLOWED_IMPORTS = {
    "models": {"models"},
    "interfaces": {"models", "interfaces"},
    "fetchers": {"models", "interfaces", "fetchers"},
    "parsers": {"models", "interfaces", "parsers"},
    "writers": {"models", "interfaces", "writers"},
    "core": {"models", "interfaces", "fetchers", "parsers", "writers", "core"},
}


@pytest.mark.parametrize("subpackage", SUBPACKAGES)
def test_layering_is_respected(subpackage: str) -> None:
    layers = {m.split(".")[1] if "." in m else "<root>" for m in _package_imports(subpackage)}
    assert layers <= ALLOWED_IMPORTS[subpackage]


@pytest.mark.parametrize("subpackage", SUBPACKAGES)
def test_subpackage_exports_match_all(subpackage: str) -> None:
    module = importlib.import_module(f"site_crawler.{subpackage}")
    for name in module.__all__:
        assert hasattr(module, name)
