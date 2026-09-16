from uuid import UUID, uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import Settings
from app.services.chunking import TextChunk


class VectorStore:
    def __init__(self, client: AsyncQdrantClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def ensure_collection(self) -> None:
        collections = await self._client.get_collections()
        names = {collection.name for collection in collections.collections}
        if self._settings.qdrant_collection in names:
            return
        await self._client.create_collection(
            collection_name=self._settings.qdrant_collection,
            vectors_config=qmodels.VectorParams(
                size=self._settings.embedding_dimension,
                distance=qmodels.Distance.COSINE,
            ),
        )

    async def upsert_chunks(
        self,
        document_id: UUID,
        filename: str,
        strategy: str,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> list[str]:
        if len(chunks) != len(embeddings):
            raise ValueError("Chunk and embedding counts must match")

        points: list[qmodels.PointStruct] = []
        point_ids: list[str] = []
        for chunk, vector in zip(chunks, embeddings, strict=True):
            point_id = str(uuid4())
            point_ids.append(point_id)
            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document_id": str(document_id),
                        "filename": filename,
                        "chunk_index": chunk.index,
                        "chunking_strategy": strategy,
                        "text": chunk.text,
                    },
                )
            )

        await self._client.upsert(
            collection_name=self._settings.qdrant_collection,
            points=points,
        )
        return point_ids

    async def search(self, query_vector: list[float], top_k: int | None = None) -> list[qmodels.ScoredPoint]:
        limit = top_k or self._settings.retrieval_top_k
        results = await self._client.query_points(
            collection_name=self._settings.qdrant_collection,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )
        return results.points
