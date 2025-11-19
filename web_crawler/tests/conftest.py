import pytest
import aiohttp.web


@pytest.fixture
def make_server(aiohttp_server):
    async def _make(routes: dict):
        app = aiohttp.web.Application()
        for path, handler in routes.items():
            app.router.add_get(path, handler)
        server = await aiohttp_server(app)
        base = f"http://{server.host}:{server.port}"
        return server, base

    return _make


def pytest_addoption(parser):
    parser.addoption(
        "--live-target",
        action="store",
        default=None,
        help="Enable running live network tests and provide the target URL (required to enable)",
    )


def pytest_configure(config):
    # If user explicitly requests running live tests, the option value must be a non-empty URL.
    val = config.getoption("--live-target")
    if val is not None:
        if not isinstance(val, str) or not val.strip():
            raise pytest.UsageError("--live-target requires a target URL, e.g. --live-target=https://example.com")


@pytest.fixture
def run_live_tests(request):
    # return True if the CLI option was provided (option value is the live target URL)
    return bool(request.config.getoption("--live-target"))


@pytest.fixture
def live_test_target(request):
    # the live target url is passed as the value of --run-live-tests
    return request.config.getoption("--live-target")
