# app/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Union, Any

# Accept ints, floats, strings, or None for scores
RubricKey = Optional[Union[int, float, str]]

class ReviewCreate(BaseModel):
    response_id_of_expertiza: int
    review: str

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

    # normalize common LLM tokens -> None or numeric
    @validator("score", pre=True)
    def _normalize_score(cls, v: Any):
        if v is None:
            return None
        if isinstance(v, str):
            txt = v.strip()
            if txt.upper() in ("N/A", "NA", ""):
                return None
            # try to coerce numeric string to int/float
            try:
                if "." in txt:
                    return float(txt)
                return int(txt)
            except Exception:
                return txt  # leave as string if not numeric
        if isinstance(v, (int, float)):
            return v
        return v

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
