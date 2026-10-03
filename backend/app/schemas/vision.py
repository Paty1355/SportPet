from pydantic import BaseModel, ConfigDict, Field, field_validator


class MachineCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    machine_id: str
    name: str
    aliases: list[str]


class MachineUsage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    description: str
    primary_muscles: list[str]
    secondary_muscles: list[str]
    setup_steps: list[str]
    exercise_steps: list[str]
    tips: list[str]

    @field_validator("description")
    @classmethod
    def nonempty_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("description must not be blank")
        return value.strip()

    @field_validator("primary_muscles", "secondary_muscles", "setup_steps", "exercise_steps", "tips")
    @classmethod
    def nonempty_items(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("list items must not be blank")
        return [value.strip() for value in values]

    @field_validator("primary_muscles", "setup_steps", "exercise_steps")
    @classmethod
    def required_items(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("at least one item is required")
        return values


class MachineDocument(MachineUsage):
    machine_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)
    aliases: list[str]
    category: str = Field(min_length=1)
    sources: list[str] = Field(min_length=1)

    @field_validator("name", "category")
    @classmethod
    def nonempty_names(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("names and category must not be blank")
        return value.strip()

    @field_validator("aliases", "sources")
    @classmethod
    def nonempty_metadata(cls, values: list[str]) -> list[str]:
        return MachineUsage.nonempty_items(values)


class MachineIdentification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    machine_id: str | None
    machine_name: str


class VisionResponse(MachineUsage):
    machine_id: str
    machine_name: str
    category: str
    sources: list[str]
