from __future__ import annotations
import os
from typing import Any, Dict, Iterable, Optional
import httpx

REQUESTY_BASE_URL = os.getenv("REQUESTY_BASE_URL", "https://router.requesty.ai/v1")
REQUESTY_API_KEY = os.getenv("REQUESTY_API_KEY")
REQUESTY_DEFAULT_MODEL = os.getenv("REQUESTY_DEFAULT_MODEL", "openai/gpt-4o")

class RequestyError(RuntimeError):
    pass

class RequestyClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, timeout: float = 60.0):
        self.base_url = (base_url or REQUESTY_BASE_URL).rstrip("/")
        self.api_key = api_key or REQUESTY_API_KEY
        self.timeout = timeout
        if not self.api_key:
            raise RequestyError("REQUESTY_API_KEY is not set. Please export it in the environment.")
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat_completion(self, messages: Iterable[Dict[str, Any]], model: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """
        Non-streaming chat completion via Requesty (OpenAI-compatible API).
        Pass model like "openai/gpt-4o" or an alias configured in Requesty.
        """
        payload: Dict[str, Any] = {
            "model": model or REQUESTY_DEFAULT_MODEL,
            "messages": list(messages),
        }
        payload.update(kwargs)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers,
                json=payload,
            )
        resp.raise_for_status()
        return resp.json()

    async def chat_completion_stream(self, messages: Iterable[Dict[str, Any]], model: Optional[str] = None, **kwargs: Any):
        """
        Streaming chat completion (yields SSE 'data:' JSON chunks).
        """
        payload: Dict[str, Any] = {
            "model": model or REQUESTY_DEFAULT_MODEL,
            "messages": list(messages),
            "stream": True,
        }
        payload.update(kwargs)
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    yield data
