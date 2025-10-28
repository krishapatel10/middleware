"""
Prompt builder for review evaluation.
This version STRICTLY asks the LLM to return ONLY JSON — in the exact schema provided.
"""

from typing import Dict

SCHEMA_EXAMPLE = {
    "reasoning": {
        "Praise": "string",
        "Problems & Solutions": "string",
        "Tone": "string",
        "Localization": "string",
        "Helpfulness": "string",
        "Explanation": "string",
        "Acted On": "string",
        "Relevance": "string",
        "Consistency": "string",
        "Actionability": "string",
        "Factuality": "string",
        "Accessibility": "string",
        "Comprehensiveness": "string"
    },
    "evaluation": {
        "Praise": {"score": "int", "justification": "string"},
        "Problems & Solutions": {"score": "int", "justification": "string"},
        "Tone": {"score": "int", "justification": "string"},
        "Localization": {"score": "int", "justification": "string"},
        "Helpfulness": {"score": "int", "justification": "string"},
        "Explanation": {"score": "int", "justification": "string"},
        "Acted On": {"score": "int or N/A", "justification": "string"},
        "Relevance": {"score": "int", "justification": "string"},
        "Consistency": {"score": "int", "justification": "string"},
        "Actionability": {"score": "int", "justification": "string"},
        "Factuality": {"score": "int", "justification": "string"},
        "Accessibility": {"score": "int", "justification": "string"},
        "Comprehensiveness": {"score": "int", "justification": "string"}
    },
    "feedback": "string"
}


SYSTEM_PROMPT = (
    "You are an expert reviewer. Read the given review carefully and evaluate it according to the following schema.\n\n"
    "Your response MUST be a VALID JSON object that strictly follows this format:\n\n"
    "{\n"
    '  "reasoning": {\n'
    '    "Praise": "string",\n'
    '    "Problems & Solutions": "string",\n'
    '    "Tone": "string",\n'
    '    "Localization": "string",\n'
    '    "Helpfulness": "string",\n'
    '    "Explanation": "string",\n'
    '    "Acted On": "string",\n'
    '    "Relevance": "string",\n'
    '    "Consistency": "string",\n'
    '    "Actionability": "string",\n'
    '    "Factuality": "string",\n'
    '    "Accessibility": "string",\n'
    '    "Comprehensiveness": "string"\n'
    "  },\n"
    '  "evaluation": {\n'
    '    "Praise": {"score": int, "justification": "string"},\n'
    '    "Problems & Solutions": {"score": int, "justification": "string"},\n'
    '    "Tone": {"score": int, "justification": "string"},\n'
    '    "Localization": {"score": int, "justification": "string"},\n'
    '    "Helpfulness": {"score": int, "justification": "string"},\n'
    '    "Explanation": {"score": int, "justification": "string"},\n'
    '    "Acted On": {"score": "int or N/A", "justification": "string"},\n'
    '    "Relevance": {"score": int, "justification": "string"},\n'
    '    "Consistency": {"score": int, "justification": "string"},\n'
    '    "Actionability": {"score": int, "justification": "string"},\n'
    '    "Factuality": {"score": int, "justification": "string"},\n'
    '    "Accessibility": {"score": int, "justification": "string"},\n'
    '    "Comprehensiveness": {"score": int, "justification": "string"}\n'
    "  },\n"
    '  "feedback": "string"\n'
    "}\n\n"
    " STRICT RULES:\n"
    "- Return ONLY valid JSON. No markdown, no explanations, no text before or after.\n"
    "- Do not include ```json fences.\n"
    "- Use double quotes for all keys and string values.\n"
    "- If a rubric is not applicable, set its score to \"N/A\".\n"
    "- Do not summarize outside this JSON structure."
)


def build_review_prompt(review_text: str) -> str:
    """
    Build the full prompt to send to the LLM for review evaluation.
    This prompt explicitly demands JSON in the exact schema above.
    """
    return f"{SYSTEM_PROMPT}\n\nReview to evaluate:\n{review_text.strip()}\n"


def build_chat_messages(review_text: str) -> list[Dict[str, str]]:
    """
    Build chat-style messages for APIs expecting 'messages' format (e.g., OpenAI, Gemini chat endpoints).
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Review to evaluate:\n{review_text.strip()}"}
    ]
