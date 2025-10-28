# app/services/service.py
import asyncio
import json
import logging
from typing import Optional, Any

from pydantic import ValidationError

from mcp.services.llm_client import LLMClient
from mcp.services.prompt import build_review_prompt
from mcp.schemas import ReviewLLMOutput
import mcp.config as config

logger = logging.getLogger(__name__)

# How many times to retry a single evaluate call until we accept a parsed JSON
MAX_ATTEMPTS_PER_CALL = getattr(config, "MAX_REVIEW_ATTEMPTS", 10)


# --- Module-level helper: normalization ---
def _normalize(value: Any) -> Any:
    """
    Recursively normalize model output:
    - strip strings
    - treat "N/A", "NA", "NONE", "NULL", "" as None
    - coerce numeric strings (int/float) to numbers
    - recurse into dicts/lists
    """
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


class LLMService:
    """
    High-level service that connects to the LLM (via LLMClient),
    asks for a strict JSON evaluation (using prompt.py), and returns
    validated ReviewLLMOutput objects.
    """

    def __init__(self, client: Optional[LLMClient] = None):
        # allow injection of a custom client for testing; otherwise create one
        self.client = client or LLMClient()
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        """Close underlying HTTP client connections."""
        async with self._lock:
            await self.client.close()

    async def test_connection(self, timeout_seconds: float = 5.0) -> bool:
        """
        Lightweight smoke test: attempt a single LLM call with a tiny prompt.
        Returns True if call succeeds (HTTP/parse), False on error.
        Note: This still counts as a real LLM call (cost) — use sparingly.
        """
        test_review = "This is a short test review. Please return the required JSON skeleton only."
        try:
            raw = await asyncio.wait_for(self.client.evaluate(test_review, temperature=0.0), timeout=timeout_seconds)
            parsed = self.client.extract_json_from_text(raw)
            return parsed is not None
        except Exception as e:
            logger.warning("LLM test_connection failed: %s", e)
            return False

    async def evaluate_once(self, review_text: str, temperature: float = 0.0) -> str:
        """Ask the LLM once (no retries) and return the raw text response."""
        prompt = build_review_prompt(review_text)
        raw = await self.client.evaluate(prompt, temperature=temperature)
        return raw

    async def evaluate_and_parse(
        self,
        review_text: str,
        temperature: float = 0.0,
        max_attempts: int = MAX_ATTEMPTS_PER_CALL,
    ) -> ReviewLLMOutput:
        """
        Repeatedly call the LLM (up to max_attempts) until we can parse and validate
        a JSON object that conforms to ReviewLLMOutput. Returns the validated model.
        Raises ValueError if unable to get valid structured output after attempts.
        """
        attempt = 0
        last_raw = None

        while attempt < max_attempts:
            attempt += 1
            try:
                prompt = build_review_prompt(review_text)
                raw = await self.client.evaluate(prompt, temperature=temperature)
                last_raw = raw

                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as jde:
                    logger.info("JSON decode failed on parsed string: %s", jde)
                    logger.debug("JSON candidate (truncated): %s", parsed[:1000])
                    raise

                if parsed is None:
                    logger.info("Attempt %d: no JSON extracted from LLM output; raw saved for inspection.", attempt)
                    try:
                        with open("tmp_last_raw.json", "w", encoding="utf-8") as f:
                            f.write(raw if isinstance(raw, str) else str(raw))
                    except Exception:
                        logger.debug("Failed writing tmp_last_raw.json", exc_info=True)
                    raise ValueError("No JSON parsed from LLM output")
            
                try:
                    parsed = _normalize(parsed)
                except Exception as e:
                    logger.debug("Normalization failed (non-fatal): %s", e, exc_info=True)

                if not isinstance(parsed, (dict, list)):
                    logger.info("Parsed object is not a dict/list after normalization; type=%s", type(parsed))
                    raise TypeError("Parsed object is not JSON-mappable")

                # Validate with pydantic (v2 or v1 compatible)
                try:
                    validated = ReviewLLMOutput.model_validate(parsed)
                    return validated
                except ValidationError as ve:
                    try:
                        details = ve.errors()
                    except Exception:
                        try:
                            details = ve.json()
                        except Exception:
                            details = str(ve)
                    logger.info("Pydantic validation failed on attempt %d/%d: %s", attempt, max_attempts, details)
                    logger.debug("Raw LLM output (truncated): %s", raw[:2000])
                    try:
                        with open("tmp_last_raw.json", "w", encoding="utf-8") as f:
                            f.write(raw if isinstance(raw, str) else str(raw))
                    except Exception:
                        logger.debug("Failed writing tmp_last_raw.json", exc_info=True)
                    raise

            except Exception as e:
                logger.warning("Attempt %d/%d: LLM output invalid or parsing failed: %s", attempt, max_attempts, e)
                logger.debug("Full traceback for attempt %d:", attempt, exc_info=True)
                await asyncio.sleep(0.3)

        # After attempts exhausted, raise with last raw output location for debugging
        raise ValueError(
            f"Could not obtain valid LLM JSON after {max_attempts} attempts. "
            f"Last raw output (saved to tmp_last_raw.json if available):\n{last_raw!s}"
        )

    async def evaluate_many(self, review_texts: list[str], temperature: float = 0.0):
        """
        Evaluate a list of review_texts and return a list of validated ReviewLLMOutput objects.
        """
        outputs = []
        for rt in review_texts:
            validated = await self.evaluate_and_parse(rt, temperature=temperature)
            outputs.append(validated)
        return outputs
