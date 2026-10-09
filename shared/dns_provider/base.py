from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ZoneDTO:
    ref: str
    name: str
    zone_type: str


@dataclass
class RecordDTO:
    ref: str
    zone_ref: str
    name: str
    record_type: str
    ttl: str
    data: str


class DNSProvider(ABC):
    """Generic DNS provider interface — business logic (policy engine, request
    workflow, executor) must only depend on this, never on a specific provider
    like Micetro, so swapping to GCP Cloud DNS later doesn't touch business logic."""

    @abstractmethod
    def get_zones(self, offset: int, limit: int) -> tuple[list[ZoneDTO], int]:
        """Returns (zones, total_count)."""

    @abstractmethod
    def get_zone(self, zone_ref: str) -> ZoneDTO:
        ...

    @abstractmethod
    def search_records(self, zone_ref: str, offset: int, limit: int) -> tuple[list[RecordDTO], int]:
        """Returns (records, total_count) for the given zone, unfiltered page."""

    @abstractmethod
    def find_records_by_name(
        self,
        zone_ref: str,
        fqdn: str,
        record_type: str | None = None,
        zone_name: str | None = None,
    ) -> list[RecordDTO]:
        """Targeted lookup for records matching an FQDN and optional record_type."""

    @abstractmethod
    def get_record(self, record_ref: str) -> RecordDTO:
        """Fresh lookup by ref — used by the Executor for pre-execution conflict checks."""

    @abstractmethod
    def create_record(self, zone_ref: str, record: RecordDTO) -> str:
        """Returns the new record's ref. Implemented in Phase 8."""

    @abstractmethod
    def modify_record(self, record_ref: str, properties: dict) -> None:
        """Implemented in Phase 8."""

    @abstractmethod
    def delete_record(self, record_ref: str) -> None:
        """Implemented in Phase 8."""
