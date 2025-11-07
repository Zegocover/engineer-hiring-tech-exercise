import argparse
import asyncio
import time
from parser import Parser


async def main(url: str, loop: asyncio.AbstractEventLoop):
    parser = Parser(url)
    start = time.time()
    await parser.process()
    end = time.time()
    print(f"Total time: {end - start}")
    loop.stop()

def get_url() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args()
    return args.url

if __name__ == "__main__":
    url = get_url()
    loop = asyncio.get_event_loop()
    loop.create_task(main(url.replace("www.", ""), loop))
    loop.run_forever()