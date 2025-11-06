# app/routes/reviews.py
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from mcp.schemas import ReviewPayload, ReviewResponse, FinalizeReview
from mcp.db.session import AsyncSessionLocal
from mcp.db.crud import insert_review_received, get_review_by_id, finalize_review_by_id
from mcp.services.utils import schedule_process_review  
from mcp.core.auth import verify_jwt  
from mcp.services.utils import build_review_text

router = APIRouter(prefix="/reviews", tags=["reviews"])

# DB dependency (kept trivial)
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: ReviewPayload,
    background_tasks: BackgroundTasks,
    user=Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    # Basic validation
    if not payload.response_id_of_expertiza:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Missing response_id_of_expertiza")

    if not (payload.overall_comments or payload.scores or payload.additional_comments):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Review content cannot be empty")

    # Convert structured payload into single LLM-facing text
    review_text = build_review_text(payload)

    # Insert (idempotency handled inside insert helper)
    inserted = await insert_review_received(db, payload.response_id_of_expertiza, review_text)
    if not inserted:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to insert review")

    # schedule background LLM work — pass review_text (not payload.review)
    background_tasks.add_task(schedule_process_review, inserted["id"], review_text)

    return ReviewResponse(**inserted)



@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: int, user=Depends(verify_jwt), db: AsyncSession = Depends(get_db)):
    rec = await get_review_by_id(db, review_id)
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")
    return ReviewResponse(**rec)


@router.post("/{review_id}/accept", response_model=ReviewResponse)
async def accept_review(review_id: int, payload: FinalizeReview, user=Depends(verify_jwt), db: AsyncSession = Depends(get_db)):
    updated = await finalize_review_by_id(db, review_id, payload.finalized_score, payload.finalized_feedback)
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")
    return ReviewResponse(**updated)


@router.post("/{review_id}/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_llm_job(
    review_id: int,
    background_tasks: BackgroundTasks,
    user=Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger background LLM processing for an existing review.
    Useful for reprocessing or admin testing.
    """
    review = await get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Review not found")

    # Schedule background LLM job (uses same helper as /POST /v1/reviews)
    background_tasks.add_task(schedule_process_review, review_id, review["review"])

    return {
        "message": f"Triggered LLM processing for review {review_id}",
        "status": "scheduled",
        "review_id": review_id,
    }
