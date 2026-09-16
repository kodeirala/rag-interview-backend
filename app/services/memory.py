import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import Settings

Message = dict[str, str]


class ChatMemory:
    """Redis-backed sliding conversation history for multi-turn RAG."""

    def __init__(self, redis: Redis, settings: Settings) -> None:
        self._redis = redis
        self._ttl = settings.chat_memory_ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"chat:{session_id}"

    def _booking_key(self, session_id: str) -> str:
        return f"booking:{session_id}"

    async def get_messages(self, session_id: str) -> list[Message]:
        raw = await self._redis.get(self._key(session_id))
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []

    async def append_messages(self, session_id: str, messages: list[Message]) -> list[Message]:
        history = await self.get_messages(session_id)
        history.extend(messages)
        history = history[-40:]
        await self._redis.set(
            self._key(session_id),
            json.dumps(history),
            ex=self._ttl,
        )
        return history

    async def get_booking_state(self, session_id: str) -> dict[str, Any]:
        raw = await self._redis.get(self._booking_key(session_id))
        if not raw:
            return {"name": None, "email": None, "interview_date": None, "interview_time": None}
        return json.loads(raw)

    async def save_booking_state(self, session_id: str, state: dict[str, Any]) -> None:
        await self._redis.set(
            self._booking_key(session_id),
            json.dumps(state),
            ex=self._ttl,
        )

    async def clear_booking_state(self, session_id: str) -> None:
        await self._redis.delete(self._booking_key(session_id))
