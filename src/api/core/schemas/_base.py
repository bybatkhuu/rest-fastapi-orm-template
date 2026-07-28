from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict, AwareDatetime
from pydantic.types import StringConstraints


class BasePM(BaseModel):
    model_config = ConfigDict(validate_default=True)


class ExtraBasePM(BasePM):
    model_config = ConfigDict(
        extra="allow", json_schema_extra={"additionalProperties": False}
    )


class IdPM(BasePM):
    id: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(
        ...,
        min_length=8,
        max_length=64,
        title="ID",
        description="Identifier value of the resource.",
        examples=["res1701388800_dc2cc6c9033c4837b6c34c8bb19bb289"],
    )


class TimestampPM(BasePM):
    updated_at: AwareDatetime = Field(
        ...,
        title="Updated datetime",
        description="Last updated datetime of the resource.",
        examples=["2026-01-01T00:00:00+00:00"],
    )
    created_at: AwareDatetime = Field(
        ...,
        title="Created datetime",
        description="Created datetime of the resource.",
        examples=["2026-01-01T00:00:00+00:00"],
    )


__all__ = [
    "BasePM",
    "ExtraBasePM",
    "IdPM",
    "TimestampPM",
]
