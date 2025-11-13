# app/schemas.py
from pydantic import BaseModel, Field, conint
from typing import Optional, Union, List

# Accept ints, floats, strings, or None for scores
RubricKey = Optional[Union[int, float, str]]

class ScoreItem(BaseModel):
    question: str = Field(..., description="Question identifier or label")
    type: str = Field(..., description="Type of the question, e.g., 'Criterion'")
    max_points: Union[int, float, str] = Field(..., description="Numeric or textual score answer")
    awarded_points: Union[int, float, str, None] = Field(..., description="Points awarded for the question") #it can be null to indicate no score given
    comments: Optional[str] = Field(None, description="Optional comment for the question")

class ReviewPayload(BaseModel):
    assignment_name: Optional[str] = Field(None, description="Name of the assignment")
    course_name: Optional[str] = Field(None, description="Name of the course")
    response_id_of_expertiza: Union[int, str] = Field(..., description="ID of the expertiza response being reviewed")
    scores: Optional[List[ScoreItem]] = Field(None, description="List of scores with questions and comments")
    additional_comment: Optional[str] = Field(None, description="Additional comments about the review")

class FinalizeReview(BaseModel):
    finalized_feedback: Optional[str]
    finalized_score: Optional[float]

class Reasoning(BaseModel):
    Praise: Optional[str] = None
    Problems_and_Solutions: Optional[str] = Field(None, alias="Problems & Solutions")
    Tone: Optional[str] = None
    Localization: Optional[str] = None
    Helpfulness: Optional[str] = None
    Explanation: Optional[str] = None
    Acted_On: Optional[str] = Field(None, alias="Acted On")
    Relevance: Optional[str] = None
    Consistency: Optional[str] = None
    Actionability: Optional[str] = None
    Factuality: Optional[str] = None
    Accessibility: Optional[str] = None
    Comprehensiveness: Optional[str] = None

    class Config:

        allow_population_by_field_name = True
        anystr_strip_whitespace = True

class RubricEvaluation(BaseModel):
    score: RubricKey
    justification: Optional[str] = None


class Evaluation(BaseModel):
    Praise: RubricEvaluation
    Problems_and_Solutions: RubricEvaluation = Field(..., alias="Problems & Solutions")
    Tone: RubricEvaluation
    Localization: RubricEvaluation
    Helpfulness: RubricEvaluation
    Explanation: RubricEvaluation
    Acted_On: RubricEvaluation = Field(..., alias="Acted On")
    Relevance: RubricEvaluation
    Consistency: RubricEvaluation
    Actionability: RubricEvaluation
    Factuality: RubricEvaluation
    Accessibility: RubricEvaluation
    Comprehensiveness: RubricEvaluation

    class Config:
        allow_population_by_field_name = True
        anystr_strip_whitespace = True

class ReviewLLMOutput(BaseModel):
    reasoning: Reasoning
    evaluation: Evaluation
    feedback: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        anystr_strip_whitespace = True

class ReviewResponse(BaseModel):
    id: int
    llm_generated_feedback: Optional[str] = None
    llm_generated_score: Optional[float] = None
    llm_details_reasoning: Optional[str] = None
    llm_generated_output: Optional[ReviewLLMOutput] = None
    finalized_feedback: Optional[str] = None
    finalized_score: Optional[float] = None
    status: str

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

class ReviewRequest(BaseModel):
    review_text: str = Field(..., description="Raw review text to evaluate")
    temperature: Optional[float] = Field(0.0, description="LLM temperature")
    max_attempts: Optional[int] = Field(None, description="Override max attempts (optional)")
