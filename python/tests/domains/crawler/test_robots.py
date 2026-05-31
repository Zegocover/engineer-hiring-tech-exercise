from domains.crawler.ports import RobotsPolicy
from domains.crawler.robots import NoOpRobotsPolicy


async def test_noop_allows_everything() -> None:
    policy = NoOpRobotsPolicy()
    assert await policy.allowed("http://a.com/anything") is True
    assert await policy.allowed("http://a.com/private") is True


def test_noop_satisfies_the_port() -> None:
    assert isinstance(NoOpRobotsPolicy(), RobotsPolicy)
