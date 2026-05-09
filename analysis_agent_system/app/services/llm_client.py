"""LLM client service – thin wrapper around the OpenAI-compatible VLLM API."""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from analysis_agent_system.app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Asynchronous client for the VLLM OpenAI-compatible API."""

    def __init__(self) -> None:
        self.api_base = settings.VLLM_API_BASE.rstrip("/")
        self.api_key = settings.VLLM_API_KEY
        self.model = settings.MODEL_NAME
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE
        self.timeout = settings.LLM_TIMEOUT

    # ------------------------------------------------------------------
    # Core chat completion
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict] = None,
    ) -> str:
        """Send a chat completion request and return the assistant content.

        Parameters
        ----------
        messages : list[dict]
            OpenAI-style message list, e.g.
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        temperature : float, optional
        max_tokens : int, optional
        response_format : dict, optional
            e.g. {"type": "json_object"} to force JSON output

        Returns
        -------
        str  – the text content of the first choice
        """
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        logger.debug("LLM response tokens used: %s", data.get("usage"))
        return content

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        """Chat that expects a JSON response (forces JSON mode)."""
        raw = await self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("LLM did not return valid JSON, returning raw string")
            return raw

    async def analyse(self, system_prompt: str, user_prompt: str) -> str:
        """Shortcut: system + user message → assistant text."""
        return await self.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])

    async def analyse_json(self, system_prompt: str, user_prompt: str) -> Any:
        """Shortcut: system + user message → parsed JSON."""
        return await self.chat_json([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])


# Module-level singleton
llm_client = LLMClient()
