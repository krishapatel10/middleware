# mcp/schemas.py
from pydantic import BaseModel
from typing import Optional

# Request model: when Expertiza sends a new review
class ReviewCreate(BaseModel):
    response_id_of_expertiza: int
    review: str

# Response model: when returning data from DB
class ReviewResponse(BaseModel):
    id: int
    llm_generated_feedback: Optional[str] = None
    llm_generated_score: Optional[float] = None
    llm_details_reasoning: Optional[str] = None
    finalized_feedback: Optional[str] = None
    finalized_score: Optional[float] = None
    status: str

    class Config:
        from_attributes = True  # Fix for Pydantic v2 (replaces orm_mode)

# Model for accepting instructor’s edits
class FinalizeReview(BaseModel):
    finalized_feedback: Optional[str] = None
    finalized_score: Optional[float] = None

