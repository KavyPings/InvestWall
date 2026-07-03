"""Optional local-LLM explainer via Ollama (Gemma / Qwen / Llama).

Enable with LLM_PROVIDER=ollama and a running Ollama server. Falls back to the
template explainer automatically on any failure (see LLMExplainer.safe_explain).
"""
from __future__ import annotations

import json
import urllib.request

from app.config import get_settings
from app.llm._prompt import SYSTEM_PROMPT, build_user_prompt
from app.llm.base import ExplanationInput, LLMExplainer


class OllamaExplainer(LLMExplainer):
    provider = "ollama"

    def explain(self, data: ExplanationInput) -> str:
        settings = get_settings()
        payload = {
            "model": settings.ollama_model,
            "system": SYSTEM_PROMPT,
            "prompt": build_user_prompt(data),
            "stream": False,
            "options": {"temperature": 0.3},
        }
        req = urllib.request.Request(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return str(body.get("response", "")).strip()
