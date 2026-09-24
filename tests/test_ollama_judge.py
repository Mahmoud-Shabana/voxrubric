import json

import httpx
import pytest

from voxrubric.models import (
    InterviewTrace,
    Rubric,
    RubricDimension,
    Speaker,
    Turn,
)
from voxrubric.providers import JudgeProviderError, OllamaJudgeProvider


def rubric() -> Rubric:
    return Rubric(
        id="backend",
        title="Backend Engineer",
        dimensions=[
            RubricDimension(
                id="debugging",
                description="Diagnoses production failures.",
            ),
            RubricDimension(
                id="reliability",
                description="Builds reliable systems.",
            ),
        ],
    )


def trace() -> InterviewTrace:
    return InterviewTrace(
        session_id="session-local",
        role="Backend Engineer",
        locale="en",
        turns=[
            Turn(
                id="q1",
                speaker=Speaker.INTERVIEWER,
                text="Describe a production incident.",
                rubric_tags=["debugging"],
            ),
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text=(
                    "I compared event-loop lag with database latency "
                    "and found a blocking driver."
                ),
                parent_turn_id="q1",
            ),
            Turn(
                id="q2",
                speaker=Speaker.INTERVIEWER,
                text="How did you improve reliability?",
                rubric_tags=["reliability"],
            ),
            Turn(
                id="a2",
                speaker=Speaker.CANDIDATE,
                text="I added timeouts and a circuit breaker.",
                parent_turn_id="q2",
            ),
        ],
    )


def valid_dimensions():
    return [
        {
            "dimension": "debugging",
            "score": 9,
            "evidence": [
                {
                    "turn_id": "a1",
                    "quote": "event-loop lag with database latency",
                }
            ],
        },
        {
            "dimension": "reliability",
            "score": 8,
            "evidence": [
                {
                    "turn_id": "a2",
                    "quote": "timeouts and a circuit breaker",
                }
            ],
        },
    ]


def test_ollama_judge_uses_native_chat_contract_and_preserves_metadata():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": "qwen3:8b",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {"dimensions": valid_dimensions()}
                    ),
                },
                "done": True,
                "total_duration": 1200,
                "load_duration": 300,
                "prompt_eval_count": 420,
                "eval_count": 180,
            },
        )

    provider = OllamaJudgeProvider(
        model="qwen3:8b",
        keep_alive="10m",
        transport=httpx.MockTransport(handler),
    )

    scorecard = provider.score(trace(), rubric())

    assert scorecard.judge_id == "ollama:qwen3:8b"
    assert [item.score for item in scorecard.dimensions] == [9, 8]
    assert scorecard.metadata == {
        "provider": "ollama",
        "model": "qwen3:8b",
        "local": True,
        "total_duration": 1200,
        "load_duration": 300,
        "prompt_eval_count": 420,
        "eval_count": 180,
    }

    request = requests[0]
    assert str(request.url) == "http://127.0.0.1:11434/api/chat"
    body = json.loads(request.content)
    assert body["model"] == "qwen3:8b"
    assert body["stream"] is False
    assert body["format"] == "json"
    assert body["options"]["temperature"] == 0.0
    assert body["keep_alive"] == "10m"
    assert body["messages"][0]["role"] == "system"
    user_payload = json.loads(body["messages"][1]["content"])
    assert user_payload["trace"]["session_id"] == "session-local"


def test_ollama_judge_reuses_strict_literal_grounding():
    dimensions = valid_dimensions()
    dimensions[0]["evidence"][0]["quote"] = "I used tracing"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {"dimensions": dimensions}
                    ),
                }
            },
        )

    provider = OllamaJudgeProvider(
        model="local-test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        JudgeProviderError,
        match="not literal",
    ):
        provider.score(trace(), rubric())


def test_ollama_judge_rejects_unsupported_response_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"response": "legacy shape"},
        )

    provider = OllamaJudgeProvider(
        model="local-test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        JudgeProviderError,
        match="unsupported response shape",
    ):
        provider.score(trace(), rubric())


def test_ollama_judge_allows_custom_local_endpoint_and_id():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {"dimensions": valid_dimensions()}
                    ),
                }
            },
        )

    provider = OllamaJudgeProvider(
        base_url="http://ollama.internal:11434/",
        model="qwen-local",
        judge_id="local-primary",
        temperature=0.2,
        transport=httpx.MockTransport(handler),
    )

    scorecard = provider.score(trace(), rubric())

    assert scorecard.judge_id == "local-primary"
    assert seen == ["http://ollama.internal:11434/api/chat"]
