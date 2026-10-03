from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    # bcrypt obsługuje max 72 bajty
    password: str = Field(min_length=8, max_length=64)
    name: str | None = Field(default=None, max_length=100)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str | None
    created_at: datetime
