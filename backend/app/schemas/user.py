from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    # bcrypt obsługuje max 72 bajty
    password: str = Field(min_length=8, max_length=64)
    name: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        # max_length liczy znaki, a bcrypt bajty – polskie litery mają po 2 bajty w UTF-8
        if len(v.encode()) > 72:
            raise ValueError("Password too long (max 72 bytes)")
        return v


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str | None
    created_at: datetime
