from shared.dns_provider.base import DNSProvider, RecordDTO, ZoneDTO
from shared.micetro.client import MicetroClient

# Micetro pseudo-"record types" that aren't actual DNS records (comments, zone
# file directives) — never surfaced as DNSRecord rows in our inventory.
_NON_RECORD_TYPES = {"Comment", "EmptyLine", "$GENERATE", "$INCLUDE", "$TTL"}


def _to_fqdn(record_name: str, zone_name: str) -> str:
    """Micetro's DNSRecord.name is RELATIVE to the zone (e.g. "txt" for
    txt.web1.com, confirmed via live API call) — NOT the full FQDN, even
    though the zone's own name IS fully qualified (e.g. "web1.com."). Every
    RecordDTO.name produced by this provider must be a full FQDN so no
    consumer (sync job, wizard, validators) ever has to know about this
    Micetro-specific quirk."""
    zone_clean = zone_name.rstrip(".")
    record_clean = (record_name or "").strip()
    if not record_clean or record_clean in ("@", zone_clean):
        return zone_name
    return f"{record_clean}.{zone_name}"


class MicetroProvider(DNSProvider):
    def __init__(self, client: MicetroClient | None = None):
        self.client = client or MicetroClient()
        self._zone_name_cache: dict[str, str] = {}

    def _zone_name(self, zone_ref: str) -> str:
        if zone_ref not in self._zone_name_cache:
            self._zone_name_cache[zone_ref] = self.get_zone(zone_ref).name
        return self._zone_name_cache[zone_ref]

    def get_zones(self, offset: int, limit: int) -> tuple[list[ZoneDTO], int]:
        body = self.client.get("/dnsZones", params={"offset": offset, "limit": limit})
        zones = [
            ZoneDTO(ref=z["ref"], name=z["name"], zone_type=z["type"]) for z in body.get("dnsZones", [])
        ]
        return zones, body["totalResults"]

    def get_zone(self, zone_ref: str) -> ZoneDTO:
        body = self.client.get(f"/dnsZones/{zone_ref}")
        z = body["dnsZone"]
        return ZoneDTO(ref=z["ref"], name=z["name"], zone_type=z["type"])

    def search_records(
        self, zone_ref: str, offset: int, limit: int, zone_name: str | None = None
    ) -> tuple[list[RecordDTO], int]:
        zone_name = zone_name or self._zone_name(zone_ref)
        body = self.client.get(f"/dnsZones/{zone_ref}/dnsRecords", params={"offset": offset, "limit": limit})
        records = [
            RecordDTO(
                ref=r["ref"],
                zone_ref=zone_ref,
                name=_to_fqdn(r["name"], zone_name),
                record_type=r["type"],
                ttl=r.get("ttl", ""),
                data=r.get("data", ""),
            )
            for r in body.get("dnsRecords", [])
            if r["type"] not in _NON_RECORD_TYPES
        ]
        return records, body["totalResults"]

    def list_all_records(
        self, zone_ref: str, page_size: int = 500, safety_cap: int = 20000, zone_name: str | None = None
    ) -> list[RecordDTO]:
        """Fetches every record in a zone directly from Micetro (no Postgres
        cache) — used by the request wizard, which must never act on stale
        inventory data. Deliberately slow for large zones; safety_cap guards
        against a pathological infinite loop, not a feature limit."""
        zone_name = zone_name or self._zone_name(zone_ref)
        records: list[RecordDTO] = []
        offset = 0
        total = None
        while total is None or offset < total:
            batch, total = self.search_records(zone_ref, offset=offset, limit=page_size, zone_name=zone_name)
            if not batch:
                break
            records.extend(batch)
            offset += len(batch)
            if offset >= safety_cap:
                break
        return records

    def get_record(self, record_ref: str, zone_name: str | None = None) -> RecordDTO:
        body = self.client.get(f"/dnsRecords/{record_ref}")
        r = body["dnsRecord"]
        zone_ref = r.get("dnsZoneRef", "")
        zone_name = zone_name or (self._zone_name(zone_ref) if zone_ref else r["name"])
        return RecordDTO(
            ref=r["ref"],
            zone_ref=zone_ref,
            name=_to_fqdn(r["name"], zone_name),
            record_type=r["type"],
            ttl=r.get("ttl", ""),
            data=r.get("data", ""),
        )

    def create_record(self, zone_ref: str, record: RecordDTO) -> str:
        raise NotImplementedError("Implemented in Phase 8 (Executor)")

    def modify_record(self, record_ref: str, properties: dict) -> None:
        raise NotImplementedError("Implemented in Phase 8 (Executor)")

    def delete_record(self, record_ref: str) -> None:
        raise NotImplementedError("Implemented in Phase 8 (Executor)")
