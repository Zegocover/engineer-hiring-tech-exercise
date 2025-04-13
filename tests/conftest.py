import subprocess
from http.client import HTTPResponse
from pathlib import Path
from time import sleep
from urllib.request import urlopen

import pytest


@pytest.fixture(scope="session")
def website():
    compose_filepath = Path(__file__).parent.joinpath("docker-compose.yaml")

    subprocess.run(
        ["docker", "compose", "-f", str(compose_filepath), "up", "-d"],
        check=True,
    )

    server_url = "http://localhost:8888"

    yield server_url

    subprocess.run(
        ["docker", "compose", "-f", str(compose_filepath), "down"],
        check=True,
    )


@pytest.fixture
def html():
    class HtmlFetcher:
        @staticmethod
        def get(path: Path):
            file_path = (
                Path(__file__).parent.joinpath(Path("html_fixtures")).joinpath(path)
            )

            with open(file_path) as file:
                return file.read()

    return HtmlFetcher()
