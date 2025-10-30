# routes/reviews.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.session import get_db
from db import crud
router = APIRouter()

@router.get("/v1/reviews/{id}")
def get_review(id: int, database: Session = Depends(get_db)):
    row = crud.get_review_by_id(database, id)
    if not row:
        raise HTTPException(status_code=404, detail="Review not found")
    return row
