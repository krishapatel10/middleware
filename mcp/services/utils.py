from typing import Optional, Any
import asyncio
from typing import Any
from mcp.services.orchestrator import process_review_and_update
from mcp.schemas import ReviewPayload

async def schedule_process_review(review_id: int, review_text: str) -> None:
    """
    Async helper that schedules the worker on the running event loop.
    Make this async so FastAPI's BackgroundTasks will await/schedule it on the server loop.
    """
    # get_running_loop should succeed when called by FastAPI in async context
    loop = asyncio.get_running_loop()
    # debug print (optional)
    print("schedule_process_review loop id:", id(loop))
    # schedule the real worker coroutine without awaiting it
    loop.create_task(process_review_and_update(review_id, review_text))

def build_review_text(payload: ReviewPayload) -> str:
    parts: list[str] = []

    # Course / assignment metadata
    if payload.course_name:
        parts.append(f"Course Name: {payload.course_name}")

    if payload.assignment_name:
        parts.append(f"Assignment Name: {payload.assignment_name}")

    parts.append(f"Response ID (Expertiza): {payload.response_id_of_expertiza}")
    parts.append(f"Round no: {payload.round}")

    # Scores block
    if payload.scores:
        parts.append("Scores:")
        for i, s in enumerate(payload.scores, start=1):
            question = s.question or f"Question {i}"

            parts.append(
                f" - {question} "
                f"(type={s.type}, max_points={s.max_points}, awarded_points={s.awarded_points})"
            )

            if s.comments:
                parts.append(f"   comments: {s.comments}")

    # Additional overall comment
    if payload.additional_comment:
        parts.append("Additional comments:")
        parts.append(payload.additional_comment)

    if payload.previous_round_review:
        parts.append("Previous round review:")
        parts.append(payload.previous_round_review)

    # Join with double newlines to keep things readable for the LLM
    return "\n\n".join(parts)


def _normalize(value: any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        up = s.upper()
        # Preserve "N/A" as string for "Acted On" scores (don't convert to None)
        # Only convert empty strings and explicit null-like values to None
        if up in {"NONE", "NULL", ""}:
            return None
        # numeric-like string -> number
        if s.replace(".", "", 1).lstrip("-").isdigit():
            return float(s) if "." in s else int(s)
        return s
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(x) for x in value]
    return value