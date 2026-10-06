from pydantic import BaseModel, Field

from shared.models.requests import DnsRequestItem


class RequestItemIn(BaseModel):
    action: str = Field(pattern="^(CREATE|MODIFY|DELETE)$")
    record_type: str
    fqdn: str
    ttl: int | None = None
    value: dict = Field(default_factory=dict)
    # For MODIFY/DELETE: the Micetro record ref the user selected from the
    # live-fetched list — re-fetched live again at creation time, never
    # trusted from the browser, to guarantee no stale/discrepant data is used.
    source_record_ref: str | None = None


class RequestItemOut(BaseModel):
    id: int
    action: str
    record_type: str
    fqdn: str
    ttl: int | None
    status: str
    error_message: str | None

    @classmethod
    def from_model(cls, item: DnsRequestItem) -> "RequestItemOut":
        return cls(
            id=item.id,
            action=item.action,
            record_type=item.record_type,
            fqdn=item.fqdn,
            ttl=item.ttl,
            status=item.status,
            error_message=item.error_message,
        )


class CreateRequestIn(BaseModel):
    zone_id: int
    justification: str | None = None
    items: list[RequestItemIn] = Field(min_length=1, max_length=50)


class RequestOut(BaseModel):
    id: int
    zone_id: int
    status: str
    justification: str | None
    items: list[RequestItemOut]
