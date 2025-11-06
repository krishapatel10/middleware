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
        model_name = model_name or config.GEMINI_MODEL_NAME

        def _sync_call():
            try:
                model = genai.GenerativeModel(model_name)
              
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
        try:
            return await self.call_gemini(prompt, temperature=temperature)
        except Exception as e:
            logger.error("LLM call (Gemini) failed: %s", e)
           
            raise
