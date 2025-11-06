# mcp/services/orchestrator.py
import json
import logging
import traceback
from typing import Optional, Any, Dict
from pydantic import BaseModel

from sqlalchemy import text
from mcp.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

# You already have this helper; keep it as the LLM entrypoint
async def generate_llm_review(review_text: str, temperature: float = 0.0, max_attempts: int = 10) -> Any:
    """
    Dynamically import LLMService at call time to avoid circular imports.
    Returns whatever evaluate_and_parse returns (pydantic model or dict).
    """
    # local import avoids circular import at module import time
    from mcp.services.llm_service import LLMService

    llm = LLMService()
    result = await llm.evaluate_and_parse(review_text=review_text, temperature=temperature, max_attempts=max_attempts)
    return result


async def process_review_and_update(review_id: int, review_text: str):
    """
    Worker coroutine: calls LLM via generate_llm_review, normalizes output,
    and writes only llm_generated_feedback, llm_generated_score, llm_details_reasoning, status.
    (No writes to llm_generated_output.)
    """
    try:
        llm_out = await generate_llm_review(review_text)  # returns pydantic model or dict
    except Exception as exc:
        traceback.print_exc()
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text(
                        """
                        UPDATE reviews_table
                           SET status = :status,
                               llm_details_reasoning = :err,
                               updated_at = CURRENT_TIMESTAMP
                         WHERE id = :id
                        """
                    ),
                    {"status": "failed", "err": str(exc), "id": review_id},
                )
                await db.commit()
        except Exception:
            traceback.print_exc()
        return

    # Normalize to plain dict
    if isinstance(llm_out, BaseModel):
        try:
            llm_dict = llm_out.model_dump()
        except Exception:
            llm_dict = llm_out.dict()
    elif isinstance(llm_out, dict):
        llm_dict = llm_out
    else:
        llm_dict = {"feedback": str(llm_out)}

    # Extract fields
    feedback = llm_dict.get("feedback")
    score = llm_dict.get("score")

    # Extract reasoning/details and JSON-serialize for storage text column
    details_obj = llm_dict.get("reasoning") or llm_dict.get("reasoning_summary") or None
    try:
        details_json = json.dumps(details_obj) if details_obj is not None else None
    except (TypeError, ValueError):
        details_json = json.dumps(str(details_obj))

    update_sql = text(
        """
        UPDATE reviews_table
           SET llm_generated_feedback = :feedback,
               llm_generated_score = :score,
               llm_details_reasoning = :details,
               status = :status,
               updated_at = CURRENT_TIMESTAMP
         WHERE id = :id
        """
    )

    async with AsyncSessionLocal() as db:
        try:
            await db.execute(
                update_sql,
                {
                    "feedback": feedback,
                    "score": score,
                    "details": details_json,
                    "status": "processed",
                    "id": review_id,
                },
            )
            await db.commit()
            print(f"Processed review id={review_id}")
            return
        except Exception as exc:
            try:
                await db.rollback()
            except Exception:
                pass
            traceback.print_exc()
            try:
                await db.execute(
                    text(
                        """
                        UPDATE reviews_table
                           SET status = :status,
                               llm_details_reasoning = :err,
                               updated_at = CURRENT_TIMESTAMP
                         WHERE id = :id
                        """
                    ),
                    {"status": "failed", "err": str(exc), "id": review_id},
                )
                await db.commit()
                print(f"Marked review {review_id} as failed")
            except Exception:
                try:
                    await db.rollback()
                except Exception:
                    pass
                traceback.print_exc()
                print(f"Failed to mark review {review_id} as failed (see stack traces above)")
