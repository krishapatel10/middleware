from pydantic import BaseModel
from typing import Optional

class ReviewCreate(BaseModel):
    response_id_of_expertiza: int
    review: str

class ReviewResponse(BaseModel):
    id: int
    llm_generated_feedback: Optional[str]
    llm_generated_score: Optional[float]
    llm_details_reasoning: Optional[str]
    finalized_feedback: Optional[str]
    finalized_score: Optional[float]
    status: str

    class Config:
        orm_mode = True

class FinalizeReview(BaseModel):
    finalized_feedback: Optional[str]
    finalized_score: Optional[float]
