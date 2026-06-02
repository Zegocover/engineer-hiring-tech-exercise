"""Ports (Protocols) the engine depends on. Implementations live in gateways
or in the domain's own stages. Defined here so dependencies point inward."""

from typing import Protocol, runtime_checkable

from domains.crawler.models import FetchResult, ParseOutcome


@runtime_checkable
class Fetcher(Protocol):
    """Fetch one URL over the network. Implemented by a gateway (httpx)."""

    async def fetch(self, url: str) -> FetchResult: ...


@runtime_checkable
class Queue[T](Protocol):
    """Minimal generic message queue. In-memory now; broker (Kafka/SQS) later."""

    async def put(self, item: T) -> None: ...
    async def get(self) -> T: ...


@runtime_checkable
class RobotsPolicy(Protocol):
    """Decide whether a URL may be fetched. NoOp placeholder for now."""

    async def allowed(self, url: str) -> bool: ...


@runtime_checkable
class FetchStage(Protocol):
    """Stage 1: URL -> FetchResult (applies the robots gate, then fetches)."""

    async def fetch(self, url: str) -> FetchResult: ...


@runtime_checkable
class ParseStage(Protocol):
    """Stage 2: FetchResult -> ParseOutcome (extract, normalize, classify)."""

    async def parse(self, result: FetchResult) -> ParseOutcome: ...
