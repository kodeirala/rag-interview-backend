from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ChunkingStrategy = Literal["fixed_size", "sentence_window"]


class IngestResponse(BaseModel):
    document_id: UUID
    filename: str
    chunking_strategy: ChunkingStrategy
    chunk_count: int
    created_at: datetime


class DocumentSummary(BaseModel):
    id: UUID
    filename: str
    chunking_strategy: str
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
