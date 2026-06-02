"""Ports (Protocols) the engine depends on — the two genuine external-system
boundaries. Implementations live in gateways. Defined here so dependencies
point inward."""

from typing import Protocol, runtime_checkable

from domains.crawler.models import FetchResult


@runtime_checkable
class Fetcher(Protocol):
    """Fetch one URL over the network. Implemented by a gateway (httpx)."""

    async def fetch(self, url: str) -> FetchResult: ...


@runtime_checkable
class Queue[T](Protocol):
    """Minimal generic message queue. In-memory now; broker (Kafka/SQS) later."""

    async def put(self, item: T) -> None: ...
    async def get(self) -> T: ...
