from pydantic import BaseModel, Field


class ApprovalListItemOut(BaseModel):
    approval_request_id: int
    request_id: int
    zone_id: int
    zone_name: str
    requestor: str
    justification: str | None
    created_at: str


class ApprovalActionIn(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)
