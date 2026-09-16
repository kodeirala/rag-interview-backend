from uuid import uuid4

from app.core.config import Settings
from app.schemas.chat import BookingStatus, ChatResponse, RetrievedSource
from app.services.booking import BookingService
from app.services.embeddings import EmbeddingClient
from app.services.llm import LLMClient
from app.services.memory import ChatMemory
from app.services.vectorstore import VectorStore


class RAGService:
    """Custom retrieval-augmented generation with Redis memory (no RetrievalQAChain)."""

    def __init__(
        self,
        memory: ChatMemory,
        embeddings: EmbeddingClient,
        vectors: VectorStore,
        llm: LLMClient,
        booking: BookingService,
        settings: Settings,
    ) -> None:
        self._memory = memory
        self._embeddings = embeddings
        self._vectors = vectors
        self._llm = llm
        self._booking = booking
        self._settings = settings

    async def chat(self, message: str, session_id: str | None) -> ChatResponse:
        sid = session_id or str(uuid4())
        history = await self._memory.get_messages(sid)

        booking_state = await self._memory.get_booking_state(sid)
        extraction = await self._llm.extract_booking(message, history, booking_state)
        merged_state, booking_status = await self._booking.apply_extraction(sid, extraction)

        sources: list[RetrievedSource] = []
        if booking_status.state in {"collecting", "confirmed"}:
            reply = extraction.assistant_message or (
                "I can book that interview. Still needed: "
                + ", ".join(booking_status.missing_fields)
            )
            if booking_status.state == "confirmed":
                reply = (
                    "Your interview is booked. "
                    f"Date: {merged_state['interview_date']} at {merged_state['interview_time']}. "
                    f"Confirmation id: {booking_status.booking_id}."
                )
        else:
            search_query = await self._llm.rewrite_query(message, history)
            query_vectors = await self._embeddings.embed([search_query])
            hits = await self._vectors.search(query_vectors[0], self._settings.retrieval_top_k)
            context_blocks: list[str] = []
            for hit in hits:
                payload = hit.payload or {}
                text = str(payload.get("text", ""))
                context_blocks.append(
                    f"Source: {payload.get('filename')} chunk {payload.get('chunk_index')}\n{text}"
                )
                sources.append(
                    RetrievedSource(
                        document_id=str(payload.get("document_id", "")),
                        filename=str(payload.get("filename", "")),
                        chunk_index=int(payload.get("chunk_index", 0)),
                        score=float(hit.score or 0.0),
                        preview=text[:280],
                    )
                )
            reply = await self._llm.answer_with_context(message, history, context_blocks)

        await self._memory.append_messages(
            sid,
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply},
            ],
        )
        return ChatResponse(session_id=sid, reply=reply, sources=sources, booking=booking_status)
