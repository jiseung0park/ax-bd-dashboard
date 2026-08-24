"""RawDocument — the common shape every collector normalizes into, regardless
of source (API vs HTML crawl). Keeping this one small schema is what lets the
matcher/extractor stages stay collector-agnostic (기능 1의 핵심)."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional
import hashlib


@dataclass
class RawDocument:
    source: str            # e.g. "충남도청", "나라장터-사전규격"
    title: str
    body: str
    published_at: Optional[str]   # "YYYY-MM-DD", None if unknown
    url: str
    collected_at: str = ""

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    @property
    def doc_id(self) -> str:
        """Stable id from source+url so re-collecting the same posting is a no-op, not a duplicate."""
        return hashlib.sha1(f"{self.source}|{self.url}".encode("utf-8")).hexdigest()[:16]

    def to_dict(self):
        d = asdict(self)
        d["doc_id"] = self.doc_id
        return d
