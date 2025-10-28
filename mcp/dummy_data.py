# mcp/dummy_data.py
import random

# ✅ Function 1: generate a dummy review JSON (mimics Expertiza input)
def generate_dummy_review():
    return {
        "response_id_of_expertiza": random.randint(1000, 9999),
        "review": "The student provided clear arguments, though the analysis could be deeper."
    }

# ✅ Function 2: validate the review JSON structure before DB insert
def validate_review_structure(data: dict) -> bool:
    """
    Validates that the data has the expected structure and types:
      - response_id_of_expertiza: int
      - review: str
    """
    if not isinstance(data, dict):
        return False
    if "response_id_of_expertiza" not in data or "review" not in data:
        return False
    if not isinstance(data["response_id_of_expertiza"], int):
        return False
    if not isinstance(data["review"], str):
        return False
    return True

