import re
from typing import Any
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import PIICipher
from app.db.models import InterviewBooking
from app.schemas.booking import BookingExtraction
from app.schemas.chat import BookingStatus
from app.services.memory import ChatMemory

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")
REQUIRED_FIELDS = ("name", "email", "interview_date", "interview_time")


class BookingService:
    def __init__(self, session: AsyncSession, memory: ChatMemory, cipher: PIICipher) -> None:
        self._session = session
        self._memory = memory
        self._cipher = cipher

    async def apply_extraction(
        self,
        session_id: str,
        extraction: BookingExtraction,
    ) -> tuple[dict[str, Any], BookingStatus]:
        state = await self._memory.get_booking_state(session_id)

        if extraction.intent == "cancel_booking":
            await self._memory.clear_booking_state(session_id)
            empty = {"name": None, "email": None, "interview_date": None, "interview_time": None}
            return empty, BookingStatus(state="idle", missing_fields=list(REQUIRED_FIELDS))

        if extraction.intent != "book_interview" and not any(state.values()):
            return state, BookingStatus(state="idle", missing_fields=[])

        merged = {
            "name": _clean(extraction.name) or state.get("name"),
            "email": _normalize_email(extraction.email) or state.get("email"),
            "interview_date": _normalize_date(extraction.interview_date) or state.get("interview_date"),
            "interview_time": _normalize_time(extraction.interview_time) or state.get("interview_time"),
        }
        await self._memory.save_booking_state(session_id, merged)
        missing = [field for field in REQUIRED_FIELDS if not merged.get(field)]

        if missing:
            return merged, BookingStatus(state="collecting", missing_fields=missing)

        booking_id = await self._persist(session_id, merged)
        await self._memory.clear_booking_state(session_id)
        return merged, BookingStatus(state="confirmed", missing_fields=[], booking_id=booking_id)

    async def _persist(self, session_id: str, state: dict[str, Any]) -> UUID:
        booking = InterviewBooking(
            session_id=session_id,
            name_encrypted=self._cipher.encrypt(str(state["name"])),
            email_encrypted=self._cipher.encrypt(str(state["email"])),
            interview_date=str(state["interview_date"]),
            interview_time=str(state["interview_time"]),
        )
        self._session.add(booking)
        await self._session.commit()
        await self._session.refresh(booking)
        return booking.id


def _clean(value: str | None) -> str | None:
    if not value:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_email(value: str | None) -> str | None:
    cleaned = _clean(value)
    if not cleaned:
        return None
    try:
        return validate_email(cleaned, check_deliverability=False).normalized
    except EmailNotValidError:
        return None


def _normalize_date(value: str | None) -> str | None:
    cleaned = _clean(value)
    if cleaned and DATE_RE.match(cleaned):
        return cleaned
    return None


def _normalize_time(value: str | None) -> str | None:
    cleaned = _clean(value)
    if cleaned and TIME_RE.match(cleaned):
        hour, minute = cleaned.split(":")
        if 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59:
            return cleaned
    return None
