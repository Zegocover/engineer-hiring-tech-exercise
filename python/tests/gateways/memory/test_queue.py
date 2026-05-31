from domains.crawler.ports import Queue
from gateways.memory.queue import InMemoryQueue


def test_satisfies_the_port() -> None:
    assert isinstance(InMemoryQueue(), Queue)


async def test_put_then_get_roundtrips_fifo() -> None:
    q: InMemoryQueue[str] = InMemoryQueue()
    await q.put("first")
    await q.put("second")
    assert await q.get() == "first"
    assert await q.get() == "second"
