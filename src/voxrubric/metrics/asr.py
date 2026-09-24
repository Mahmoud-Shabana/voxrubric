from __future__ import annotations

import re
import unicodedata
from statistics import fmean

from ..models import InterviewTrace, MetricResult, Rubric, Speaker
from .base import Metric


_ARABIC = re.compile(r"[\u0600-\u06FF]")
_LATIN = re.compile(r"[A-Za-z]")
_ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_NON_WORD = re.compile(r"[^\w\u0600-\u06FF]+", re.UNICODE)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _ARABIC_DIACRITICS.sub("", text)
    text = text.lower()
    text = _NON_WORD.sub(" ", text)
    return " ".join(text.split())


def _tokens(text: str) -> list[str]:
    normalized = _normalize(text)
    return normalized.split() if normalized else []


def _edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, ref_token in enumerate(reference, start=1):
        current = [row]
        for column, hyp_token in enumerate(hypothesis, start=1):
            substitution = previous[column - 1] + (
                ref_token != hyp_token
            )
            insertion = current[column - 1] + 1
            deletion = previous[column] + 1
            current.append(
                min(substitution, insertion, deletion)
            )
        previous = current
    return previous[-1]


def _contains_term(text: str, term: str) -> bool:
    normalized_text = f" {_normalize(text)} "
    normalized_term = _normalize(term)
    if not normalized_term:
        return False
    return f" {normalized_term} " in normalized_text


class AsrPreservationMetric(Metric):
    """Evaluate benchmark ASR output against manual reference transcripts."""

    name = "asr_preservation"

    def __init__(
        self,
        *,
        max_mean_wer: float = 0.2,
        min_critical_term_recall: float = 0.9,
        require_code_switch_preservation: bool = True,
    ) -> None:
        if not 0 <= max_mean_wer <= 1:
            raise ValueError("max_mean_wer must be between 0 and 1")
        if not 0 <= min_critical_term_recall <= 1:
            raise ValueError(
                "min_critical_term_recall must be between 0 and 1"
            )
        self.max_mean_wer = max_mean_wer
        self.min_critical_term_recall = min_critical_term_recall
        self.require_code_switch_preservation = (
            require_code_switch_preservation
        )

    def evaluate(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> MetricResult:
        samples: list[dict[str, object]] = []
        wers: list[float] = []
        critical_total = 0
        critical_preserved = 0
        mixed_expected = 0
        mixed_preserved = 0
        problems: list[str] = []

        for turn in trace.turns:
            if turn.speaker is not Speaker.CANDIDATE:
                continue
            reference = turn.metadata.get(
                "asr_reference_text"
            )
            if not isinstance(reference, str):
                continue

            reference_tokens = _tokens(reference)
            hypothesis_tokens = _tokens(turn.text)
            if not reference_tokens:
                problems.append(
                    f"{turn.id}: ASR reference transcript is empty"
                )
                continue

            distance = _edit_distance(
                reference_tokens,
                hypothesis_tokens,
            )
            wer = distance / len(reference_tokens)
            wers.append(wer)

            raw_terms = turn.metadata.get(
                "asr_critical_terms",
                [],
            )
            if not isinstance(raw_terms, list):
                problems.append(
                    f"{turn.id}: asr_critical_terms is not a list"
                )
                raw_terms = []

            valid_terms = [
                term
                for term in raw_terms
                if isinstance(term, str) and term.strip()
            ]
            preserved_terms = [
                term
                for term in valid_terms
                if _contains_term(turn.text, term)
            ]
            critical_total += len(valid_terms)
            critical_preserved += len(preserved_terms)

            expected_mixed = bool(
                _ARABIC.search(reference)
                and _LATIN.search(reference)
            )
            observed_mixed = bool(
                _ARABIC.search(turn.text)
                and _LATIN.search(turn.text)
            )
            if expected_mixed:
                mixed_expected += 1
                mixed_preserved += int(observed_mixed)

            samples.append(
                {
                    "turn_id": turn.id,
                    "reference": reference,
                    "hypothesis": turn.text,
                    "word_errors": distance,
                    "reference_words": len(reference_tokens),
                    "wer": round(wer, 4),
                    "critical_terms": valid_terms,
                    "preserved_critical_terms": (
                        preserved_terms
                    ),
                    "code_switch_expected": expected_mixed,
                    "code_switch_preserved": (
                        observed_mixed
                        if expected_mixed
                        else None
                    ),
                }
            )

        if not samples:
            return MetricResult(
                metric=self.name,
                summary=(
                    "Trace contains no ASR benchmark reference transcripts."
                ),
                details={"applicable": False},
            )

        mean_wer = fmean(wers) if wers else 1.0
        word_accuracy = max(0.0, 1.0 - mean_wer)
        critical_recall = (
            critical_preserved / critical_total
            if critical_total
            else 1.0
        )
        code_switch_recall = (
            mixed_preserved / mixed_expected
            if mixed_expected
            else 1.0
        )

        if mean_wer > self.max_mean_wer:
            problems.append(
                f"mean WER {mean_wer:.4f} exceeds "
                f"{self.max_mean_wer:.4f}"
            )
        if critical_recall < self.min_critical_term_recall:
            problems.append(
                f"critical-term recall {critical_recall:.4f} is below "
                f"{self.min_critical_term_recall:.4f}"
            )
        if (
            self.require_code_switch_preservation
            and code_switch_recall < 1.0
        ):
            problems.append(
                "Arabic/Latin code-switching was not preserved "
                "for every mixed-language reference"
            )

        return MetricResult(
            metric=self.name,
            value=round(word_accuracy, 4),
            unit="mean_word_accuracy",
            passed=not problems,
            summary=(
                f"{len(samples)} ASR benchmark turns: "
                f"mean WER {mean_wer:.3f}, "
                f"critical-term recall {critical_recall:.3f}."
            ),
            details={
                "applicable": True,
                "samples": samples,
                "mean_wer": round(mean_wer, 4),
                "mean_word_accuracy": round(
                    word_accuracy,
                    4,
                ),
                "critical_terms": critical_total,
                "critical_terms_preserved": (
                    critical_preserved
                ),
                "critical_term_recall": round(
                    critical_recall,
                    4,
                ),
                "mixed_language_references": mixed_expected,
                "mixed_language_preserved": mixed_preserved,
                "code_switch_preservation": round(
                    code_switch_recall,
                    4,
                ),
                "max_mean_wer": self.max_mean_wer,
                "min_critical_term_recall": (
                    self.min_critical_term_recall
                ),
                "problems": problems,
            },
        )
