"""One test per scenario in the crawl-api spec, through the real app."""

import asyncio

import httpx

from crawler_api.settings import Settings
from tests.conftest import ApiOpener
from tests.fakes import FakeSite, GatedSite
from tests.helpers import finish, poll, start

BASE = "https://example.com/"


def three_page_site(failing: set[str] | None = None) -> FakeSite:
    return FakeSite({BASE: ["/a", "/b"], f"{BASE}a": [], f"{BASE}b": []}, failing=failing)


async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Clients can start a crawl ---


async def test_start_a_crawl(api: ApiOpener) -> None:
    site = GatedSite({BASE: []}, gated={BASE})
    async with api(site) as client:
        response = await client.post("/crawls", json={"url": BASE})
        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "running"
        assert response.headers["location"] == f"/crawls/{body['id']}"
        # The crawl is still going: the request did not wait for it.
        assert (await client.get(f"/crawls/{body['id']}/status")).json()["status"] == "running"
        site.gate.set()
        assert (await finish(client, body["id"]))["status"] == "completed"


async def test_ids_are_unique(api: ApiOpener) -> None:
    async with api(three_page_site()) as client:
        assert await start(client) != await start(client)


# --- Invalid crawl requests are rejected ---


async def test_non_http_url_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post("/crawls", json={"url": "ftp://example.com/"})
    assert response.status_code == 422
    assert "http(s)" in response.json()["detail"][0]["msg"]
    assert (await client.get("/crawls")).json() == []


async def test_negative_depth_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post("/crawls", json={"url": BASE, "max_depth": -1})
    assert response.status_code == 422
    assert (await client.get("/crawls")).json() == []


# --- Server limits bound every crawl ---


async def test_default_page_budget_applied(api: ApiOpener) -> None:
    pages = {BASE: [f"/{n}" for n in range(5)], **{f"{BASE}{n}": [] for n in range(5)}}
    site = FakeSite(pages)
    async with api(site, Settings(default_max_pages=3)) as client:
        job_id = await start(client)
        detail = (await client.get(f"/crawls/{job_id}")).json()
        assert detail["limits"]["max_pages"] == 3
        status = await finish(client, job_id)
    assert status["stats"]["fetched"] <= 3
    assert sum(n for url, n in site.calls.items() if not url.endswith("robots.txt")) <= 3


async def test_page_budget_above_maximum_rejected(api: ApiOpener) -> None:
    async with api(three_page_site(), Settings(max_pages_limit=10)) as client:
        response = await client.post("/crawls", json={"url": BASE, "max_pages": 11})
        assert response.status_code == 422
        assert "at most 10" in response.json()["detail"][0]["msg"]
        assert (await client.get("/crawls")).json() == []


async def test_concurrency_above_maximum_rejected(api: ApiOpener) -> None:
    async with api(three_page_site(), Settings(max_concurrency=4)) as client:
        response = await client.post("/crawls", json={"url": BASE, "concurrency": 5})
        assert response.status_code == 422


# --- Clients can read a crawl's details ---


async def test_details_include_effective_limits(api: ApiOpener) -> None:
    settings = Settings(default_max_pages=50, default_concurrency=6)
    async with api(three_page_site(), settings) as client:
        job_id = await start(client, max_depth=2)
        detail = (await client.get(f"/crawls/{job_id}")).json()
    assert detail["id"] == job_id
    assert detail["url"] == BASE
    assert detail["limits"] == {
        "max_pages": 50,
        "max_depth": 2,
        "concurrency": 6,
        "respect_robots": True,
    }
    assert "error" in detail


async def test_details_of_unknown_crawl(client: httpx.AsyncClient) -> None:
    assert (await client.get("/crawls/nope")).status_code == 404


# --- Clients can poll a crawl's status ---


async def test_status_while_running(api: ApiOpener) -> None:
    site = GatedSite(
        {BASE: ["/a", "/hold"], f"{BASE}a": [], f"{BASE}hold": []}, gated={f"{BASE}hold"}
    )
    async with api(site) as client:
        job_id = await start(client)
        status = await poll(client, job_id, lambda body: body["stats"]["pages"] == 2)
        assert status["status"] == "running"
        assert status["finished_at"] is None
        assert "limits" not in status
        assert "url" not in status
        site.gate.set()
        await finish(client, job_id)


async def test_status_after_completion(api: ApiOpener) -> None:
    async with api(three_page_site(failing={f"{BASE}b"})) as client:
        status = await finish(client, await start(client))
    assert status["status"] == "completed"
    assert status["finished_at"] is not None
    assert status["stats"]["pages"] == 2
    assert status["stats"]["errors"] == 1


async def test_status_of_unknown_crawl(client: httpx.AsyncClient) -> None:
    assert (await client.get("/crawls/nope/status")).status_code == 404


# --- Clients can page through a crawl's results ---


async def test_read_results_in_pages(api: ApiOpener) -> None:
    pages = {BASE: ["/1", "/2", "/3", "/4"], **{f"{BASE}{n}": [] for n in "1234"}}
    async with api(FakeSite(pages)) as client:
        job_id = await start(client, concurrency=1)
        await finish(client, job_id)
        body = (await client.get(f"/crawls/{job_id}/pages?offset=2&limit=2")).json()
    assert body["total"] == 5
    assert (body["offset"], body["limit"]) == (2, 2)
    assert [item["url"] for item in body["items"]] == [f"{BASE}2", f"{BASE}3"]
    assert body["items"][0]["links"] == []


async def test_read_results_while_running(api: ApiOpener) -> None:
    site = GatedSite({BASE: ["/hold"], f"{BASE}hold": []}, gated={f"{BASE}hold"})
    async with api(site) as client:
        job_id = await start(client)
        await poll(client, job_id, lambda body: body["stats"]["pages"] == 1)
        body = (await client.get(f"/crawls/{job_id}/pages")).json()
        assert body["total"] == 1
        assert body["items"] == [{"url": BASE, "links": [f"{BASE}hold"]}]
        site.gate.set()
        await finish(client, job_id)


async def test_pages_of_unknown_crawl(client: httpx.AsyncClient) -> None:
    assert (await client.get("/crawls/nope/pages")).status_code == 404


async def test_pages_limit_out_of_range(api: ApiOpener) -> None:
    async with api(three_page_site()) as client:
        job_id = await start(client)
        assert (await client.get(f"/crawls/{job_id}/pages?limit=0")).status_code == 422
        assert (await client.get(f"/crawls/{job_id}/pages?offset=-1")).status_code == 422


# --- Clients can list the links a crawl found ---


async def test_links_deduplicated_across_pages(api: ApiOpener) -> None:
    pages = {BASE: ["/a", "/b"], f"{BASE}a": ["/b", "/c"], f"{BASE}b": [], f"{BASE}c": []}
    async with api(FakeSite(pages)) as client:
        job_id = await start(client, concurrency=1)
        await finish(client, job_id)
        body = (await client.get(f"/crawls/{job_id}/links")).json()
    assert body["items"] == [f"{BASE}a", f"{BASE}b", f"{BASE}c"]
    assert body["total"] == 3


async def test_links_not_followed_are_listed(api: ApiOpener) -> None:
    site = FakeSite({BASE: ["https://other.org/", "/a"], f"{BASE}a": []})
    async with api(site) as client:
        job_id = await start(client)
        await finish(client, job_id)
        links = (await client.get(f"/crawls/{job_id}/links")).json()["items"]
    assert "https://other.org/" in links


async def test_read_links_in_pages(api: ApiOpener) -> None:
    hrefs = [f"/{n}" for n in range(1, 6)]
    async with api(FakeSite({BASE: hrefs}), Settings(default_max_pages=1)) as client:
        job_id = await start(client)
        await finish(client, job_id)
        body = (await client.get(f"/crawls/{job_id}/links?offset=1&limit=2")).json()
    assert body["total"] == 5
    assert body["items"] == [f"{BASE}2", f"{BASE}3"]


async def test_links_of_unknown_crawl(client: httpx.AsyncClient) -> None:
    assert (await client.get("/crawls/nope/links")).status_code == 404


# --- Clients can list crawls ---


async def test_crawls_listed_newest_first(api: ApiOpener) -> None:
    site = FakeSite({"https://a.example/": [], "https://b.example/": []})
    async with api(site) as client:
        first = await start(client, "https://a.example/")
        second = await start(client, "https://b.example/")
        listed = (await client.get("/crawls")).json()
    assert [(c["id"], c["url"]) for c in listed] == [
        (second, "https://b.example/"),
        (first, "https://a.example/"),
    ]
    assert {"status", "stats"} <= listed[0].keys()


# --- Crawls follow the site-crawl rules ---


async def test_off_host_links_reported_but_not_fetched(api: ApiOpener) -> None:
    site = FakeSite({BASE: ["https://other.org/", "/a"], f"{BASE}a": ["/"]})
    async with api(site) as client:
        job_id = await start(client)
        await finish(client, job_id)
        items = (await client.get(f"/crawls/{job_id}/pages")).json()["items"]
    home = next(item for item in items if item["url"] == BASE)
    assert "https://other.org/" in home["links"]
    assert all(not item["url"].startswith("https://other.org") for item in items)
    assert not any(url.startswith("https://other.org") for url in site.calls)
    assert site.calls[BASE] == 1  # linked twice, fetched once


# --- Crawls run concurrently and independently ---


async def test_cancelling_one_crawl_leaves_another_running(api: ApiOpener) -> None:
    held = GatedSite({BASE: ["/hold"], f"{BASE}hold": []}, gated={f"{BASE}hold"})
    sites = iter([held, three_page_site()])
    async with api(lambda: next(sites)) as client:
        first = await start(client)
        second = await start(client)
        await poll(client, first, lambda body: body["stats"]["pages"] == 1)
        assert (await client.delete(f"/crawls/{first}")).status_code == 200
        status = await finish(client, second)
        assert status["status"] == "completed"
        assert status["stats"]["pages"] == 3
        assert (await client.get(f"/crawls/{first}/status")).json()["status"] == "cancelled"


# --- Clients can cancel a running crawl ---


async def test_cancel_running_crawl(api: ApiOpener) -> None:
    pages = {BASE: ["/1", "/2", "/hold"], f"{BASE}1": [], f"{BASE}2": [], f"{BASE}hold": []}
    site = GatedSite(pages, gated={f"{BASE}hold"})
    async with api(site) as client:
        job_id = await start(client)
        await poll(client, job_id, lambda body: body["stats"]["pages"] == 3)

        response = await client.delete(f"/crawls/{job_id}")

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        assert response.json()["finished_at"] is not None
        site.gate.set()
        await asyncio.sleep(0)
        body = (await client.get(f"/crawls/{job_id}/pages")).json()
        assert body["total"] == 3
        assert (await client.get(f"/crawls/{job_id}/status")).json()["stats"]["pages"] == 3


async def test_cancel_finished_crawl(api: ApiOpener) -> None:
    async with api(three_page_site()) as client:
        job_id = await start(client)
        await finish(client, job_id)
        response = await client.delete(f"/crawls/{job_id}")
        assert response.status_code == 409
        assert (await client.get(f"/crawls/{job_id}/status")).json()["status"] == "completed"


async def test_cancel_unknown_crawl(client: httpx.AsyncClient) -> None:
    assert (await client.delete("/crawls/nope")).status_code == 404


# --- Crawl failures are reported on the crawl ---


async def test_base_url_unreachable(api: ApiOpener) -> None:
    async with api(three_page_site(failing={BASE})) as client:
        status = await finish(client, await start(client))
    assert status["status"] == "failed"
    assert BASE in status["error"]


async def test_one_page_fails(api: ApiOpener) -> None:
    async with api(three_page_site(failing={f"{BASE}a"})) as client:
        status = await finish(client, await start(client))
    assert status["status"] == "completed"
    assert status["stats"]["errors"] == 1
    assert status["error"] is None


async def test_unexpected_error_fails_only_that_crawl(api: ApiOpener) -> None:
    broken = FakeSite({BASE: ["/a"], f"{BASE}a": []}, broken={f"{BASE}a"})
    sites = iter([broken, three_page_site()])
    async with api(lambda: next(sites)) as client:
        bad = await start(client)
        good = await start(client)
        assert (await finish(client, bad))["status"] == "failed"
        assert (await finish(client, good))["status"] == "completed"
        assert (await client.get("/health")).status_code == 200
