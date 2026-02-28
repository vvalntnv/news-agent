from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from domain.ai.protocols import Agent
from domain.ai.configuration import AIConfiguration


class AIFactory(Protocol):
    """Protocol that produces AI agents configured with ``AIConfiguration``."""

    def create_agent(self, config: AIConfiguration) -> Agent:
        """Create an ``Agent`` instance configured for ``config``."""
        ...
