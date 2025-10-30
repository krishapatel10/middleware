# services/orchestrator.py
import asyncio
import httpx
import logging
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import Optional, Callable
from db.session import SessionLocal
from mcp.services.llm_service import LLMService   

logger = logging.getLogger(__name__)

async def generate_llm_review(review_text: str, temperature: float = 0.0, max_attempts: int = 10):
    llm = LLMService()
    result = await llm.evaluate_and_parse(review_text=review_text, temperature=temperature, max_attempts=max_attempts)
    return result


async def process_review_and_update(
    review_id: int,
    review_text: str,
    temperature: float = 0.0,
    max_attempts: Optional[int] = None,
    db_session_factory: Callable[[], Session] = SessionLocal,
):
    """
    Background orchestration task:
    - Calls the LLM service
    - Waits for LLM output
    - Updates the review row in DB with generated feedback, score, reasoning
    """

    db = db_session_factory()
    try:
        logger.info(f"Starting LLM processing for review id={review_id}")

        async with httpx.AsyncClient() as client:
            response = await generate_llm_review(
                review_text=review_text,
                temperature=temperature,
                max_attempts=max_attempts or 10)
        if response.status_code != 200:
            logger.error(f"LLM API failed for id={review_id}: {response.status_code} - {response.text}")
            raise Exception(f"LLM API call failed with {response.status_code}")

        data = response.json()

        # Update DB with LLM results
        db.execute(
            text("""
                UPDATE reviews_table
                   SET llm_generated_feedback = :feedback,
                       llm_generated_score = :score,
                       llm_details_reasoning = :reasoning,
                       status = 'processed',
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = :id
            """),
            {
                "feedback": data.get("llm_generated_feedback") or data.get("feedback") or "",
                "score": data.get("llm_generated_score") or data.get("score"),
                "reasoning": data.get("llm_details_reasoning") or data.get("reasoning") or "",
                "id": review_id,
            },
        )
        db.commit()
        logger.info(f"Review {review_id} processed successfully and updated in DB.")

    except Exception as e:
        logger.exception(f"Failed to process review id={review_id}: {e}")
        # Mark as failed for debugging / retries
        db.execute(
            text("""
                UPDATE reviews_table
                   SET status = 'failed',
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = :id
            """),
            {"id": review_id},
        )
        db.commit()

    finally:
        db.close()
