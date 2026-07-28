import httpx
import pytest

from tests.integration.helpers.sites import SITE_FACTORIES, SITES
from tests.integration.helpers.website import make_app

TEST_HOST = "testsite.local"


@pytest.fixture
def site(
    request: pytest.FixtureRequest,
) -> tuple[str, httpx.BaseTransport, list[tuple[str, str, float]]]:
    """Builds an in-process site for the named entry in SITES/SITE_FACTORIES.

    Returns (url, transport, requests): a real-looking start URL, an
    ASGITransport routing that host to the in-memory app, and a recorder
    of requests the app received.
    """
    name = request.param
    if name in SITE_FACTORIES:
        pages = SITE_FACTORIES[name](TEST_HOST)
    else:
        pages = SITES[name]
    app, requests = make_app(pages)
    transport = httpx.ASGITransport(app=app)
    return f"http://{TEST_HOST}/", transport, requests
