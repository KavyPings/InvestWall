from __future__ import annotations

from ml.schema import Label, Register
from ml.scripts.generate_synthetic import (
    ARCHETYPES,
    SyntheticGenerator,
    build_prompt,
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
