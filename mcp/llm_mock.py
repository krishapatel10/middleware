import random

def evaluate_review(review_text: str):
    """
    Mock LLM evaluation - later you replace with actual LLM API call.
    """
    feedback = f"Auto-generated feedback for review: {review_text[:50]}..."
    score = round(random.uniform(60, 95), 2)
    reasoning = "This score was generated using a mock LLM function."
    return feedback, score, reasoning
