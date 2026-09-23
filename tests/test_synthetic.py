from voxrubric.synthetic import AnswerStyle, CandidatePersona, SyntheticCandidate


def test_code_switched_persona_is_deterministic():
    persona = CandidatePersona(
        id="arabic-senior",
        skill_level=4,
        answer_style=AnswerStyle.CODE_SWITCHED,
        known_topics=["debugging"],
    )
    candidate = SyntheticCandidate(persona)
    a = candidate.answer("How did you debug it?", "debugging")
    b = candidate.answer("How did you debug it?", "debugging")
    assert a == b
    assert "metrics" in a
    assert any("\u0600" <= ch <= "\u06ff" for ch in a)


def test_weak_persona_admits_limited_exposure():
    persona = CandidatePersona(
        id="junior",
        skill_level=2,
        weak_topics=["distributed_systems"],
    )
    answer = SyntheticCandidate(persona).answer("Tell me about consensus.", "distributed_systems")
    assert "limited" in answer.lower()
