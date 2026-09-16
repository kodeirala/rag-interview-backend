from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import Settings
from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError
from app.db.models import Document, DocumentChunk
from app.schemas.ingest import ChunkingStrategy, DocumentSummary, IngestResponse
from app.services.chunking import chunk_text
from app.services.embeddings import EmbeddingClient
from app.services.extraction import extract_text, normalize_extension
from app.services.vectorstore import VectorStore


class IngestService:
    def __init__(
        self,
        session: AsyncSession,
        embeddings: EmbeddingClient,
        vectors: VectorStore,
        settings: Settings,
    ) -> None:
        self._session = session
        self._embeddings = embeddings
        self._vectors = vectors
        self._settings = settings

    async def ingest(self, upload: UploadFile, strategy: ChunkingStrategy) -> IngestResponse:
        filename = upload.filename or "upload"
        extension = normalize_extension(filename)
        if extension not in {".pdf", ".txt"}:
            raise UnsupportedFileTypeError()

        content = await upload.read()
        if len(content) > self._settings.max_upload_bytes:
            raise FileTooLargeError(self._settings.max_upload_bytes)

        text = extract_text(filename, content)
        chunks = chunk_text(text, strategy, self._settings)
        embeddings = await self._embeddings.embed([chunk.text for chunk in chunks])

        document = Document(
            filename=filename,
            content_type=upload.content_type or "application/octet-stream",
            chunking_strategy=strategy,
            chunk_count=len(chunks),
        )
        self._session.add(document)
        await self._session.flush()

        point_ids = await self._vectors.upsert_chunks(
            document_id=document.id,
            filename=filename,
            strategy=strategy,
            chunks=chunks,
            embeddings=embeddings,
        )

        for chunk, point_id in zip(chunks, point_ids, strict=True):
            preview = chunk.text[:280]
            self._session.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.index,
                    qdrant_point_id=point_id,
                    token_estimate=max(1, len(chunk.text) // 4),
                    preview=preview,
                )
            )

        await self._session.commit()
        await self._session.refresh(document)
        return IngestResponse(
            document_id=document.id,
            filename=document.filename,
            chunking_strategy=strategy,
            chunk_count=document.chunk_count,
            created_at=document.created_at,
        )

    async def list_documents(self) -> list[DocumentSummary]:
        result = await self._session.execute(select(Document).order_by(Document.created_at.desc()))
        return [DocumentSummary.model_validate(row) for row in result.scalars().all()]
