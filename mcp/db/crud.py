# db/crud.py
from typing import Any, Dict, Optional, Union
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import DBAPIError

ResponseId = Union[int, str]

async def get_review_by_response_id(database: AsyncSession, response_id: ResponseId) -> Optional[Dict[str, Any]]:
    """
    Return the first review that matches response_id_of_expertiza or None.
    """
    result = await database.execute(
        text("SELECT * FROM reviews_table WHERE response_id_of_expertiza = :rid LIMIT 1"),
        {"rid": response_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def insert_review_received(
    database: AsyncSession,
    response_id_of_expertiza: ResponseId,
    review_text: str,
    status: str = "pending",   # <<-- changed from "received" to "pending"
    idempotent: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Insert a review row and return the inserted row as a dict.
    If idempotent=True, will return an existing row for the same response_id_of_expertiza instead of inserting a duplicate.
    Note: for true atomic idempotency, add a UNIQUE constraint on response_id_of_expertiza and use the upsert SQL below.
    """
    if idempotent:
        existing = await get_review_by_response_id(database, response_id_of_expertiza)
        if existing:
            return existing

    insert_sql = text(
        """
        INSERT INTO reviews_table (response_id_of_expertiza, review, status, created_at, updated_at)
        VALUES (:response_id_of_expertiza, :review, :status, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING *
        """
    )
    try:
        result = await database.execute(
            insert_sql,
            {"response_id_of_expertiza": response_id_of_expertiza, "review": review_text, "status": status},
        )
        await database.commit()
        row = result.mappings().first()
        return dict(row) if row else None
    except DBAPIError as exc:
        # You can customize logging here; re-raise or return None
        # For debugging: raise a clearer exception or log exc.orig
        raise


async def get_review_by_id(database: AsyncSession, review_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a review row by id. Returns a dict or None if not found.
    """
    result = await database.execute(text("SELECT * FROM reviews_table WHERE id = :id"), {"id": review_id})
    row = result.mappings().first()
    return dict(row) if row else None


async def finalize_review_by_id(
    database: AsyncSession,
    review_id: int,
    finalized_score: Optional[float],
    finalized_feedback: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Update finalized fields and mark the review as 'finalized'.
    If finalized_score or finalized_feedback is None, existing LLM-generated values are preserved.
    Returns the updated row dict or None if the id does not exist.
    """
    # fetch current row
    current = await get_review_by_id(database, review_id)
    if not current:
        return None

    fs = finalized_score if finalized_score is not None else current.get("llm_generated_score")
    ff = finalized_feedback if finalized_feedback is not None else current.get("llm_generated_feedback")

    await database.execute(
        text(
            """
            UPDATE reviews_table
               SET finalized_score    = :fs,
                   finalized_feedback = :ff,
                   status             = 'finalized',
                   updated_at         = CURRENT_TIMESTAMP
             WHERE id = :id
            """
        ),
        {"fs": fs, "ff": ff, "id": review_id},
    )
    await database.commit()

    result = await database.execute(text("SELECT * FROM reviews_table WHERE id = :id"), {"id": review_id})
    updated = result.mappings().first()
    return dict(updated) if updated else None


# --- Optional: atomic upsert version (use after adding UNIQUE constraint on response_id_of_expertiza)
# async def insert_review_received_upsert(...):
#     upsert_sql = text(
#         """
#         INSERT INTO reviews_table (response_id_of_expertiza, review, status, created_at, updated_at)
#         VALUES (:response_id_of_expertiza, :review, :status, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
#         ON CONFLICT (response_id_of_expertiza)
#         DO UPDATE SET updated_at = EXCLUDED.updated_at
#         RETURNING *
#         """
#     )
#     result = await database.execute(upsert_sql, {...})
#     await database.commit()
#     return dict(result.mappings().first()) if result else None
