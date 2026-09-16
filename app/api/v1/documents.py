from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_ingest_service
from app.schemas.ingest import ChunkingStrategy, DocumentSummary, IngestResponse
from app.services.ingest import IngestService

router = APIRouter(prefix="/documents", tags=["ingestion"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(..., description="PDF or TXT file"),
    chunking_strategy: ChunkingStrategy = Form(
        "fixed_size",
        description="fixed_size (character windows) or sentence_window (sliding sentences)",
    ),
    service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    return await service.ingest(file, chunking_strategy)


@router.get("", response_model=list[DocumentSummary])
async def list_documents(
    service: IngestService = Depends(get_ingest_service),
) -> list[DocumentSummary]:
    return await service.list_documents()
