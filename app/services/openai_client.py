from __future__ import annotations

import os
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Any

import httpx
from fastapi import HTTPException

@dataclass
class LLMReply:
    text: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

async def _post_with_retries(url: str, headers: dict, payload: dict, timeout: float = 90.0, retries: int = 4) -> dict:
    last_exc = None
    backoff = 1.5
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(url, headers=headers, json=payload)
            if r.status_code < 400:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                await asyncio.sleep(backoff ** attempt)
                continue
            raise HTTPException(status_code=500, detail=r.text)
        except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.WriteError) as e:
            last_exc = e
            await asyncio.sleep(backoff ** attempt)
            continue
    raise HTTPException(status_code=502, detail=f"Falha ao conectar ao OpenAI após {retries} tentativas: {last_exc}")

class OpenAIClient:
    def __init__(self, model: str, temperature: float = 0.0):
        self.model = model
        self.temperature = temperature
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY não configurada")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    async def complete(self, system: str, user: str) -> LLMReply:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        data = await _post_with_retries(url, headers, payload)
        text = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})
        return LLMReply(
            text=text,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )
