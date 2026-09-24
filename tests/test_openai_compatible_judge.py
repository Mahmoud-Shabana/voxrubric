import json

import httpx
import pytest

from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn
from voxrubric.providers import JudgeProviderError, OpenAICompatibleJudgeProvider


def rubric() -> Rubric:
    return Rubric(
        id="backend",
        title="Backend Engineer",
        dimensions=[
            RubricDimension(
                id="debugging",
                description="Diagnoses production failures using evidence.",
            ),
            RubricDimension(
                id="reliability",
                description="Designs reliable production systems.",
            ),
        ],
    )


def trace() -> InterviewTrace:
    return InterviewTrace(
        session_id="session-1",
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
                    "I compared event-loop lag with database query latency "
                    "and found a blocking driver."
                ),
                parent_turn_id="q1",
            ),
            Turn(
                id="q2",
                speaker=Speaker.INTERVIEWER,
                text="What did you change for reliability?",
                rubric_tags=["reliability"],
            ),
            Turn(
                id="a2",
                speaker=Speaker.CANDIDATE,
                text="I added timeouts, retries, and a circuit breaker.",
                parent_turn_id="q2",
            ),
        ],
    )


def response_payload(dimensions):
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"dimensions": dimensions})
                }
            }
        ]
    }


def provider_for(dimensions, requests):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json=response_payload(dimensions),
        )

    return OpenAICompatibleJudgeProvider(
        base_url="https://judge.example/v1",
        model="judge-model",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )


def test_hosted_judge_maps_valid_grounded_response():
    requests = []
    provider = provider_for(
        [
            {
                "dimension": "reliability",
                "score": 8,
                "evidence": [
                    {
                        "turn_id": "a2",
                        "quote": "timeouts, retries, and a circuit breaker",
                    }
                ],
                "rationale": "Concrete resilience controls.",
            },
            {
                "dimension": "debugging",
                "score": 9,
                "evidence": [
                    {
                        "turn_id": "a1",
                        "quote": "event-loop lag with database query latency",
                    }
                ],
            },
        ],
        requests,
    )

    scorecard = provider.score(trace(), rubric())

    assert scorecard.judge_id == "openai-compatible:judge-model"
    assert [item.dimension for item in scorecard.dimensions] == [
        "debugging",
        "reliability",
    ]
    assert [item.score for item in scorecard.dimensions] == [9, 8]
    assert scorecard.metadata == {
        "provider": "openai-compatible",
        "model": "judge-model",
    }

    request = requests[0]
    assert request.url == "https://judge.example/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer secret"
    body = json.loads(request.content)
    assert body["temperature"] == 0.0
    user_payload = json.loads(body["messages"][1]["content"])
    assert user_payload["trace"]["session_id"] == "session-1"
    assert "metadata" not in user_payload["trace"]["turns"][0]


def test_hosted_judge_rejects_fabricated_quote():
    provider = provider_for(
        [
            {
                "dimension": "debugging",
                "score": 9,
                "evidence": [
                    {
                        "turn_id": "a1",
                        "quote": "I used distributed tracing",
                    }
                ],
            },
            {
                "dimension": "reliability",
                "score": 8,
                "evidence": [],
            },
        ],
        [],
    )

    with pytest.raises(
        JudgeProviderError,
        match="not literal",
    ):
        provider.score(trace(), rubric())


def test_hosted_judge_rejects_unknown_dimension():
    provider = provider_for(
        [
            {
                "dimension": "personality",
                "score": 10,
                "evidence": [],
            },
            {
                "dimension": "reliability",
                "score": 8,
                "evidence": [],
            },
        ],
        [],
    )

    with pytest.raises(
        JudgeProviderError,
        match="unknown dimension",
    ):
        provider.score(trace(), rubric())


def test_hosted_judge_requires_every_rubric_dimension_once():
    provider = provider_for(
        [
            {
                "dimension": "debugging",
                "score": 7,
                "evidence": [],
            }
        ],
        [],
    )

    with pytest.raises(
        JudgeProviderError,
        match="omitted rubric dimensions: reliability",
    ):
        provider.score(trace(), rubric())


def test_hosted_judge_accepts_fenced_json_but_rejects_non_json():
    valid = {
        "dimensions": [
            {
                "dimension": "debugging",
                "score": 7,
                "evidence": [],
            },
            {
                "dimension": "reliability",
                "score": 6,
                "evidence": [],
            },
        ]
    }

    def fenced_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "```json\n"
                            + json.dumps(valid)
                            + "\n```"
                        }
                    }
                ]
            },
        )

    provider = OpenAICompatibleJudgeProvider(
        base_url="https://judge.example/v1",
        model="judge-model",
        transport=httpx.MockTransport(fenced_handler),
    )
    assert provider.score(trace(), rubric()).dimensions[0].score == 7

    def invalid_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "not json"}}
                ]
            },
        )

    invalid = OpenAICompatibleJudgeProvider(
        base_url="https://judge.example/v1",
        model="judge-model",
        transport=httpx.MockTransport(invalid_handler),
    )
    with pytest.raises(
        JudgeProviderError,
        match="not valid JSON",
    ):
        invalid.score(trace(), rubric())
