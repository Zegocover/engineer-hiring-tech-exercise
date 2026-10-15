"""Driving crawls through the HTTP API in tests."""

import asyncio
from collections.abc import Callable
from typing import Any

import httpx

BASE = "https://example.com/"


async def start(client: httpx.AsyncClient, url: str = BASE, **limits: Any) -> str:
    response = await client.post("/crawls", json={"url": url, **limits})
    assert response.status_code == 202, response.text
    job_id: str = response.json()["id"]
    return job_id


async def poll(
    client: httpx.AsyncClient, job_id: str, until: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    async with asyncio.timeout(5):
        while True:
            body: dict[str, Any] = (await client.get(f"/crawls/{job_id}/status")).json()
            if until(body):
                return body
            await asyncio.sleep(0)


async def finish(client: httpx.AsyncClient, job_id: str) -> dict[str, Any]:
    return await poll(client, job_id, lambda body: body["status"] != "running")
