# routes/review_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import logging
from mcp.services.llm_service import LLMService 
from mcp.schemas import ReviewRequest
logger = logging.getLogger(__name__)
router = APIRouter()


_llm_service_instance: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    """Return a single shared LLMService instance."""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()  # internally creates an LLMClient
    return _llm_service_instance


@router.post("/llmreview", status_code=200)
async def llmservice_endpoint(request: ReviewRequest, svc: LLMService = Depends(get_llm_service)):
    """
    POST /llmreview
    Calls svc.evaluate_and_parse(review_text=...) and returns validated JSON.
    """
    try:
        validated = await svc.evaluate_and_parse(
            review_text=request.review_text,
            temperature=request.temperature or 0.0,
            max_attempts=request.max_attempts or 10,
        )

        # Handle both Pydantic v1/v2 output
        if hasattr(validated, "model_dump"):
            return validated.model_dump()
        if hasattr(validated, "dict"):
            return validated.dict()
        return validated

    except Exception as exc:
        msg = str(exc)
        logger.exception("LLM evaluate_and_parse failed: %s", msg)
        if "ValidationError" in msg or "Could not obtain valid LLM JSON" in msg:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=msg)


