import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def website():
    compose_filepath = Path(__file__).parent.joinpath("docker-compose.yaml")

    subprocess.run(
        ["docker", "compose", "-f", str(compose_filepath), "up", "-d"],
        check=True,
    )

    yield "http://localhost:8888"

    subprocess.run(
        ["docker", "compose", "-f", str(compose_filepath), "down"],
        check=True,
    )
