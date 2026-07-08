"""Generate synthetic scam/legit examples across English, Hinglish, and
mixed registers, using an LLM (GPT-OSS-120B via an OpenAI-compatible API)
seeded with real quotes from app.knowledge.scam_quotes.SCAM_QUOTE_BANK.

Run: python -m ml.scripts.generate_synthetic --out data/synthetic/synthetic.jsonl \
    --api-key $GPT_OSS_API_KEY --base-url https://api.<provider>.com/v1 \
    --model gpt-oss-120b --n-per-batch 40
"""
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from typing import Callable

from app.knowledge.scam_quotes import SCAM_QUOTE_BANK
from ml.schema import Example, Label, Register, Source, write_jsonl


@dataclass(frozen=True)
class Archetype:
    id: str
    description: str
    seed_quotes: list[str]


def _seeds_for(archetype_id: str) -> list[str]:
    return [q.text for q in SCAM_QUOTE_BANK if q.archetype == archetype_id]


ARCHETYPES: list[Archetype] = [
    Archetype("guaranteed_returns", "Promises guaranteed/fixed high returns with no risk",
               _seeds_for("guaranteed_returns")),
    Archetype("fake_regulator_approval", "Falsely implies SEBI/RBI/NSE/BSE approval or endorsement",
               _seeds_for("fake_regulator_approval")),
    Archetype("insider_tip", "Sure-shot / insider stock tips with high win-rate claims",
               _seeds_for("insider_tip")),
    Archetype("credential_harvest", "Requests OTP/PIN/PAN/login under account-threat pretext",
               _seeds_for("credential_harvest")),
    Archetype("telegram_recruit", "Recruits into a paid tips Telegram/WhatsApp group",
               _seeds_for("telegram_recruit")),
    Archetype("pump_and_dump", "Pump-and-dump exhortation on a specific stock",
               _seeds_for("pump_and_dump")),
    Archetype("crypto_scheme", "Daily-payout crypto/forex scheme with profit promises",
               _seeds_for("crypto_scheme")),
    Archetype("legit_broker_alert", "Genuine order/margin/dividend notification from a broker",
               []),
    Archetype("legit_sebi_language", "Genuine SEBI-registered-adviser disclaimer language",
               []),
    Archetype("legit_otp_message", "Genuine OTP/verification message with standard security wording",
               []),
]


def build_prompt(
    archetype: Archetype, register: Register, label: Label, n: int, seed_quotes: list[str],
) -> list[dict]:
    register_instruction = {
        Register.ENGLISH: "Write in plain English, as typed in an SMS or WhatsApp message.",
        Register.HINGLISH: (
            "Write in Hinglish — natural Hindi-English code-mixed text in Roman "
            "script, exactly as commonly typed on Indian WhatsApp/SMS "
            "(e.g. mixing words like 'aapka', 'abhi', 'ho jayega')."
        ),
        Register.MIXED: (
            "Mix English and Hinglish freely across the batch, and include some "
            "informal typos/abbreviations as seen in real forwarded messages."
        ),
    }[register]

    label_instruction = (
        f"Each message must be a realistic example of: {archetype.description}."
        if label == Label.SCAM
        else (
            f"Each message must be a GENUINE, non-scam message related to: "
            f"{archetype.description}. It must NOT be a scam, even though it may "
            f"use similar vocabulary (e.g. mentioning SEBI, returns, or KYC in a "
            f"legitimate context)."
        )
    )

    seed_block = (
        "Here are real examples of this kind of message for style reference "
        "(do not copy verbatim, write new varied ones):\n"
        + "\n".join(f"- {q}" for q in seed_quotes)
        if seed_quotes
        else ""
    )

    user_content = (
        f"{label_instruction}\n{register_instruction}\n{seed_block}\n"
        f"Generate {n} distinct messages, varied in length and phrasing. "
        f"Return them as a numbered list, one message per line, no extra commentary."
    )

    return [
        {"role": "system", "content": "You generate training data for a financial-scam detection classifier."},
        {"role": "user", "content": user_content},
    ]


_NUMBERED_LINE_RE = re.compile(r"^\s*\d+[\.\)]\s*(.+?)\s*$")


def parse_response(raw_text: str) -> list[str]:
    lines = []
    for line in raw_text.splitlines():
        match = _NUMBERED_LINE_RE.match(line)
        if match:
            lines.append(match.group(1))
    return lines


def call_gpt_oss(messages: list[dict], api_key: str, base_url: str, model: str) -> str:
    """Real network call to an OpenAI-compatible chat completions endpoint."""
    import requests

    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.9},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


class SyntheticGenerator:
    def __init__(self, chat_fn: Callable[[list[dict]], str]):
        self.chat_fn = chat_fn

    def generate_batch(
        self, archetype: Archetype, register: Register, label: Label, n: int,
    ) -> list[Example]:
        messages = build_prompt(archetype, register, label, n, archetype.seed_quotes)
        raw = self.chat_fn(messages)
        lines = parse_response(raw)
        return [
            Example(text=text, label=label, source=Source.SYNTHETIC,
                    register=register, archetype=archetype.id)
            for text in lines
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/synthetic/synthetic.jsonl")
    parser.add_argument("--api-key", default=os.environ.get("GPT_OSS_API_KEY", ""))
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", default="gpt-oss-120b")
    parser.add_argument("--n-per-batch", type=int, default=40)
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("Set --api-key or GPT_OSS_API_KEY")

    def chat_fn(messages: list[dict]) -> str:
        return call_gpt_oss(messages, args.api_key, args.base_url, args.model)

    generator = SyntheticGenerator(chat_fn=chat_fn)
    all_examples: list[Example] = []
    registers = [Register.ENGLISH, Register.HINGLISH, Register.MIXED]
    labels = [Label.SCAM, Label.LEGIT]

    for archetype in ARCHETYPES:
        for register in registers:
            for label in labels:
                batch = generator.generate_batch(archetype, register, label, args.n_per_batch)
                all_examples.extend(batch)
                print(f"{archetype.id}/{register.value}/{label.value}: +{len(batch)}")

    write_jsonl(all_examples, args.out)
    print(f"Wrote {len(all_examples)} synthetic examples to {args.out}")


if __name__ == "__main__":
    main()
