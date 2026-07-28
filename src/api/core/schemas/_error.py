from pydantic import BaseModel, Field


class HTTPErrorPM(BaseModel):
    code: str = Field(..., min_length=3, max_length=36)
    name: str = Field(..., min_length=3, max_length=64)
    status_code: int = Field(..., ge=100, le=599)
    message: str = Field(..., min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=1024)


__all__ = [
    "HTTPErrorPM",
]
