from fastapi import APIRouter, Depends

from app.api.deps import get_rag_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag import RAGService

router = APIRouter(prefix="/chat", tags=["rag"])


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: RAGService = Depends(get_rag_service),
) -> ChatResponse:
    return await service.chat(payload.message, payload.session_id)
