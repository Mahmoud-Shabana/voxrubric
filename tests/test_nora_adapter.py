import asyncio
import json

import httpx

from voxrubric.models import Rubric, RubricDimension
from voxrubric.nora_adapter import NoraAgentFactory


def run(coro):
    return asyncio.run(coro)


def test_nora_adapter_maps_remote_interview_into_arena_utterances():
    calls: list[tuple[str, str, dict | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = None
        if request.content:
            payload = json.loads(request.content.decode("utf-8"))
        calls.append((request.method, request.url.path, payload))

        if request.url.path == "/v1/jobs":
            return httpx.Response(
                201,
                json={
                    "id": "job-1",
                    "title": payload["title"],
                    "description": payload["description"],
                    "competencies": payload["competencies"],
                    "max_questions": payload["max_questions"],
                    "anchor_ratio": payload["anchor_ratio"],
                    "tool_templates": [],
                    "max_tools": 2,
                },
            )

        if request.url.path == "/v1/sessions":
            return httpx.Response(
                201,
                json={
                    "id": "session-1",
                    "job_id": "job-1",
                    "candidate_ref": payload["candidate_ref"],
                    "locale": payload["locale"],
                },
            )

        if request.url.path == "/v1/sessions/session-1/start":
            return httpx.Response(
                200,
                json={
                    "session_id": "session-1",
                    "status": "running",
                    "interviewer_turn": {
                        "id": "q1",
                        "speaker": "interviewer",
                        "text": "Describe a production incident.",
                        "parent_turn_id": None,
                        "competency_tags": ["debugging"],
                        "metadata": {
                            "question_lane": "anchor",
                        },
                    },
                    "tool_invocation": None,
                },
            )

        if request.url.path == "/v1/sessions/session-1/responses":
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
                        "metadata": {
                            "question_lane": "closing",
                        },
                    },
                    "tool_invocation": None,
                },
            )

        return httpx.Response(404, json={"detail": "not found"})

    transport = httpx.MockTransport(handler)

    def client_factory():
        return httpx.AsyncClient(
            transport=transport,
            base_url="http://nora.test",
        )

    async def scenario():
        factory = NoraAgentFactory(
            agent_id="nora-local",
            base_url="http://nora.test",
            client_factory=client_factory,
        )
        session = factory.create()
        rubric = Rubric(
            id="r",
            title="Backend",
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
        assert opening.text == "Describe a production incident."
        assert opening.rubric_tags == ["debugging"]
        assert opening.is_followup is False

        closing = await session.respond(
            "I reproduced the issue and compared traces."
        )
        assert closing.completes_interview is True
        assert closing.is_followup is True
        assert closing.metadata["remote_turn_id"] == "q2"

        await session.aclose()

    run(scenario())

    paths = [path for _, path, _ in calls]
    assert paths == [
        "/v1/jobs",
        "/v1/sessions",
        "/v1/sessions/session-1/start",
        "/v1/sessions/session-1/responses",
    ]
