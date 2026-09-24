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


class OpenAICompatibleJudgeProvider:
    """Strict JudgeProvider for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 30.0,
        temperature: float = 0.0,
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
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self._judge_id = judge_id or f"openai-compatible:{model}"
        self.transport = transport

    @property
    def judge_id(self) -> str:
        return self._judge_id

    def score(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> InterviewScorecard:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt()},
                {"role": "user", "content": user_prompt(trace, rubric)},
            ],
        }

        with httpx.Client(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise JudgeProviderError(
                "Judge provider returned an unsupported response shape"
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise JudgeProviderError(
                "Judge provider returned an empty response"
            )

        return validate_scorecard(
            raw=parse_json_object(content),
            trace=trace,
            rubric=rubric,
            judge_id=self.judge_id,
            metadata={
                "provider": "openai-compatible",
                "model": self.model,
            },
        )
