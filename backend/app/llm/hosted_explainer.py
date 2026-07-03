"""Optional hosted-LLM explainer (Anthropic Messages API compatible).

Enable with LLM_PROVIDER=hosted and HOSTED_LLM_API_KEY set. Falls back to the
template explainer automatically on any failure.
"""
from __future__ import annotations

import json
import urllib.request

from app.config import get_settings
from app.llm._prompt import SYSTEM_PROMPT, build_user_prompt
from app.llm.base import ExplanationInput, LLMExplainer


class HostedExplainer(LLMExplainer):
    provider = "hosted"

    def explain(self, data: ExplanationInput) -> str:
        settings = get_settings()
        if not settings.hosted_llm_api_key:
            raise RuntimeError("HOSTED_LLM_API_KEY not configured")

        payload = {
            "model": settings.hosted_llm_model,
            "max_tokens": 400,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": build_user_prompt(data)}],
        }
        req = urllib.request.Request(
            f"{settings.hosted_llm_base_url.rstrip('/')}/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": settings.hosted_llm_api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        blocks = body.get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
