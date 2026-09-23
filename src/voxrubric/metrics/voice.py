from __future__ import annotations

from collections import defaultdict

from ..models import InterviewTrace, MetricResult, Rubric, Speaker
from .base import Metric
from .latency import percentile


def _events(trace: InterviewTrace) -> list[dict]:
    events = trace.metadata.get("voice_events")
    if not isinstance(events, list):
        return []
    valid = [item for item in events if isinstance(item, dict)]
    return sorted(valid, key=lambda item: int(item.get("seq", 0)))


def _payload(event: dict) -> dict:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


class VoiceEventIntegrityMetric(Metric):
    name = "voice_event_integrity"

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        events = _events(trace)
        if not events:
            return MetricResult(
                metric=self.name,
                summary="Trace does not expose realtime voice events.",
                details={"applicable": False},
            )

        known_turns = {turn.id: turn for turn in trace.turns}
        speech_generations: set[int] = set()
        final_generations: set[int] = set()
        response_generations: set[int] = set()
        active_tts: str | None = None
        checks = 0
        valid = 0
        problems: list[str] = []
        previous_seq = -1

        for index, event in enumerate(events):
            seq = event.get("seq")
            event_type = str(event.get("type", ""))
            payload = _payload(event)
            generation = int(payload.get("generation", 0) or 0)
            turn_id = event.get("turn_id")

            checks += 1
            if not isinstance(seq, int) or seq <= previous_seq:
                problems.append(
                    f"voice_event[{index}] has non-increasing sequence {seq!r}"
                )
            else:
                valid += 1
                previous_seq = seq

            if event_type == "voice_speech_started":
                speech_generations.add(generation)

            elif event_type == "voice_transcript_partial":
                checks += 1
                if generation not in speech_generations:
                    problems.append(
                        f"partial transcript generation {generation} has no speech start"
                    )
                else:
                    valid += 1

            elif event_type == "voice_transcript_final":
                checks += 1
                if generation not in speech_generations:
                    problems.append(
                        f"final transcript generation {generation} has no speech start"
                    )
                else:
                    valid += 1
                    final_generations.add(generation)

            elif event_type == "voice_response_ready":
                checks += 1
                if generation not in final_generations:
                    problems.append(
                        f"response generation {generation} has no final transcript"
                    )
                elif turn_id and turn_id not in known_turns:
                    problems.append(
                        f"response generation {generation} references unknown turn"
                    )
                else:
                    valid += 1
                    response_generations.add(generation)

            elif event_type == "voice_tts_started":
                checks += 1
                if not turn_id or turn_id not in known_turns:
                    problems.append("TTS start references unknown interviewer turn")
                elif known_turns[turn_id].speaker is not Speaker.INTERVIEWER:
                    problems.append("TTS start references a non-interviewer turn")
                elif active_tts is not None:
                    problems.append(
                        f"TTS turn {turn_id} started while {active_tts} is still active"
                    )
                else:
                    valid += 1
                    active_tts = str(turn_id)

            elif event_type in {
                "voice_tts_completed",
                "voice_tts_cancelled",
            }:
                checks += 1
                expected = str(turn_id) if turn_id else str(payload.get("turn_id") or "")
                if active_tts is None:
                    problems.append(
                        f"{event_type} occurred without active TTS"
                    )
                elif expected and expected != active_tts:
                    problems.append(
                        f"{event_type} references {expected}, active TTS is {active_tts}"
                    )
                else:
                    valid += 1
                    active_tts = None

            elif event_type == "voice_barge_in":
                checks += 1
                if active_tts is None:
                    problems.append(
                        f"barge-in generation {generation} occurred without active TTS"
                    )
                else:
                    valid += 1

        if (
            trace.metadata.get("status") == "completed"
            and active_tts is not None
        ):
            checks += 1
            problems.append(
                f"completed trace leaves TTS turn {active_tts} active"
            )

        ratio = valid / checks if checks else 1.0
        return MetricResult(
            metric=self.name,
            value=round(ratio, 4),
            unit="valid_voice_event_ratio",
            passed=not problems,
            summary=f"{valid}/{checks} realtime voice lifecycle checks hold.",
            details={
                "events": len(events),
                "speech_generations": sorted(speech_generations),
                "response_generations": sorted(response_generations),
                "problems": problems,
            },
        )


class VoiceLatencyBreakdownMetric(Metric):
    name = "voice_latency_breakdown"

    def __init__(
        self,
        *,
        end_to_end_budget_ms: int = 4000,
    ) -> None:
        self.end_to_end_budget_ms = end_to_end_budget_ms

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        events = _events(trace)
        if not events:
            return MetricResult(
                metric=self.name,
                summary="Trace does not expose realtime voice events.",
                details={"applicable": False},
            )

        by_generation: dict[int, dict[str, int]] = defaultdict(dict)
        for event in events:
            payload = _payload(event)
            generation = int(payload.get("generation", 0) or 0)
            event_type = str(event.get("type", ""))

            if event_type == "voice_transcript_final":
                value = payload.get("speech_to_final_ms")
                if isinstance(value, int) and value >= 0:
                    by_generation[generation]["speech_to_final_ms"] = value
            elif event_type == "voice_response_ready":
                value = payload.get("final_to_response_ms")
                if isinstance(value, int) and value >= 0:
                    by_generation[generation]["final_to_response_ms"] = value
            elif event_type == "voice_tts_started":
                value = payload.get("response_to_tts_ms")
                if isinstance(value, int) and value >= 0:
                    by_generation[generation]["response_to_tts_ms"] = value

        speech = [
            values["speech_to_final_ms"]
            for values in by_generation.values()
            if "speech_to_final_ms" in values
        ]
        reasoning = [
            values["final_to_response_ms"]
            for values in by_generation.values()
            if "final_to_response_ms" in values
        ]
        tts = [
            values["response_to_tts_ms"]
            for values in by_generation.values()
            if "response_to_tts_ms" in values
        ]
        end_to_end = [
            (
                values["speech_to_final_ms"]
                + values["final_to_response_ms"]
                + values["response_to_tts_ms"]
            )
            for values in by_generation.values()
            if {
                "speech_to_final_ms",
                "final_to_response_ms",
                "response_to_tts_ms",
            } <= set(values)
        ]

        def p95(values: list[int]) -> float | None:
            return round(percentile(values, 0.95), 2) if values else None

        e2e_p95 = p95(end_to_end)
        return MetricResult(
            metric=self.name,
            value=e2e_p95,
            unit="ms_end_to_end_p95" if e2e_p95 is not None else None,
            passed=(
                e2e_p95 <= self.end_to_end_budget_ms
                if e2e_p95 is not None
                else None
            ),
            summary=(
                f"Voice end-to-end p95 is {e2e_p95:.0f} ms."
                if e2e_p95 is not None
                else "Voice events exist, but no complete end-to-end latency sample is available."
            ),
            details={
                "speech_to_final_p95_ms": p95(speech),
                "final_to_response_p95_ms": p95(reasoning),
                "response_to_tts_p95_ms": p95(tts),
                "end_to_end_p95_ms": e2e_p95,
                "complete_samples": len(end_to_end),
                "end_to_end_budget_ms": self.end_to_end_budget_ms,
            },
        )


class BargeInRecoveryMetric(Metric):
    name = "barge_in_recovery"

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        events = _events(trace)
        if not events:
            return MetricResult(
                metric=self.name,
                summary="Trace does not expose realtime voice events.",
                details={"applicable": False},
            )

        barge_generations: set[int] = set()
        cancelled_generations: set[int] = set()
        speech_generations: set[int] = set()
        final_generations: set[int] = set()
        response_generations: set[int] = set()

        for event in events:
            payload = _payload(event)
            generation = int(payload.get("generation", 0) or 0)
            event_type = str(event.get("type", ""))
            if event_type == "voice_barge_in":
                barge_generations.add(generation)
            elif event_type == "voice_tts_cancelled":
                cancelled_generations.add(generation)
            elif event_type == "voice_speech_started":
                speech_generations.add(generation)
            elif event_type == "voice_transcript_final":
                final_generations.add(generation)
            elif event_type == "voice_response_ready":
                response_generations.add(generation)

        if not barge_generations:
            return MetricResult(
                metric=self.name,
                summary="No barge-in events were recorded.",
                details={"barge_ins": 0},
            )

        recovered: list[int] = []
        failures: dict[int, list[str]] = {}
        for generation in sorted(barge_generations):
            missing: list[str] = []
            if generation not in cancelled_generations:
                missing.append("tts_cancelled")
            if generation not in speech_generations:
                missing.append("speech_started")
            if generation not in final_generations:
                missing.append("final_transcript")
            if generation not in response_generations:
                missing.append("response_ready")

            if missing:
                failures[generation] = missing
            else:
                recovered.append(generation)

        ratio = len(recovered) / len(barge_generations)
        return MetricResult(
            metric=self.name,
            value=round(ratio, 4),
            unit="recovered_barge_in_ratio",
            passed=not failures,
            summary=(
                f"{len(recovered)}/{len(barge_generations)} "
                "barge-ins recovered through a new response."
            ),
            details={
                "barge_ins": len(barge_generations),
                "recovered_generations": recovered,
                "failures": failures,
            },
        )
