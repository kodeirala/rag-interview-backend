from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = Field(
        default=None,
        description="Client-supplied conversation id. A new one is created when omitted.",
    )


class RetrievedSource(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    score: float
    preview: str


class BookingStatus(BaseModel):
    state: Literal["idle", "collecting", "confirmed"]
    missing_fields: list[str] = Field(default_factory=list)
    booking_id: UUID | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    sources: list[RetrievedSource] = Field(default_factory=list)
    booking: BookingStatus
