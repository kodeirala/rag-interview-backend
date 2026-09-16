from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.exceptions import LLMNotConfiguredError


class EmbeddingClient:
    def __init__(self, client: AsyncOpenAI, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._settings.openai_api_key:
            raise LLMNotConfiguredError()

        vectors: list[list[float]] = []
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self._client.embeddings.create(
                model=self._settings.embedding_model,
                input=batch,
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend(item.embedding for item in ordered)
        return vectors
