from __future__ import annotations

from uuid import uuid4

import httpx

from .models import AgentUtterance, Rubric


class NoraAdapterError(RuntimeError):
    pass


class NoraAgentSession:
    """Arena adapter for a running Nora HTTP service."""

    def __init__(
        self,
        *,
        base_url: str,
        role_description: str,
        headers: dict[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.role_description = role_description
        self.headers = dict(headers or {})
        self._owned_client = client is None
        self.client = client or httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0,
        )
        self.session_id: str | None = None
        self.job_id: str | None = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
    ) -> dict:
        response = await self.client.request(
            method,
            path,
            json=json,
            headers=self.headers or None,
        )
        if response.status_code >= 400:
            raise NoraAdapterError(
                f"Nora returned HTTP {response.status_code} for {path}: "
                f"{response.text[:500]}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise NoraAdapterError(
                f"Nora returned a non-object response for {path}"
            )
        return payload

    @staticmethod
    def _utterance(step: dict) -> AgentUtterance:
        turn = step.get("interviewer_turn")
        status = str(step.get("status", ""))

        if turn is None:
            if status == "completed":
                return AgentUtterance(
                    text="Interview completed.",
                    completes_interview=True,
                    metadata={"source": "nora-http"},
                )
            raise NoraAdapterError(
                "Nora response did not contain interviewer_turn"
            )

        metadata = turn.get("metadata") or {}
        parent_turn_id = turn.get("parent_turn_id")
        return AgentUtterance(
            text=str(turn.get("text", "")),
            rubric_tags=[
                str(item)
                for item in turn.get("competency_tags", [])
            ],
            metadata={
                **metadata,
                "source": "nora-http",
                "remote_turn_id": turn.get("id"),
                "remote_parent_turn_id": parent_turn_id,
            },
            is_followup=bool(parent_turn_id),
            completes_interview=(
                status == "completed"
                or metadata.get("question_lane") == "closing"
            ),
        )

    async def start(
        self,
        *,
        role: str,
        rubric: Rubric,
        locale: str,
    ) -> AgentUtterance:
        if self.session_id is not None:
            raise NoraAdapterError(
                "NoraAgentSession.start may only be called once"
            )

        job = await self._request(
            "POST",
            "/v1/jobs",
            json={
                "title": role,
                "description": self.role_description,
                "competencies": [
                    {
                        "id": dimension.id,
                        "description": dimension.description,
                        "weight": dimension.weight,
                    }
                    for dimension in rubric.dimensions
                ],
                "max_questions": max(
                    4,
                    len(rubric.dimensions) * 2,
                ),
                "anchor_ratio": 0.4,
            },
        )
        self.job_id = str(job["id"])

        session = await self._request(
            "POST",
            "/v1/sessions",
            json={
                "job_id": self.job_id,
                "candidate_ref": f"voxrubric-arena-{uuid4()}",
                "locale": locale,
                "consent_to_ai_interview": True,
                "consent_to_transcript": True,
                "integrity_level": "none",
            },
        )
        self.session_id = str(session["id"])

        step = await self._request(
            "POST",
            f"/v1/sessions/{self.session_id}/start",
        )
        return self._utterance(step)

    async def respond(
        self,
        candidate_text: str,
    ) -> AgentUtterance:
        if self.session_id is None:
            raise NoraAdapterError(
                "NoraAgentSession.start must run before respond"
            )
        step = await self._request(
            "POST",
            f"/v1/sessions/{self.session_id}/responses",
            json={"text": candidate_text},
        )
        return self._utterance(step)

    async def aclose(self) -> None:
        if self._owned_client:
            await self.client.aclose()


class NoraAgentFactory:
    def __init__(
        self,
        *,
        agent_id: str,
        base_url: str,
        role_description: str = "Arena-controlled interview role.",
        headers: dict[str, str] | None = None,
        client_factory=None,
    ) -> None:
        self._agent_id = agent_id
        self.base_url = base_url
        self.role_description = role_description
        self.headers = dict(headers or {})
        self.client_factory = client_factory

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def create(self) -> NoraAgentSession:
        client = (
            self.client_factory()
            if self.client_factory is not None
            else None
        )
        return NoraAgentSession(
            base_url=self.base_url,
            role_description=self.role_description,
            headers=self.headers,
            client=client,
        )
