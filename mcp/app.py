# mcp/app.py
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from .db import get_db
from .schemas import ReviewCreate, ReviewResponse, FinalizeReview
from dotenv import load_dotenv
import os
from routes.review_routes import get_llm_service

# Import dummy data utilities
from .dummy_data import generate_dummy_review, validate_review_structure

# Load environment variables
load_dotenv()

app = FastAPI(title="HTTP Server for Review Processing")

# CORS setup
origins = [
    "https://expertiza.ncsu.edu",  # production
    "http://localhost:3000"        # local dev
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple API key security
API_KEY = os.getenv("API_KEY", "supersecret123")

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

# -----------------------------------------------------
# ✅ Generate and insert dummy review
# -----------------------------------------------------
@app.post("/v1/reviews/dummy", response_model=ReviewResponse)
def create_dummy_review(database: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """Generate dummy input, validate it, and insert into DB."""
    dummy_review = generate_dummy_review()

    # Validate structure
    if not validate_review_structure(dummy_review):
        raise HTTPException(status_code=400, detail="Invalid review structure")

    # Insert into table with 'processed' status
    database.execute(
        text("""
            INSERT INTO reviews_table (response_id_of_expertiza, review, status)
            VALUES (:response_id_of_expertiza, :review, 'processed')
        """),
        {
            "response_id_of_expertiza": dummy_review["response_id_of_expertiza"],
            "review": dummy_review["review"]
        },
    )
    database.commit()

    # Fetch last inserted row (SQLite-safe alternative to RETURNING)
    row = database.execute(text("SELECT * FROM reviews_table ORDER BY id DESC LIMIT 1")).mappings().one()

    return {
        "id": row["id"],
        "llm_generated_feedback": row["llm_generated_feedback"],
        "llm_generated_score": row["llm_generated_score"],
        "llm_details_reasoning": row["llm_details_reasoning"],
        "finalized_feedback": row["finalized_feedback"],
        "finalized_score": row["finalized_score"],
        "status": row["status"],
    }

# -----------------------------------------------------
# 🧱 Existing Endpoints
# -----------------------------------------------------

@app.post("/v1/reviews", response_model=ReviewResponse)
def create_review(review: ReviewCreate, database: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    database.execute(
        text("""
            INSERT INTO reviews_table (response_id_of_expertiza, review, status)
            VALUES (:response_id_of_expertiza, :review, 'received')
        """),
        {"response_id_of_expertiza": review.response_id_of_expertiza, "review": review.review},
    )
    database.commit()

    row = database.execute(text("SELECT * FROM reviews_table ORDER BY id DESC LIMIT 1")).mappings().one()

    return {
        "id": row["id"],
        "llm_generated_feedback": row["llm_generated_feedback"],
        "llm_generated_score": row["llm_generated_score"],
        "llm_details_reasoning": row["llm_details_reasoning"],
        "finalized_feedback": row["finalized_feedback"],
        "finalized_score": row["finalized_score"],
        "status": row["status"],
    }

@app.get("/v1/reviews/{id}", response_model=ReviewResponse)
def get_review(id: int, database: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
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
def finalize_review(id: int, data: FinalizeReview, database: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    current = database.execute(text("SELECT * FROM reviews_table WHERE id = :id"), {"id": id}).mappings().first()
    if not current:
        raise HTTPException(status_code=404, detail="Review not found")

    finalized_score = data.finalized_score if data.finalized_score is not None else current["llm_generated_score"]
    finalized_feedback = data.finalized_feedback if data.finalized_feedback is not None else current["llm_generated_feedback"]

    database.execute(
        text("""
            UPDATE reviews_table
               SET finalized_score    = :fs,
                   finalized_feedback = :ff,
                   status             = 'finalized',
                   updated_at         = CURRENT_TIMESTAMP
             WHERE id = :id
        """),
        {"fs": finalized_score, "ff": finalized_feedback, "id": id},
    )
    database.commit()

    updated = database.execute(text("SELECT * FROM reviews_table WHERE id = :id"), {"id": id}).mappings().one()

    return {
        "id": updated["id"],
        "llm_generated_feedback": updated["llm_generated_feedback"],
        "llm_generated_score": updated["llm_generated_score"],
        "llm_details_reasoning": updated["llm_details_reasoning"],
        "finalized_feedback": updated["finalized_feedback"],
        "finalized_score": updated["finalized_score"],
        "status": updated["status"],
    }

# -----------------------------------------------------
# Temporary Test Endpoint
# -----------------------------------------------------
@app.post("/v1/test-dummy")
def test_dummy(database: Session = Depends(get_db)):
    dummy = generate_dummy_review()

    if not validate_review_structure(dummy):
        return {"error": "Invalid structure", "data": dummy}

    database.execute(
        text("""
            INSERT INTO reviews_table (response_id_of_expertiza, review, status)
            VALUES (:response_id, :review, 'processed')
        """),
        {"response_id": dummy["response_id_of_expertiza"], "review": dummy["review"]}
    )
    database.commit()

    row = database.execute(text("SELECT * FROM reviews_table ORDER BY id DESC LIMIT 1")).mappings().one()
    return {"message": "Inserted dummy review successfully", "data": row}


@app.on_event("shutdown")
async def close_llm_service():
    svc = get_llm_service()
    await svc.close()