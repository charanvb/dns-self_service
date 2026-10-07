from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    user_id: int
    username: str
    display_name: str
    roles: list[str]
