# db/models.py
from sqlalchemy import Column, Integer, Text, Float, Enum, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from mcp.db.session import Base

class ReviewStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    processed = "processed"
    failed = "failed"
    finalized = "finalized"

class Review(Base):
    __tablename__ = "reviews_table"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    response_id_of_expertiza = Column(Integer, nullable=False, index=True, unique=True) 

    review = Column(Text, nullable=False)

    llm_generated_feedback = Column(Text, nullable=True)
    llm_generated_score = Column(Text, nullable=True)  
    llm_details_reasoning = Column(Text, nullable=True)
    llm_generated_output = Column(Text, nullable=True) 

    finalized_feedback = Column(Text, nullable=True)
    finalized_score = Column(Float, nullable=True)

    status = Column(Enum(ReviewStatus, name="review_status"), nullable=False, default=ReviewStatus.pending)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("response_id_of_expertiza", name="uq_response_id_of_expertiza"), 
    )

class FailedJob(Base):
    __tablename__ = "failed_jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reviews_id_from_review_table = Column(Integer, ForeignKey("reviews_table.id", ondelete="CASCADE"), nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    review = relationship("Review", backref="failed_jobs")
