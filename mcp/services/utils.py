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
    parts = []

    if payload.assignment:
        parts.append(f"Assignment: {payload.assignment}")

    parts.append(f"Response ID: {payload.response_id_of_expertiza}")

    if payload.overall_comments:
        parts.append("Overall comments:")
        parts.append(payload.overall_comments)

    if payload.scores:
        parts.append("Scores:")
        for i, s in enumerate(payload.scores, start=1):
            # include question, numeric answer and optional comment
            q = s.question or f"question_{i}"
            parts.append(f" - {q}: {s.answer}")
            if s.comment:
                parts.append(f"   comment: {s.comment}")

    if payload.additional_comments:
        parts.append("Additional comments:")
        parts.append(payload.additional_comments)

    # join with double newlines to make the input readable to LLM
    return "\n\n".join(parts)


def _normalize(value: any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        up = s.upper()
        if up in {"N/A", "NA", "NONE", "NULL", ""}:
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