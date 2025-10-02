# mcp/app.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from .db import get_db
from .schemas import ReviewCreate, ReviewResponse, FinalizeReview
from .llm_mock import evaluate_review

app = FastAPI(title="MCP Server")

@app.post("/v1/reviews", response_model=ReviewResponse)
def create_review(review: ReviewCreate, database: Session = Depends(get_db)):
    # Insert initial row (received)
    result = database.execute(
        text("""
            INSERT INTO reviews_table (response_id_of_expertiza, review, status)
            VALUES (:response_id_of_expertiza, :review, 'received')
            RETURNING *;
        """),
        {"response_id_of_expertiza": review.response_id_of_expertiza, "review": review.review},
    )
    row = result.mappings().one()

    # Mock LLM
    feedback, score, reasoning = evaluate_review(review.review)

    # Update with LLM-generated fields
    result = database.execute(
        text("""
            UPDATE reviews_table
               SET llm_generated_feedback = :feedback,
                   llm_generated_score    = :score,
                   llm_details_reasoning  = :reasoning,
                   status                 = 'evaluated',
                   updated_at             = now()
             WHERE id = :id
         RETURNING *;
        """),
        {"feedback": feedback, "score": score, "reasoning": reasoning, "id": row["id"]},
    )
    updated = result.mappings().one()
    database.commit()

    return {
        "id": updated["id"],
        "llm_generated_feedback": updated["llm_generated_feedback"],
        "llm_generated_score": updated["llm_generated_score"],
        "llm_details_reasoning": updated["llm_details_reasoning"],
        "finalized_feedback": updated["finalized_feedback"],
        "finalized_score": updated["finalized_score"],
        "status": updated["status"],
    }

@app.get("/v1/reviews/{id}", response_model=ReviewResponse)
def get_review(id: int, database: Session = Depends(get_db)):
    result = database.execute(text("SELECT * FROM reviews_table WHERE id = :id"), {"id": id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Review not found")
    return {
        "id": row["id"],
        "llm_generated_feedback": row["llm_generated_feedback"],
        "llm_generated_score": row["llm_generated_score"],
        "llm_details_reasoning": row["llm_details_reasoning"],
        "finalized_feedback": row["finalized_feedback"],
        "finalized_score": row["finalized_score"],
        "status": row["status"],
    }

@app.post("/v1/reviews/{id}/accept", response_model=ReviewResponse)
def finalize_review(id: int, data: FinalizeReview, database: Session = Depends(get_db)):
    current = database.execute(text("SELECT * FROM reviews_table WHERE id = :id"), {"id": id}).mappings().first()
    if not current:
        raise HTTPException(status_code=404, detail="Review not found")

    finalized_score = data.finalized_score if data.finalized_score is not None else current["llm_generated_score"]
    finalized_feedback = data.finalized_feedback if data.finalized_feedback is not None else current["llm_generated_feedback"]

    result = database.execute(
        text("""
            UPDATE reviews_table
               SET finalized_score    = :fs,
                   finalized_feedback = :ff,
                   status             = 'finalized',
                   updated_at         = now()
             WHERE id = :id
         RETURNING *;
        """),
        {"fs": finalized_score, "ff": finalized_feedback, "id": id},
    )
    updated = result.mappings().one()
    database.commit()

    return {
        "id": updated["id"],
        "llm_generated_feedback": updated["llm_generated_feedback"],
        "llm_generated_score": updated["llm_generated_score"],
        "llm_details_reasoning": updated["llm_details_reasoning"],
        "finalized_feedback": updated["finalized_feedback"],
        "finalized_score": updated["finalized_score"],
        "status": updated["status"],
    }
