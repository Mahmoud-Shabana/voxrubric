from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx

from ..models import AgentUtterance, Rubric


class NoraHttpAgentSession:
    """Arena adapter for a running Nora HTTP API.

    The adapter intentionally uses Nora's public HTTP contract instead of
    importing Nora internals, keeping both projects independently deployable.
    """

    def __init__(
        self,
        *,
        base_url: str,
        agent_id: str,
        timeout_seconds: float = 30.0,
        headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.timeout_seconds = timeout_seconds
        self.headers = dict(headers or {})
        self.transport = transport
        self.session_id: str | None = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            headers=self.headers,
            transport=self.transport,
        ) as client:
            response = await client.request(
                method,
                path,
                json=json_body,
            )
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, dict):
            raise RuntimeError(
                f"Nora endpoint {path} returned a non-object JSON response"
            )
        return payload

    @staticmethod
    def _utterance(step: dict[str, Any]) -> AgentUtterance:
        status = str(step.get("status", ""))
        turn = step.get("interviewer_turn")

        if not isinstance(turn, dict):
            return AgentUtterance(
                text="Interview completed.",
                completes_interview=(status == "completed"),
                metadata={"adapter": "nora-http"},
            )

        metadata = dict(turn.get("metadata") or {})
        latency = turn.get("response_latency_ms")
        if isinstance(latency, int):
            metadata.setdefault(
                "response_latency_ms",
                latency,
            )

        parent_turn_id = turn.get("parent_turn_id")
        return AgentUtterance(
            text=str(turn.get("text", "")),
            rubric_tags=[
                str(tag)
                for tag in (turn.get("competency_tags") or [])
            ],
            metadata=metadata,
            is_followup=bool(parent_turn_id),
            completes_interview=(status == "completed"),
        )

    async def start(
        self,
        *,
        role: str,
        rubric: Rubric,
        locale: str,
    ) -> AgentUtterance:
        competencies = [
            {
                "id": dimension.id,
                "description": dimension.description,
                "weight": dimension.weight,
            }
            for dimension in rubric.dimensions
        ]
        job = await self._request(
            "POST",
            "/v1/jobs",
            json_body={
                "title": role,
                "description": (
                    "VoxRubric Arena controlled role for evaluating "
                    f"the interview agent behavior for {role}."
                ),
                "competencies": competencies,
                "max_questions": max(4, len(competencies) * 2),
                "anchor_ratio": 0.4,
                "tool_templates": [],
                "max_tools": 0,
            },
        )

        job_id = job.get("id")
        if not isinstance(job_id, str) or not job_id:
            raise RuntimeError("Nora job creation did not return an id")

        session = await self._request(
            "POST",
            "/v1/sessions",
            json_body={
                "job_id": job_id,
                "candidate_ref": (
                    "voxrubric-arena-"
                    + uuid4().hex[:12]
                ),
                "locale": locale,
                "consent_to_ai_interview": True,
                "consent_to_transcript": True,
                "integrity_level": "none",
            },
        )
        session_id = session.get("id")
        if not isinstance(session_id, str) or not session_id:
            raise RuntimeError(
                "Nora session creation did not return an id"
            )
        self.session_id = session_id

        step = await self._request(
            "POST",
            f"/v1/sessions/{self.session_id}/start",
        )
        utterance = self._utterance(step)
        utterance.metadata.setdefault(
            "arena_remote_agent",
            self.agent_id,
        )
        return utterance

    async def respond(
        self,
        candidate_text: str,
    ) -> AgentUtterance:
        if not self.session_id:
            raise RuntimeError(
                "Nora Arena session has not been started"
            )

        step = await self._request(
            "POST",
            f"/v1/sessions/{self.session_id}/responses",
            json_body={"text": candidate_text},
        )
        utterance = self._utterance(step)
        utterance.metadata.setdefault(
            "arena_remote_agent",
            self.agent_id,
        )
        return utterance


class NoraHttpAgentFactory:
    """Create clean Nora-backed Arena sessions for repeated runs."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8000",
        agent_id: str = "nora-http",
        timeout_seconds: float = 30.0,
        headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url
        self._agent_id = agent_id
        self.timeout_seconds = timeout_seconds
        self.headers = dict(headers or {})
        self.transport = transport

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def create(self) -> NoraHttpAgentSession:
        return NoraHttpAgentSession(
            base_url=self.base_url,
            agent_id=self._agent_id,
            timeout_seconds=self.timeout_seconds,
            headers=self.headers,
            transport=self.transport,
        )
