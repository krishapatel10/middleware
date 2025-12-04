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

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        # keep an httpx client for potential fallback or other endpoints
        self._client = httpx.AsyncClient(timeout=self.timeout)

        # configure the official SDK (safe to call multiple times)
        api_key = getattr(config, "GEMINI_API_KEY", None)
        if api_key:
            try:
                genai.configure(api_key=api_key)
                logger.info("Configured google.generativeai with API key (length: %d)", len(api_key))
            except Exception as e:
                logger.error("Failed to configure google.generativeai SDK: %s", e)
                raise
        else:
            error_msg = "GEMINI_API_KEY not set in config; SDK calls will fail."
            logger.error(error_msg)
            raise ValueError(error_msg)

    async def close(self):
        """Close the HTTP client session."""
        await self._client.aclose()

    async def call_gemini(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
    ) -> str:
        model_name = model_name or config.GEMINI_MODEL_NAME

        def _sync_call():
            try:
                logger.debug("Creating GenerativeModel with name: %s", model_name)
                model = genai.GenerativeModel(model_name)
                logger.debug("Calling generate_content with prompt length: %d", len(prompt))
              
                resp = model.generate_content(
                    prompt,
                    generation_config={"temperature": temperature}
                )
                logger.debug("Received response from Gemini API")
                
                # Check for response text
                if hasattr(resp, "text") and resp.text:
                    return resp.text
                elif hasattr(resp, "candidates") and resp.candidates:
                    # Try to get text from candidates
                    candidate = resp.candidates[0]
                    if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                        parts = candidate.content.parts
                        if parts:
                            text = getattr(parts[0], "text", None)
                            if text:
                                return text
                
                # Fallback: try to stringify the response
                response_str = str(resp)
                if response_str and response_str != "None":
                    logger.warning("Gemini response has no text attribute, using string representation")
                    return response_str
                
                # If we get here, the response is empty
                logger.error("Gemini API returned empty response. Response object: %s", resp)
                raise ValueError(f"Gemini API returned empty response. Check API key and model availability.")
                
            except Exception as e:
                logger.exception("Gemini SDK sync call failed: %s", e)
                raise

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_call)


    async def evaluate(self, prompt: str, temperature: float = 0.0) -> str:
        try:
            # Log prompt length for debugging
            logger.debug("Calling Gemini with prompt length: %d chars", len(prompt))
            result = await self.call_gemini(prompt, temperature=temperature)
            logger.debug("Gemini returned response length: %d chars", len(result) if result else 0)
            return result
        except Exception as e:
            logger.error("LLM call (Gemini) failed: %s", e)
            logger.error("Prompt length was: %d chars", len(prompt))
            logger.error("Prompt preview (first 500 chars): %s", prompt[:500])
            raise
