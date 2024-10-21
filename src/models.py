from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NewsItem:
    title: str
    date: str
    url: str
    hash: Optional[str] = field(default=None, init=False)
    content: Optional[str] = field(default=None, init=False)


@dataclass
class ReleaseItem:
    title: str
    date: str
    url: str
    author: str
    system: Optional[str] = field(default=None, init=False)
    hash: Optional[str] = field(default=None, init=False)
