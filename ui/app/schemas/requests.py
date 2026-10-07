from pydantic import BaseModel, Field, field_validator

from shared.models.requests import DnsRequestItem

_MAX_VALUE_KEYS = 10
_MAX_VALUE_FIELD_LEN = 4096


class RequestItemIn(BaseModel):
    action: str = Field(pattern="^(CREATE|MODIFY|DELETE)$")
    record_type: str = Field(max_length=20)
    fqdn: str = Field(max_length=255)
    ttl: int | None = Field(default=None, ge=0, le=2_147_483_647)
    value: dict = Field(default_factory=dict)
    # For MODIFY/DELETE: the Micetro record ref the user selected from the
    # live-fetched list — re-fetched live again at creation time, never
    # trusted from the browser, to guarantee no stale/discrepant data is used.
    source_record_ref: str | None = Field(default=None, max_length=255)

    @field_validator("value")
    @classmethod
    def _bound_value_shape(cls, v: dict) -> dict:
        # Defense in depth ahead of the per-record-type validators and the
        # overall request body-size middleware — rejects absurdly large/odd
        # payloads as early as possible, cheaply.
        if len(v) > _MAX_VALUE_KEYS:
            raise ValueError(f"value has too many fields (max {_MAX_VALUE_KEYS})")
        for key, val in v.items():
            if len(str(key)) > 50:
                raise ValueError("value field name too long")
            if len(str(val)) > _MAX_VALUE_FIELD_LEN:
                raise ValueError(f"value field '{key}' exceeds {_MAX_VALUE_FIELD_LEN} characters")
        return v


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
    justification: str | None = Field(default=None, max_length=2000)
    items: list[RequestItemIn] = Field(min_length=1, max_length=50)


class RequestOut(BaseModel):
    id: int
    zone_id: int
    status: str
    justification: str | None
    items: list[RequestItemOut]
