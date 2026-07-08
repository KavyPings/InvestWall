from __future__ import annotations

import os
import tempfile

from ml.schema import Example, Label, Register, Source, write_jsonl
from ml.scripts.generate_synthetic import (
    ARCHETYPES,
    Archetype,
    SyntheticGenerator,
    build_prompt,
    call_bedrock_gpt_oss,
    existing_batch_counts,
    filter_incomplete_jobs,
    iter_generation_jobs,
    parse_response,
)


def test_build_prompt_includes_register_and_seed_quotes():
    archetype = ARCHETYPES[0]
    messages = build_prompt(
        archetype, Register.HINGLISH, Label.SCAM, n=5,
        seed_quotes=["Guaranteed 40% returns every month."],
    )
    joined = " ".join(m["content"] for m in messages)
    assert "Hinglish" in joined
    assert "Guaranteed 40% returns every month." in joined
    assert "5" in joined


def test_parse_response_splits_numbered_list():
    raw = "1. First scam message here\n2. Second scam message here\n3. Third one"
    lines = parse_response(raw)
    assert lines == [
        "First scam message here",
        "Second scam message here",
        "Third one",
    ]


def test_parse_response_ignores_blank_lines():
    raw = "1. Only one\n\n\n"
    assert parse_response(raw) == ["Only one"]


def test_generate_batch_uses_injected_chat_fn():
    archetype = ARCHETYPES[0]
    calls = []

    def fake_chat_fn(messages: list[dict]) -> str:
        calls.append(messages)
        return "1. Example one\n2. Example two"

    gen = SyntheticGenerator(chat_fn=fake_chat_fn)
    examples = gen.generate_batch(archetype, Register.ENGLISH, Label.SCAM, n=2)

    assert len(calls) == 1
    assert len(examples) == 2
    assert examples[0].label == Label.SCAM
    assert examples[0].register == Register.ENGLISH
    assert examples[0].archetype == archetype.id
    assert examples[0].text == "Example one"


def test_iter_generation_jobs_skips_mismatched_only_label():
    scam_archetype = Archetype("a", "desc", [])
    legit_only_archetype = Archetype("b", "desc", [], only_label=Label.LEGIT)

    jobs = list(iter_generation_jobs(
        [scam_archetype, legit_only_archetype],
        [Register.ENGLISH], [Label.SCAM, Label.LEGIT],
    ))

    assert (scam_archetype, Register.ENGLISH, Label.SCAM) in jobs
    assert (scam_archetype, Register.ENGLISH, Label.LEGIT) in jobs
    assert (legit_only_archetype, Register.ENGLISH, Label.LEGIT) in jobs
    assert (legit_only_archetype, Register.ENGLISH, Label.SCAM) not in jobs


def test_archetypes_has_at_least_40_entries_with_unique_ids():
    assert len(ARCHETYPES) >= 40
    ids = [a.id for a in ARCHETYPES]
    assert len(ids) == len(set(ids))


def test_call_bedrock_gpt_oss_uses_injected_client():
    captured = {}

    class _FakeMessage:
        content = "1. Example scam message"

    class _FakeChoice:
        message = _FakeMessage()

    class _FakeResponse:
        choices = [_FakeChoice()]

    class _FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _FakeResponse()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeClient:
        chat = _FakeChat()

    result = call_bedrock_gpt_oss(
        messages=[
            {"role": "system", "content": "sys prompt"},
            {"role": "user", "content": "user prompt"},
        ],
        region="eu-north-1",
        client=_FakeClient(),
    )

    assert result == "1. Example scam message"
    assert captured["model"] == "openai.gpt-oss-120b"
    assert captured["messages"] == [
        {"role": "system", "content": "sys prompt"},
        {"role": "user", "content": "user prompt"},
    ]


def test_generate_batch_retries_when_underfilled():
    archetype = ARCHETYPES[0]
    call_count = 0

    def flaky_chat_fn(messages: list[dict]) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "Sorry, I can't help with that request."  # 0 parsed lines
        return "\n".join(f"{i}. Message {i}" for i in range(1, 11))  # 10 lines

    gen = SyntheticGenerator(chat_fn=flaky_chat_fn)
    examples = gen.generate_batch(archetype, Register.ENGLISH, Label.SCAM, n=10, max_retries=2,
                                   sleep_fn=lambda _: None)

    assert call_count == 2
    assert len(examples) == 10


def test_generate_batch_sleeps_between_retries_but_not_after_last_attempt():
    archetype = ARCHETYPES[0]
    sleep_calls = []

    def always_empty_chat_fn(messages: list[dict]) -> str:
        return "No usable list here."

    gen = SyntheticGenerator(chat_fn=always_empty_chat_fn)
    gen.generate_batch(
        archetype, Register.ENGLISH, Label.SCAM, n=10, max_retries=2,
        sleep_fn=sleep_calls.append,
    )

    # 3 total attempts (initial + 2 retries) means 2 sleeps between them,
    # none after the final attempt.
    assert len(sleep_calls) == 2


def test_generate_batch_gives_up_after_max_retries():
    archetype = ARCHETYPES[0]
    call_count = 0

    def always_empty_chat_fn(messages: list[dict]) -> str:
        nonlocal call_count
        call_count += 1
        return "No usable list here."

    gen = SyntheticGenerator(chat_fn=always_empty_chat_fn)
    examples = gen.generate_batch(archetype, Register.ENGLISH, Label.SCAM, n=10, max_retries=2,
                                   sleep_fn=lambda _: None)

    assert call_count == 3  # initial attempt + 2 retries
    assert examples == []


def test_generate_batch_merges_unique_lines_across_retries():
    archetype = ARCHETYPES[0]
    call_count = 0

    def partial_chat_fn(messages: list[dict]) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "\n".join(f"{i}. Message {i}" for i in range(1, 5))  # 4 lines
        return "\n".join(f"{i}. Message {i}" for i in range(1, 11))  # 10 lines, overlapping

    gen = SyntheticGenerator(chat_fn=partial_chat_fn)
    examples = gen.generate_batch(archetype, Register.ENGLISH, Label.SCAM, n=10, max_retries=2,
                                   sleep_fn=lambda _: None)

    assert call_count == 2
    # merged unique texts across both attempts: "Message 1".."Message 10" (10 distinct)
    assert len(examples) == 10
    assert {e.text for e in examples} == {f"Message {i}" for i in range(1, 11)}


def test_existing_batch_counts_reads_jsonl_file():
    examples = [
        Example(text=f"scam {i}", label=Label.SCAM, source=Source.SYNTHETIC,
                register=Register.ENGLISH, archetype="guaranteed_returns")
        for i in range(3)
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "out.jsonl")
        write_jsonl(examples, path)
        counts = existing_batch_counts(path)

    assert counts[("guaranteed_returns", "english", "scam")] == 3


def test_existing_batch_counts_returns_empty_for_missing_file():
    counts = existing_batch_counts("does/not/exist.jsonl")
    assert counts == {}


def test_filter_incomplete_jobs_skips_satisfied_batches():
    a1 = Archetype("a1", "desc", [])
    a2 = Archetype("a2", "desc", [])
    jobs = [(a1, Register.ENGLISH, Label.SCAM), (a2, Register.ENGLISH, Label.SCAM)]
    counts = {("a1", "english", "scam"): 120}  # a1 fully satisfied, a2 has none

    remaining = filter_incomplete_jobs(jobs, counts, n_per_batch=120)

    assert remaining == [(a2, Register.ENGLISH, Label.SCAM)]


def test_filter_incomplete_jobs_keeps_underfilled_batches():
    a1 = Archetype("a1", "desc", [])
    jobs = [(a1, Register.ENGLISH, Label.SCAM)]
    counts = {("a1", "english", "scam"): 5}  # far short of 120, still incomplete

    remaining = filter_incomplete_jobs(jobs, counts, n_per_batch=120)

    assert remaining == [(a1, Register.ENGLISH, Label.SCAM)]
