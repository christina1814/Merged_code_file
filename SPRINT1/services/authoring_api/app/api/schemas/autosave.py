from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional


class AutosaveRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10_000_000)
    
    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class AutosaveResponse(BaseModel):
    doc_id: UUID
    new_version: int = Field(..., ge=1)
    status: str = Field(..., pattern="^(saved|unchanged)$")
    last_updated: datetime
    trace_id: Optional[str] = None


class AutosaveErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class AutosaveErrorResponse(BaseModel):
    error: AutosaveErrorDetail
    trace_id: Optional[str] = None