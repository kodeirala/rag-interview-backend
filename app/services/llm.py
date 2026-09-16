import json
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import LLMNotConfiguredError
from app.schemas.booking import BookingExtraction


class LLMClient:
    def __init__(self, client: AsyncOpenAI, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def _require_key(self) -> None:
        if not self._settings.openai_api_key:
            raise LLMNotConfiguredError()

    async def rewrite_query(self, question: str, history: list[dict[str, str]]) -> str:
        """Turn a follow-up into a standalone retrieval query."""
        self._require_key()
        if not history:
            return question

        transcript = "\n".join(f"{item['role']}: {item['content']}" for item in history[-8:])
        response = await self._client.chat.completions.create(
            model=self._settings.llm_model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Rewrite the latest user question as a standalone search query "
                        "using conversation context. Return only the query text."
                    ),
                },
                {
                    "role": "user",
                    "content": f"History:\n{transcript}\n\nLatest question:\n{question}",
                },
            ],
        )
        rewritten = (response.choices[0].message.content or "").strip()
        return rewritten or question

    async def answer_with_context(
        self,
        question: str,
        history: list[dict[str, str]],
        context_blocks: list[str],
    ) -> str:
        self._require_key()
        context = "\n\n".join(context_blocks) if context_blocks else "No retrieved documents."
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful interview-prep assistant. Answer using the retrieved "
                    "context when it is relevant. If the context is insufficient, say so. "
                    "You can also help users book an interview by collecting name, email, "
                    "date (YYYY-MM-DD), and time (HH:MM)."
                ),
            },
            {
                "role": "system",
                "content": f"Retrieved context:\n{context}",
            },
        ]
        messages.extend(history[-12:])
        messages.append({"role": "user", "content": question})

        response = await self._client.chat.completions.create(
            model=self._settings.llm_model,
            temperature=0.2,
            messages=messages,
        )
        return (response.choices[0].message.content or "").strip()

    async def extract_booking(
        self,
        question: str,
        history: list[dict[str, str]],
        current_state: dict[str, Any],
    ) -> BookingExtraction:
        self._require_key()
        prompt = (
            "Determine whether the user wants to book an interview. "
            "Merge newly mentioned fields with the current booking state. "
            "interview_date must be YYYY-MM-DD. interview_time must be 24-hour HH:MM. "
            "Set booking_complete true only when name, email, interview_date, and interview_time are all present. "
            "If collecting details, ask for the next missing field in assistant_message. "
            f"Current state: {json.dumps(current_state)}"
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": prompt},
            *history[-12:],
            {"role": "user", "content": question},
        ]
        response = await self._client.chat.completions.create(
            model=self._settings.llm_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=messages,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
            return BookingExtraction.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            return BookingExtraction(intent="none", assistant_message="")
