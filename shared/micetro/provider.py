from shared.dns_provider.base import DNSProvider, RecordDTO, ZoneDTO
from shared.micetro.client import MicetroClient

# Micetro pseudo-"record types" that aren't actual DNS records (comments, zone
# file directives) — never surfaced as DNSRecord rows in our inventory.
_NON_RECORD_TYPES = {"Comment", "EmptyLine", "$GENERATE", "$INCLUDE", "$TTL"}


class MicetroProvider(DNSProvider):
    def __init__(self, client: MicetroClient | None = None):
        self.client = client or MicetroClient()

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

    def search_records(self, zone_ref: str, offset: int, limit: int) -> tuple[list[RecordDTO], int]:
        body = self.client.get(f"/dnsZones/{zone_ref}/dnsRecords", params={"offset": offset, "limit": limit})
        records = [
            RecordDTO(
                ref=r["ref"],
                zone_ref=zone_ref,
                name=r["name"],
                record_type=r["type"],
                ttl=r.get("ttl", ""),
                data=r.get("data", ""),
            )
            for r in body.get("dnsRecords", [])
            if r["type"] not in _NON_RECORD_TYPES
        ]
        return records, body["totalResults"]

    def get_record(self, record_ref: str) -> RecordDTO:
        body = self.client.get(f"/dnsRecords/{record_ref}")
        r = body["dnsRecord"]
        return RecordDTO(
            ref=r["ref"],
            zone_ref=r.get("dnsZoneRef", ""),
            name=r["name"],
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
