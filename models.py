from typing import Optional, List, Union
from dataclasses import dataclass, field


@dataclass
class Song:
    id: int
    name: str
    url: str
    artist: Optional['Artist']

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name: '{self.name}', id: {self.id})"


@dataclass
class Artist:
    name: str
    url: str
    songs: List[Song] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(\"{self.name}\")"
