"""Encodes our structured per-record-type value dicts (see shared/validation/
record_types/*.py) into Micetro's DNSRecord.data wire format.

Confirmed from swagger: `data` is just `{type: string, description: "Contains
the record data in a tab-separated list"}` — no further schema detail. The
exact per-type layout below is inferred from standard DNS zone-file RDATA
ordering and from observing that already-synced TXT/SPF data reads back as
raw unquoted text (e.g. "v=spf1 ..." with no surrounding quotes, confirmed by
the working SPF-duplicate check in ui/app/routes/requests.py). This has NOT
been empirically verified against a live Micetro CREATE/MODIFY call — verify
with a real write (e.g. in the QA tenant) before trusting this in production,
especially MX's exact tab layout. See /memories/repo/micetro-api.md item C.
"""


def encode(record_type: str, value: dict) -> str:
    if record_type == "A":
        return value["ipv4"]
    if record_type == "AAAA":
        return value["ipv6"]
    if record_type == "CNAME":
        return value["target"]
    if record_type == "TXT":
        return value["text"]
    raise ValueError(f"No data encoder for record type: {record_type}")
