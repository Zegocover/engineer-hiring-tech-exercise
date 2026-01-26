"""Application entrypoint wiring the crawler components together."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from crawler import config, robots
from crawler.fetcher import Fetcher
from crawler.renderers import JsonRenderer, Renderer, TextRenderer
from crawler.scheduler import Scheduler
from crawler.worker import worker_loop


def _build_renderer(cfg: config.CrawlerConfig) -> Renderer:
    path = Path(cfg.output_file)
    if cfg.output_format == config.OUTPUT_JSON:
        return JsonRenderer(path)
    return TextRenderer(path)


async def run_async(cfg: config.CrawlerConfig) -> None:
    """Run the crawler until cancelled."""
    scheduler = Scheduler(max_pages_crawled=cfg.profile.max_pages_crawled)
    renderer = _build_renderer(cfg)

    policy = None
    if cfg.robots == config.ROBOTS_RESPECT:
        policy = robots.fetch_robots_policy(
            cfg.base_url,
            user_agent=cfg.user_agent,
            timeout_s=cfg.profile.timeout_seconds,
        )
        if not policy.is_allowed(cfg.base_url):
            logging.info("robots.txt disallows the base URL, exiting.")
            renderer.close()
            return

    async with Fetcher(
        user_agent=cfg.user_agent,
        timeout_s=cfg.profile.timeout_seconds,
    ) as fetcher:
        scheduler_task = asyncio.create_task(
            scheduler.run(
                cfg.base_url,
                cfg.profile.max_depth,
                robots_policy=policy,
            )
        )
        worker_tasks = []
        for idx in range(cfg.profile.concurrency):
            worker_tasks.append(
                asyncio.create_task(
                    worker_loop(
                        name=f"worker-{idx + 1}",
                        scheduler=scheduler,
                        fetcher=fetcher,
                        renderer=renderer,
                        cfg=cfg,
                    )
                )
            )

        try:
            await scheduler.wait_for_shutdown()
            await scheduler_task
            await asyncio.gather(*worker_tasks, return_exceptions=True)
        finally:
            if not scheduler_task.done():
                scheduler_task.cancel()
                await asyncio.gather(scheduler_task, return_exceptions=True)
            for task in worker_tasks:
                if not task.done():
                    task.cancel()
            if worker_tasks:
                await asyncio.gather(*worker_tasks, return_exceptions=True)
            renderer.close()


def run(cfg: config.CrawlerConfig) -> int:
    """Synchronously run the crawler and handle cancellation."""
    try:
        asyncio.run(run_async(cfg))
        return 0
    except KeyboardInterrupt:
        logging.info("🛑 Crawl interrupted by user.")
        return 0
