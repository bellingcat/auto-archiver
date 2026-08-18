from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from typing import Any

from auto_archiver.core import Metadata
from auto_archiver.version import __version__


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PlatformStatus:
    """Serializable status record for a platform/url trial."""

    id: str
    run_datetime: str
    aa_version: str
    platform_name: str
    archive_url: str
    content_type: str
    is_content_accessible: bool = False
    is_content_archived: bool = False
    current_metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_metadata(
        cls,
        metadata: Metadata,
        platform_name: str,
        archive_url: str,
        content_type: str,
    ) -> PlatformStatus:
        ts = _utcnow_iso()
        return cls(
            id=f"{ts}_{platform_name}_{content_type}",
            run_datetime=ts,
            aa_version=__version__,
            platform_name=platform_name,
            archive_url=archive_url,
            content_type=content_type,
            current_metadata=dict(metadata.metadata),
        )

    def content_accessible(self, accessible: bool) -> None:
        self.is_content_accessible = accessible

    def content_archived(self, archived: bool) -> None:
        self.is_content_archived = archived

    def to_record(self) -> dict[str, Any]:
        """Returns a plain dictionary ready for JSON serialization."""
        return asdict(self)

    def to_json(self, *, indent: int | None = None) -> str:
        """Returns a JSON string representation of this status record."""
        return json.dumps(self.to_record(), ensure_ascii=False, indent=indent, default=str)
