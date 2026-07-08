"""Generate synthetic scam/legit examples across English, Hinglish, and
mixed registers, using GPT-OSS-120B via AWS Bedrock, seeded with real
quotes from app.knowledge.scam_quotes.SCAM_QUOTE_BANK.

Credentials: set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION in
ml/.env (gitignored — never commit it) or your environment; boto3's
default credential chain picks them up automatically.

Run: python -m ml.scripts.generate_synthetic --out data/synthetic/synthetic.jsonl \
    --region eu-north-1 --n-per-batch 40
"""
from __future__ import annotations

import argparse
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from dotenv import load_dotenv

from app.knowledge.scam_quotes import SCAM_QUOTE_BANK
from ml.schema import Example, Label, Register, Source, read_jsonl, write_jsonl


@dataclass(frozen=True)
class Archetype:
    id: str
    description: str
    seed_quotes: list[str]
    # When set, this archetype is only ever generated under this one label —
    # used for pure hard-negative topics (e.g. a genuine broker alert) whose
    # description has no natural "scam version", so forcing both labels
    # through the generic label_instruction template would mislabel data.
    only_label: Label | None = field(default=None)


def _seeds_for(archetype_id: str) -> list[str]:
    return [q.text for q in SCAM_QUOTE_BANK if q.archetype == archetype_id]


ARCHETYPES: list[Archetype] = [
    # --- Guaranteed-return / unregistered-advisory family ---
    Archetype("guaranteed_returns", "Promises guaranteed/assured/near-certain returns that ignore market risk",
               _seeds_for("guaranteed_returns")),
    Archetype("guaranteed_returns_daily_payout", "Promises quick daily/weekly payouts regardless of market conditions",
               _seeds_for("guaranteed_returns_daily_payout")),
    # only_label=SCAM below: "unregistered"/"insider" are illegal/non-compliant
    # by definition, so there is no natural "genuine, non-scam" counterpart —
    # a legit registered-advisor equivalent already exists as
    # legit_sebi_language / legit_research_disclaimer.
    Archetype("unregistered_advisor_paid_tips", "An unregistered advisor selling paid stock tips/signals without SEBI registration",
               _seeds_for("unregistered_advisor_paid_tips"), only_label=Label.SCAM),
    Archetype("account_handling_scam", "Offers to 'handle'/manage the victim's trading account directly in exchange for a guaranteed profit share",
               _seeds_for("account_handling_scam")),
    Archetype("complex_strategy_obfuscation", "Credits success to a vaguely-described 'highly complex' proprietary strategy while refusing to explain the risk",
               _seeds_for("complex_strategy_obfuscation")),
    Archetype("insider_tip", "Sure-shot / insider stock tips with high win-rate claims",
               _seeds_for("insider_tip"), only_label=Label.SCAM),
    # --- Fake regulator / institutional impersonation family ---
    Archetype("fake_regulator_approval", "Falsely implies SEBI/RBI/NSE/BSE approval or endorsement",
               _seeds_for("fake_regulator_approval")),
    Archetype("fake_sebi_registration_number", "Cites a fabricated or misused SEBI registration number to appear legitimate",
               _seeds_for("fake_sebi_registration_number")),
    Archetype("impersonating_registered_entity", "Impersonates a real SEBI-registered brokerage/advisory's name or branding without affiliation",
               _seeds_for("impersonating_registered_entity")),
    Archetype("sebi_vs_scam_countercampaign_spoof", "Falsely claims the message itself is part of an official SEBI investor-protection or verification initiative",
               _seeds_for("sebi_vs_scam_countercampaign_spoof")),
    # --- Deepfake / AI-generated endorsement family ---
    Archetype("deepfake_ceo_endorsement", "A fabricated video/audio 'endorsement' by a real listed company's CEO or exchange official promoting a stock or trading app",
               _seeds_for("deepfake_ceo_endorsement")),
    Archetype("deepfake_market_expert", "A fabricated video/audio of a well-known market analyst/expert giving specific stock picks they never made",
               _seeds_for("deepfake_market_expert")),
    Archetype("fake_news_screenshot", "A fabricated or doctored news-article screenshot claiming a stock or scheme was endorsed by a reputable outlet or regulator",
               _seeds_for("fake_news_screenshot")),
    # --- Social-media / messaging-group recruitment family ---
    Archetype("telegram_recruit", "Recruits into a paid tips Telegram/WhatsApp group with false scarcity",
               _seeds_for("telegram_recruit")),
    Archetype("vip_group_free_trial", "Offers a 'VIP' trading tips group with a free trial period before a paid upsell",
               _seeds_for("vip_group_free_trial")),
    Archetype("social_media_guru_dm", "An unsolicited DM from a self-styled trading 'guru' on Instagram/X/Facebook offering personal mentorship",
               _seeds_for("social_media_guru_dm")),
    Archetype("fake_trading_course", "Advertises a 'free trading course' that funnels students into a paid signals group or fake app",
               _seeds_for("fake_trading_course")),
    Archetype("private_link_app_install", "Instructs the victim to install a trading app via a private link outside the Play Store/App Store",
               _seeds_for("private_link_app_install")),
    # --- Task-based / part-time-job investment scam family ---
    Archetype("task_scam_bait", "A part-time work-from-home offer (e.g. rating videos, liking posts) promising small daily payouts, targeting students/homemakers",
               _seeds_for("task_scam_bait")),
    Archetype("task_scam_trust_building", "Pays out small real amounts for simple tasks to build trust before introducing an 'investment task'",
               _seeds_for("task_scam_trust_building")),
    # only_label=SCAM: the pay-to-play "deposit for a bigger return" mechanic
    # IS the fraud — there's no legitimate business model matching this
    # description, so a "genuine, non-scam" version is a contradiction.
    Archetype("task_scam_investment_escalation", "An 'investment task' requiring an upfront deposit with a promised larger return, escalating in amount over time",
               _seeds_for("task_scam_investment_escalation"), only_label=Label.SCAM),
    Archetype("task_scam_fake_earnings_screenshot", "Shares fabricated screenshots of other members' large earnings to pressure the victim into depositing more",
               _seeds_for("task_scam_fake_earnings_screenshot")),
    # --- Fake trading app / platform family ---
    # only_label=SCAM: description bakes in "fake"/"fabricated", making a
    # "genuine, non-scam" version of it self-contradictory (confirmed by
    # 100% failure rate in the 2026-07-08 generation run before this fix).
    Archetype("fake_trading_app_generic", "Promotes a fake trading/investment app installed outside official app stores, showing fabricated profit dashboards",
               _seeds_for("fake_trading_app_generic"), only_label=Label.SCAM),
    Archetype("fake_app_withdrawal_block", "The fake app blocks withdrawal of funds/profits unless the victim deposits an additional 'fee', 'tax', or 'unlock' amount",
               _seeds_for("fake_app_withdrawal_block")),
    Archetype("fake_broker_website_clone", "A cloned website visually mimicking a real broker's login page to harvest credentials",
               _seeds_for("fake_broker_website_clone")),
    # --- IPO / dabba / algo-trading family ---
    Archetype("fake_ipo_allotment", "Promises guaranteed or exclusive IPO share allotment in exchange for an upfront payment beyond official retail limits",
               _seeds_for("fake_ipo_allotment")),
    # only_label=SCAM: "dabba" trading is illegal by definition (confirmed
    # 100% failure rate before this fix — there's no legitimate version).
    Archetype("dabba_trading_recruit", "Recruits into illegal off-exchange 'dabba' trading with no real regulatory protection or settlement",
               _seeds_for("dabba_trading_recruit"), only_label=Label.SCAM),
    Archetype("fake_algo_trading_bot", "Sells an 'automated algo-trading bot' claiming consistent automated profits with no manual effort",
               _seeds_for("fake_algo_trading_bot")),
    # --- Credential harvesting / account-threat family ---
    Archetype("credential_harvest", "Requests OTP/PIN/PAN/login under account-threat pretext",
               _seeds_for("credential_harvest")),
    Archetype("fake_kyc_update_sms", "SMS claiming KYC/demat details are outdated and must be 'updated' via a link within a short deadline or the account will be frozen",
               _seeds_for("fake_kyc_update_sms")),
    Archetype("fake_account_freeze_notice", "Claims the trading/demat account has already been frozen/suspended and must be 'reactivated' by providing credentials",
               _seeds_for("fake_account_freeze_notice")),
    Archetype("fake_broker_support_call", "A caller impersonating broker/exchange support requesting screen-sharing or remote-access app installation",
               _seeds_for("fake_broker_support_call")),
    # --- Digital-arrest / law-enforcement impersonation family ---
    # only_label=SCAM: impersonating police/CBI to extort money is inherently
    # illegal — there is no "genuine" version of that act to write.
    Archetype("digital_arrest_intro", "Impersonates police/CBI/customs claiming the victim's bank or demat account is linked to money laundering or a criminal case",
               _seeds_for("digital_arrest_intro"), only_label=Label.SCAM),
    Archetype("digital_arrest_video_hold", "Uses a sustained video-call 'custody' and threats of arrest to pressure a money transfer to 'clear' the victim's name",
               _seeds_for("digital_arrest_video_hold"), only_label=Label.SCAM),
    Archetype("fake_courier_customs_lead_in", "A fake courier/customs notice about an illegal parcel that escalates into a law-enforcement impersonation call demanding payment",
               _seeds_for("fake_courier_customs_lead_in")),
    # --- Pump-and-dump / market-manipulation family ---
    # only_label=SCAM: coordinated price manipulation is inherently illegal
    # market conduct with no legitimate counterpart.
    Archetype("pump_and_dump", "Pump-and-dump exhortation on a specific stock",
               _seeds_for("pump_and_dump"), only_label=Label.SCAM),
    Archetype("coordinated_telegram_manipulation", "A Telegram/WhatsApp channel coordinating simultaneous buying of a low-liquidity stock ahead of a price target, then dumping",
               _seeds_for("coordinated_telegram_manipulation"), only_label=Label.SCAM),
    Archetype("penny_stock_hot_tip", "Unsolicited 'hot tip' on an illiquid penny/small-cap stock claiming imminent multi-fold price movement",
               _seeds_for("penny_stock_hot_tip")),
    # --- Crypto / forex family ---
    Archetype("crypto_scheme", "Daily-payout crypto/forex scheme with profit promises",
               _seeds_for("crypto_scheme")),
    # only_label=SCAM: the grooming-into-fraud tactic itself is the scam;
    # there's no natural "genuine" counterpart to this description.
    Archetype("crypto_pig_butchering", "Builds a long-term personal/romantic relationship online before introducing a fraudulent crypto investment platform",
               _seeds_for("crypto_pig_butchering"), only_label=Label.SCAM),
    Archetype("forex_signal_seller", "Sells paid forex/binary-options 'signals' claiming a near-100% win rate",
               _seeds_for("forex_signal_seller")),
    # --- Legit-only hard negatives (no natural scam framing; generate LEGIT only) ---
    Archetype("legit_broker_alert", "Genuine order/margin/dividend notification from a broker",
               [], only_label=Label.LEGIT),
    Archetype("legit_sebi_language", "Genuine SEBI-registered-adviser disclaimer language",
               [], only_label=Label.LEGIT),
    Archetype("legit_otp_message", "Genuine OTP/verification message with standard security wording",
               [], only_label=Label.LEGIT),
    Archetype("legit_kyc_reminder", "Genuine periodic KYC update reminder from a broker/exchange with no threat language and no external payment",
               [], only_label=Label.LEGIT),
    Archetype("legit_ipo_allotment_notice", "Genuine IPO allotment/refund status notification from a registrar via official channels",
               [], only_label=Label.LEGIT),
    Archetype("legit_research_disclaimer", "Genuine SEBI-registered research-analyst report disclaimer noting risks and no guaranteed returns",
               [], only_label=Label.LEGIT),
]


def iter_generation_jobs(
    archetypes: list[Archetype], registers: list[Register], labels: list[Label],
) -> Iterator[tuple[Archetype, Register, Label]]:
    """Yields (archetype, register, label) jobs, skipping labels that don't
    match an archetype's only_label restriction (see Archetype docstring)."""
    for archetype in archetypes:
        for register in registers:
            for label in labels:
                if archetype.only_label is not None and archetype.only_label != label:
                    continue
                yield archetype, register, label


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


def call_bedrock_gpt_oss(
    messages: list[dict],
    region: str,
    model: str = "openai.gpt-oss-120b",
    project: str | None = None,
    client=None,
) -> str:
    """Real network call to GPT-OSS-120B via AWS Bedrock's bedrock-mantle
    endpoint (AWS's recommended endpoint for this model), using the
    OpenAI-compatible Chat Completions interface.

    Credentials are never passed explicitly here — aws_bedrock_token_generator
    uses boto3's default credential chain (AWS_ACCESS_KEY_ID /
    AWS_SECRET_ACCESS_KEY / AWS_REGION from the environment) to mint a
    short-lived bearer token, so nothing secret needs to live in this
    codebase.
    """
    if client is None:
        from aws_bedrock_token_generator import provide_token
        from openai import OpenAI

        client = OpenAI(
            api_key=provide_token(region=region),
            base_url=f"https://bedrock-mantle.{region}.api.aws/v1",
            project=project,
        )

    response = client.chat.completions.create(model=model, messages=messages, temperature=0.9)
    return response.choices[0].message.content


class SyntheticGenerator:
    def __init__(self, chat_fn: Callable[[list[dict]], str]):
        self.chat_fn = chat_fn

    def generate_batch(
        self, archetype: Archetype, register: Register, label: Label, n: int,
        max_retries: int = 2, min_fraction: float = 0.8,
        backoff_seconds: float = 2.0, sleep_fn: Callable[[float], None] = time.sleep,
    ) -> list[Example]:
        """Requests n examples; if the model returns fewer than
        min_fraction * n usable lines (occasional format non-compliance or
        an empty/refusal-shaped response — see the 2026-07-08 backend/ml
        run where ~44% of batches silently came back empty), retries up to
        max_retries times and merges unique lines across attempts rather
        than silently accepting an underfilled or empty batch. Sleeps
        backoff_seconds between retries (not after the final attempt) in
        case the underfill was caused by transient rate-limiting."""
        messages = build_prompt(archetype, register, label, n, archetype.seed_quotes)
        threshold = n * min_fraction
        seen: dict[str, None] = {}

        for attempt in range(max_retries + 1):
            raw = self.chat_fn(messages)
            for line in parse_response(raw):
                seen.setdefault(line, None)
            if len(seen) >= threshold or attempt == max_retries:
                break
            sleep_fn(backoff_seconds)

        return [
            Example(text=text, label=label, source=Source.SYNTHETIC,
                    register=register, archetype=archetype.id)
            for text in seen
        ]


def existing_batch_counts(path: str) -> dict[tuple[str, str, str], int]:
    """Counts already-generated examples per (archetype, register, label),
    read from a prior run's output file — empty if the file doesn't exist
    yet. Used to resume a generation run without redoing completed batches."""
    if not os.path.exists(path):
        return {}
    examples = read_jsonl(path)
    return dict(Counter((e.archetype, e.register.value, e.label.value) for e in examples))


def filter_incomplete_jobs(
    jobs: list[tuple[Archetype, Register, Label]],
    counts: dict[tuple[str, str, str], int],
    n_per_batch: int,
    min_fraction: float = 0.8,
) -> list[tuple[Archetype, Register, Label]]:
    """Keeps only jobs whose existing example count is below the
    min_fraction * n_per_batch threshold — i.e. skips batches a prior run
    already filled well enough."""
    threshold = n_per_batch * min_fraction
    return [
        (archetype, register, label)
        for archetype, register, label in jobs
        if counts.get((archetype.id, register.value, label.value), 0) < threshold
    ]


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/synthetic/synthetic.jsonl")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "")))
    parser.add_argument("--model", default="openai.gpt-oss-120b")
    parser.add_argument("--project", default=os.environ.get("BEDROCK_PROJECT_ID"))
    parser.add_argument("--n-per-batch", type=int, default=40)
    args = parser.parse_args()

    if not args.region:
        raise SystemExit("Set --region or AWS_REGION/AWS_DEFAULT_REGION")

    def chat_fn(messages: list[dict]) -> str:
        return call_bedrock_gpt_oss(messages, args.region, args.model, args.project)

    generator = SyntheticGenerator(chat_fn=chat_fn)
    registers = [Register.ENGLISH, Register.HINGLISH, Register.MIXED]
    labels = [Label.SCAM, Label.LEGIT]

    existing = read_jsonl(args.out) if os.path.exists(args.out) else []
    counts = existing_batch_counts(args.out)
    all_jobs = list(iter_generation_jobs(ARCHETYPES, registers, labels))
    remaining_jobs = filter_incomplete_jobs(all_jobs, counts, args.n_per_batch)
    print(f"{len(all_jobs) - len(remaining_jobs)}/{len(all_jobs)} batches already "
          f"filled in {args.out}; generating {len(remaining_jobs)} remaining")

    new_examples: list[Example] = []
    for archetype, register, label in remaining_jobs:
        batch = generator.generate_batch(archetype, register, label, args.n_per_batch)
        new_examples.extend(batch)
        print(f"{archetype.id}/{register.value}/{label.value}: +{len(batch)}")

    all_examples = existing + new_examples
    write_jsonl(all_examples, args.out)
    print(f"Wrote {len(all_examples)} synthetic examples to {args.out} "
          f"({len(new_examples)} newly generated)")


if __name__ == "__main__":
    main()
