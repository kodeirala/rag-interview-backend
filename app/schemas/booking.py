from typing import Literal

from pydantic import BaseModel, Field


class BookingExtraction(BaseModel):
    """Structured fields the LLM fills while booking."""

    intent: Literal["book_interview", "cancel_booking", "none"] = "none"
    name: str | None = None
    email: str | None = None
    interview_date: str | None = Field(default=None, description="ISO date YYYY-MM-DD")
    interview_time: str | None = Field(default=None, description="24h time HH:MM")
    assistant_message: str = ""
    booking_complete: bool = False
