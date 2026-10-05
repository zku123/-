from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Group:
    platform: str  # "telegram" | "vk"
    ext_id: str  # id на платформе
    title: str
    url: str
    description: str = ""
    members: Optional[int] = None
    last_activity: Optional[datetime] = None
    country: Optional[str] = None  # определяется по тексту
    found_by: set[str] = field(default_factory=set)  # поисковые запросы
    score: float = 0.0

    @property
    def key(self) -> tuple[str, str]:
        return (self.platform, self.ext_id)

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.description}"
