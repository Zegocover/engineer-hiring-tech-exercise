"""Run configuration read once from the ``CRAWLER_*`` environment."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, PositiveFloat, PositiveInt, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

UserAgent = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class Config(BaseSettings):
    """Immutable run configuration; ``workers`` also caps the connection pool."""

    model_config = SettingsConfigDict(env_prefix="CRAWLER_", frozen=True, populate_by_name=True)

    workers: PositiveInt = 10
    timeout: PositiveFloat = Field(default=5.0, validation_alias="CRAWLER_TIMEOUT_SECONDS")
    user_agent: UserAgent = "zego-crawler/0.1"
