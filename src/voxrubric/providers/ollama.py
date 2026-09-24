from __future__ import annotations

import httpx

from ..models import InterviewScorecard, InterviewTrace, Rubric
from ._shared import (
    JudgeProviderError,
    parse_json_object,
    system_prompt,
    user_prompt,
    validate_scorecard,
)


class OllamaJudgeProvider:
    """Strict local JudgeProvider for Ollama's native /api/chat endpoint."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 60.0,
        temperature: float = 0.0,
        keep_alive: str | int | None = None,
        judge_id: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must not be empty")
        if not model.strip():
            raise ValueError("model must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if not 0 <= temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.keep_alive = keep_alive
        self._judge_id = judge_id or f"ollama:{model}"
        self.transport = transport

    @property
    def judge_id(self) -> str:
        return self._judge_id

    def score(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> InterviewScorecard:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system_prompt()},
                {"role": "user", "content": user_prompt(trace, rubric)},
            ],
            "options": {
                "temperature": self.temperature,
            },
        }
        if self.keep_alive is not None:
            payload["keep_alive"] = self.keep_alive

        with httpx.Client(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        try:
            content = body["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise JudgeProviderError(
                "Ollama judge returned an unsupported response shape"
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise JudgeProviderError(
                "Ollama judge returned an empty response"
            )

        metadata = {
            "provider": "ollama",
            "model": self.model,
            "local": True,
        }
        for key in (
            "total_duration",
            "load_duration",
            "prompt_eval_count",
            "eval_count",
        ):
            value = body.get(key)
            if isinstance(value, int) and value >= 0:
                metadata[key] = value

        return validate_scorecard(
            raw=parse_json_object(content),
            trace=trace,
            rubric=rubric,
            judge_id=self.judge_id,
            metadata=metadata,
        )
