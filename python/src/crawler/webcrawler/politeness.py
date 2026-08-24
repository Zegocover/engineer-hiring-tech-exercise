"""Host politeness through robots.txt access rules."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.robotparser import RobotFileParser


@dataclass(frozen=True, slots=True)
class Politeness:
    """Applies a host's robots access policy (None allows all)."""

    rules: RobotFileParser | None
    user_agent: str

    @classmethod
    def from_robots(cls, text: str | None, user_agent: str) -> Politeness:
        """Parse ``robots.txt`` text (``None`` = missing/unreadable = allow all) into a policy."""
        if text is None:
            return cls(None, user_agent)
        rules = RobotFileParser()
        rules.parse(text.splitlines())
        return cls(rules, user_agent)

    def allowed(self, url: str) -> bool:
        """Whether this user-agent may fetch ``url`` (allow-all when robots is absent)."""
        if self.rules is None:
            return True
        return self.rules.can_fetch(self.user_agent, url)
