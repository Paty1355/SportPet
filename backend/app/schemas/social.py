from pydantic import BaseModel, ConfigDict

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

class FriendshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    requester_id: int
    addressee_id: int
    status: str

class FriendRequestsOut(BaseModel):
    incoming: list[FriendshipOut]
    outgoing: list[FriendshipOut]

class FriendPetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    level: int
    hat: str | None = None
    body: str | None = None
    background: str | None = None
    decor: list | None = None
    theme: str | None = None

class UserSearchOut(BaseModel):
    id: int
    name: str | None