import asyncio
import json

import httpx

from voxrubric.adapters import NoraHttpAgentFactory
from voxrubric.models import Rubric, RubricDimension


def run(coro):
    return asyncio.run(coro)


def test_nora_http_adapter_maps_public_api_to_arena_utterances():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")

        if request.url.path == "/v1/jobs":
            payload = json.loads(request.content)
            assert payload["max_tools"] == 0
            assert payload["competencies"][0]["id"] == "debugging"
            return httpx.Response(
                201,
                json={
                    "id": "job-1",
                    **payload,
                },
            )

        if request.url.path == "/v1/sessions":
            payload = json.loads(request.content)
            assert payload["job_id"] == "job-1"
            assert payload["consent_to_ai_interview"] is True
            return httpx.Response(
                201,
                json={
                    "id": "session-1",
                    "job_id": "job-1",
                    "candidate_ref": payload["candidate_ref"],
                    "locale": payload["locale"],
                    "integrity_level": "none",
                    "status": "created",
                    "paused": False,
                    "turns": [],
                    "covered_competencies": [],
                    "followups_by_competency": {},
                    "asked_anchor_competencies": [],
                    "asked_questions": 0,
                    "evidence_graph": {},
                    "transcript_revisions": [],
                    "appeals": [],
                    "integrity_signals": [],
                    "tools": [],
                    "tool_submissions": [],
                    "tool_evaluations": [],
                    "events": [],
                },
            )

        if request.url.path.endswith("/start"):
            return httpx.Response(
                200,
                json={
                    "session_id": "session-1",
                    "status": "running",
                    "interviewer_turn": {
                        "id": "q1",
                        "speaker": "interviewer",
                        "text": "Describe a debugging incident.",
                        "parent_turn_id": None,
                        "competency_tags": ["debugging"],
                        "response_latency_ms": 120,
                        "metadata": {
                            "question_lane": "anchor",
                        },
                    },
                    "tool_invocation": None,
                },
            )

        if request.url.path.endswith("/responses"):
            payload = json.loads(request.content)
            assert payload["text"] == "I compared traces."
            return httpx.Response(
                200,
                json={
                    "session_id": "session-1",
                    "status": "completed",
                    "interviewer_turn": {
                        "id": "q2",
                        "speaker": "interviewer",
                        "text": "Thank you. The interview is complete.",
                        "parent_turn_id": "a1",
                        "competency_tags": ["debugging"],
                        "response_latency_ms": 240,
                        "metadata": {
                            "question_lane": "closing",
                        },
                    },
                    "tool_invocation": None,
                },
            )

        return httpx.Response(404)

    async def scenario():
        factory = NoraHttpAgentFactory(
            base_url="https://nora.test",
            agent_id="nora-under-test",
            transport=httpx.MockTransport(handler),
        )
        session = factory.create()
        rubric = Rubric(
            id="r",
            title="r",
            dimensions=[
                RubricDimension(
                    id="debugging",
                    description="Production debugging",
                )
            ],
        )

        opening = await session.start(
            role="Backend Engineer",
            rubric=rubric,
            locale="en",
        )
        assert opening.text == "Describe a debugging incident."
        assert opening.rubric_tags == ["debugging"]
        assert opening.is_followup is False
        assert opening.completes_interview is False
        assert opening.metadata["response_latency_ms"] == 120

        closing = await session.respond(
            "I compared traces."
        )
        assert closing.completes_interview is True
        assert closing.is_followup is True
        assert closing.metadata["question_lane"] == "closing"
        assert closing.metadata["arena_remote_agent"] == "nora-under-test"

    run(scenario())

    assert calls == [
        "POST /v1/jobs",
        "POST /v1/sessions",
        "POST /v1/sessions/session-1/start",
        "POST /v1/sessions/session-1/responses",
    ]


def test_factory_creates_fresh_session_objects():
    factory = NoraHttpAgentFactory()
    first = factory.create()
    second = factory.create()

    assert first is not second
    assert first.session_id is None
    assert second.session_id is None
