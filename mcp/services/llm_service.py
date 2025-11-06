# app/services/service.py
import asyncio
import json
import logging
from typing import Optional
from pydantic import ValidationError
from mcp.services.llm_client import LLMClient
from mcp.services.prompt import build_review_prompt
from mcp.schemas import ReviewLLMOutput
from mcp.services.utils import _normalize
import mcp.config as config
from statistics import mode, StatisticsError, mean
from collections import Counter
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# How many times to retry a single evaluate call until we accept a parsed JSON
MAX_ATTEMPTS_PER_CALL = getattr(config, "MAX_REVIEW_ATTEMPTS", 10)


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
                    raise ValueError("No JSON parsed from LLM output")
            
                try:
                    parsed = _normalize(parsed)
                except Exception as e:
                    logger.debug("Normalization failed (non-fatal): %s", e, exc_info=True)

                if not isinstance(parsed, (dict, list)):
                    logger.info("Parsed object is not a dict/list after normalization; type=%s", type(parsed))
                    raise TypeError("Parsed object is not JSON-mappable")

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


## Still working on multiple output resolution
    # async def evaluate_multiple_times(
    #         self,
    #         review_text: str,
    #         num_runs: int = 2,
    #         temperature: float = 0.0,
    #         delay_between_runs: float = 0.3,
    #     ) -> ReviewLLMOutput:
            
    #         """
    #         Run evaluate_and_parse() multiple times (default=5) on the same review text
    #         and compute the mode of numeric metrics to form a final result.

    #         Returns:
    #             ReviewLLMOutput: the final merged review result.
    #         """

    #         results = []

    #         for i in range(num_runs):
    #             try:
    #                 logger.info(f"Evaluation run {i+1}/{num_runs} for review.")
    #                 validated = await self.evaluate_and_parse(
    #                     review_text, temperature=temperature
    #                 )
    #                 print(f" Run {i+1} succeeded.")
    #                 results.append(validated)
                    
    #             except Exception as e:
    #                 logger.warning(f"Run {i+1}/{num_runs} failed: {e}")
    #             await asyncio.sleep(delay_between_runs)

    #         if not results:
    #             raise ValueError("All evaluation runs failed — no valid results.")

    #         # Convert to dicts for aggregation
    #         dicts = [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in results]
    #         aggregated = {}

    #         for key in dicts[0].keys():
    #             values = [d[key] for d in dicts if key in d]

    #             # If numeric → take mean
    #             if all(isinstance(v, (int, float)) for v in values):
    #                 aggregated[key] = round(mode(values), 2)

    #             # If list → take mode of list items flattened
    #             elif all(isinstance(v, list) for v in values):
    #                 flat = [item for sublist in values for item in sublist]
    #                 try:
    #                     aggregated[key] = [mode(flat)]
    #                 except StatisticsError:
    #                     aggregated[key] = flat[:1] if flat else []

    #             # If string → take mode (most common)
    #             elif all(isinstance(v, str) for v in values):
    #                 try:
    #                     aggregated[key] = mode(values)
    #                 except StatisticsError:
    #                     aggregated[key] = values[0]

    #             # Else fallback to first
    #             else:
    #                 aggregated[key] = values[0]

    #         print(final_output)

    #         final_output = ReviewLLMOutput.model_validate(aggregated)

    #         logger.info("Final aggregated review generated after %d runs.", len(results))
    #         return final_output

        

    #         def _most_common_non_none(vals: List[Any]):
    #             """Return (value, is_unique) where value is mode if unique, else None."""
    #             filtered = [v for v in vals if v is not None]
    #             if not filtered:
    #                 return None, True
    #             cnt = Counter(filtered)
    #             most_common, freq = cnt.most_common(1)[0]
    #             # check if unique mode
    #             if sum(1 for v in cnt.values() if v == freq) == 1:
    #                 return most_common, True
    #             return None, False

    #         def aggregate_runs(runs: List[Dict]) -> Dict:
    #             """
    #             Aggregates a list of run dicts that follow the structure you provided:
    #             - each item has 'reasoning', 'evaluation', 'feedback'
    #             - 'evaluation' maps criteria -> {'score': <num|None>, 'justification': <str>}
    #             Returns an aggregated dict in the same structure.
    #             """
    #             if not runs:
    #                 raise ValueError("No runs provided")

    #             # collect keys
    #             all_eval_keys = set()
    #             all_reasoning_keys = set()
    #             for r in runs:
    #                 all_eval_keys |= set(r.get("evaluation", {}).keys())
    #                 all_reasoning_keys |= set(r.get("reasoning", {}).keys())

    #             aggregated_eval = {}
    #             for key in sorted(all_eval_keys):
    #                 # collect scores and justifications
    #                 scores = []
    #                 justs = []
    #                 for r in runs:
    #                     ev = r.get("evaluation", {}).get(key)
    #                     if isinstance(ev, dict):
    #                         scores.append(ev.get("score"))
    #                         justs.append(ev.get("justification"))
    #                     else:
    #                         # handle cases where evaluation might be nested differently
    #                         scores.append(None)
    #                         justs.append(None)

    #                 # aggregate score
    #                 mode_score, unique = _most_common_non_none(scores)
    #                 if mode_score is not None:
    #                     final_score = mode_score
    #                 else:
    #                     # fallback: compute mean of numeric values (ignore None)
    #                     numeric = [s for s in scores if isinstance(s, (int, float))]
    #                     final_score = None if not numeric else round(mean(numeric), 1)

    #                 # aggregate justification: prefer identical, else join unique
    #                 uniq_justs = [j for j in dict.fromkeys(justs) if j]  # preserve order, drop falsy
    #                 if not uniq_justs:
    #                     final_just = None
    #                 elif len(uniq_justs) == 1:
    #                     final_just = uniq_justs[0]
    #                 else:
    #                     # join into a compact form
    #                     final_just = " / ".join(uniq_justs)

    #                 aggregated_eval[key] = {"score": final_score, "justification": final_just}

    #             # aggregate reasoning fields (text)
    #             aggregated_reasoning = {}
    #             for key in sorted(all_reasoning_keys):
    #                 vals = [r.get("reasoning", {}).get(key) for r in runs if r.get("reasoning", {}).get(key)]
    #                 vals = [v for v in vals if v is not None]
    #                 if not vals:
    #                     aggregated_reasoning[key] = None
    #                     continue
    #                 cnt = Counter(vals)
    #                 most_common, freq = cnt.most_common(1)[0]
    #                 if sum(1 for v in cnt.values() if v == freq) == 1:
    #                     aggregated_reasoning[key] = most_common
    #                 else:
    #                     # tie -> join unique
    #                     aggregated_reasoning[key] = " / ".join(dict.fromkeys(vals))

    #             # aggregate feedback
    #             feedbacks = [r.get("feedback") for r in runs if r.get("feedback")]
    #             if not feedbacks:
    #                 final_feedback = None
    #             else:
    #                 cnt = Counter(feedbacks)
    #                 most_common, freq = cnt.most_common(1)[0]
    #                 if sum(1 for v in cnt.values() if v == freq) == 1:
    #                     final_feedback = most_common
    #                 else:
    #                     final_feedback = " / ".join(dict.fromkeys(feedbacks))

    #             return {"reasoning": aggregated_reasoning, "evaluation": aggregated_eval, "feedback": final_feedback}
