# mcp/services/orchestrator.py
import json
import logging
import traceback
from typing import Optional, Any, Dict
from pydantic import BaseModel

from sqlalchemy import text
from mcp.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

async def generate_llm_review(review_text: str, temperature: float = 0.0, max_attempts: int = 10) -> Any:
    """
    Dynamically import LLMService at call time to avoid circular imports.
    Returns whatever evaluate_and_parse returns (pydantic model or dict).
    """
    from mcp.services.llm_service import LLMService

    llm = LLMService()
    result = await llm.evaluate_and_parse(review_text=review_text, temperature=temperature, max_attempts=max_attempts)
    return result


async def process_review_and_update(review_id: int, review_text: str):
    """
    Worker coroutine: calls LLM via generate_llm_review, normalizes output,
    and writes llm_generated_feedback, llm_generated_score (evaluation JSON), 
    llm_details_reasoning, llm_generated_output (full output), and status.
    """
    try:
        llm_out = await generate_llm_review(review_text)  
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
    
    # Extract evaluation object (all scores) and JSON-serialize it
    evaluation_obj = llm_dict.get("evaluation")
    try:
        evaluation_json = json.dumps(evaluation_obj) if evaluation_obj is not None else None
    except (TypeError, ValueError):
        evaluation_json = json.dumps(str(evaluation_obj))

    # Extract reasoning/details and JSON-serialize for storage text column
    details_obj = llm_dict.get("reasoning") or llm_dict.get("reasoning_summary") or None
    try:
        details_json = json.dumps(details_obj) if details_obj is not None else None
    except (TypeError, ValueError):
        details_json = json.dumps(str(details_obj))

    # Serialize the full LLM output to JSON
    try:
        full_output_json = json.dumps(llm_dict) if llm_dict else None
    except (TypeError, ValueError):
        full_output_json = json.dumps(str(llm_dict))

    update_sql = text(
        """
        UPDATE reviews_table
           SET llm_generated_feedback = :feedback,
               llm_generated_score = :evaluation,
               llm_details_reasoning = :details,
               llm_generated_output = :full_output,
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
                    "evaluation": evaluation_json,
                    "details": details_json,
                    "full_output": full_output_json,
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
