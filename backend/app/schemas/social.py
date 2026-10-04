from pydantic import BaseModel

class FriendRequestCreate(BaseModel):
    user_id: int

class PrivacyUpdate(BaseModel):
    share_pet: bool

class PetUpdate(BaseModel):
    name: str | None = None
    level: int | None = None
    hat: str | None = None
    body: str | None = None
    background: str | None = None
    decor: list | None = None
    theme: str | None = None

class UserSearchOut(BaseModel):
    id: int
    name: str | None