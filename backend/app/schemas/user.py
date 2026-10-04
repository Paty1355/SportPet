from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class HealthProfileFields(BaseModel):
    sex: Literal["F", "M"] | None = None
    birth_date: date | None = None
    weight_kg: float | None = Field(default=None, ge=20, le=400)
    height_cm: float | None = Field(default=None, ge=80, le=250)


class UserCreate(HealthProfileFields):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    name: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        if len(v.encode()) > 72:
            raise ValueError("Password too long (max 72 bytes)")
        return v


class UserUpdate(HealthProfileFields):
    name: str | None = Field(default=None, max_length=100)
    post_workout_reporting_frequency: Literal["daily", "weekly", "monthly"] | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("post_workout_reporting_frequency", "timezone")
    @classmethod
    def preferences_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("preferences cannot be null")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str | None
    created_at: datetime
    sex: Literal["F", "M"] | None
    birth_date: date | None
    weight_kg: float | None
    height_cm: float | None
    post_workout_reporting_frequency: Literal["daily", "weekly", "monthly"]
    timezone: str
    share_pet: bool
