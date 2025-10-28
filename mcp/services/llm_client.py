# app/services/llm_client.py
import json
import logging
from typing import Optional, Dict, Any

import httpx
import asyncio
import google.generativeai as genai

import mcp.config as config

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = getattr(config, "LLM_TIMEOUT", 15)


class LLMClient:
    """
    Core client for calling Gemini (via google.generativeai SDK) or
    fallback to HTTP if required. SDK calls are synchronous, so we run
    them in a thread executor to keep this class async-friendly.
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        # keep an httpx client for potential fallback or other endpoints
        self._client = httpx.AsyncClient(timeout=self.timeout)

        # configure the official SDK (safe to call multiple times)
        if getattr(config, "GEMINI_API_KEY", None):
            try:
                genai.configure(api_key=config.GEMINI_API_KEY)
                logger.debug("Configured google.generativeai with provided API key.")
            except Exception as e:
                logger.warning("Failed to configure google.generativeai SDK: %s", e)
        else:
            logger.warning("GEMINI_API_KEY not set in config; SDK calls will fail.")

    async def close(self):
        """Close the HTTP client session."""
        await self._client.aclose()

    async def call_gemini(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
    ) -> str:
        """
        Use the official google.generativeai SDK to call Gemini.
        The SDK is synchronous, so we run it in a thread executor.
        Returns the model's textual output.
        """
        model_name = model_name or config.GEMINI_MODEL_NAME

        def _sync_call():
            try:
                model = genai.GenerativeModel(model_name)
                # FIXED: temperature is passed inside generation_config
                resp = model.generate_content(
                    prompt,
                    generation_config={"temperature": temperature}
                )
                return getattr(resp, "text", str(resp))
            except Exception as e:
                logger.exception("Gemini SDK sync call failed: %s", e)
                raise

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_call)


    async def evaluate(self, prompt: str, temperature: float = 0.0) -> str:
        """
        Core interface method for other services.
        Uses Gemini SDK as primary provider.
        Returns raw text response (no parsing).
        """
        try:
            return await self.call_gemini(prompt, temperature=temperature)
        except Exception as e:
            logger.error("LLM call (Gemini) failed: %s", e)
            # Optionally, implement fallback to another provider here.
            raise

    @staticmethod
    def _extract_gemini_text(data: Dict[str, Any]) -> str:
        """
        Attempt to extract textual content from various Gemini response shapes.
        This is retained as a fallback if SDK returns a dict-like payload.
        """
        try:
            # common 'candidates' shape
            candidates = data.get("candidates", []) if isinstance(data, dict) else []
            if candidates:
                first = candidates[0]
                # content might be nested
                content = first.get("content", {}) if isinstance(first, dict) else {}
                if isinstance(content, dict):
                    parts = content.get("parts", [])
                    if parts and isinstance(parts, list):
                        # parts contain dicts with "text"
                        p0 = parts[0]
                        if isinstance(p0, dict):
                            return p0.get("text", "") or json.dumps(p0)
                        return str(p0)
                elif isinstance(content, list) and content:
                    p0 = content[0]
                    if isinstance(p0, dict):
                        parts = p0.get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                    return str(content[0])
            # fallback: try top-level 'text' or 'response' or stringify
            if isinstance(data, dict):
                if "text" in data and isinstance(data["text"], str):
                    return data["text"]
                if "output" in data:
                    out = data["output"]
                    if isinstance(out, list) and out:
                        # join parts safely
                        pieces = []
                        for x in out:
                            if isinstance(x, dict):
                                pieces.append(x.get("content") or x.get("text") or json.dumps(x))
                            else:
                                pieces.append(str(x))
                        return " ".join(pieces)
                    return str(out)
            return json.dumps(data)
        except Exception as e:
            logger.warning("Gemini text extraction failed: %s", e)
            return json.dumps(data)
