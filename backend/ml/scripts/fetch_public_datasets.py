"""Download and normalize public scam/phishing/legit-text datasets into the
shared Example schema (ml/schema.py).

Sources (Hugging Face Hub dataset IDs — update here if a dataset moves):
- "sms_spam": SMS Spam Collection, ~5.5k rows, fields {"sms": str, "label": int}
  (0 = ham/legit, 1 = spam/scam).
- "zefang-liu/phishing-email-dataset": combined phishing/legit email corpus
  (built from Enron, Nazario, SpamAssassin, CEAS, Ling), fields
  {"text_combined": str, "label": int} (1 = phishing, 0 = legitimate).

Run: python -m ml.scripts.fetch_public_datasets --out data/raw/public.jsonl
"""
from __future__ import annotations

import argparse

from ml.schema import Example, Label, Register, Source, write_jsonl

SMS_SPAM_DATASET_ID = "sms_spam"
PHISHING_EMAIL_DATASET_ID = "zefang-liu/phishing-email-dataset"


def normalize_sms_spam(rows: list[dict]) -> list[Example]:
    examples = []
    for row in rows:
        text = (row.get("sms") or "").strip()
        if not text:
            continue
        label = Label.SCAM if int(row["label"]) == 1 else Label.LEGIT
        examples.append(Example(text=text, label=label, source=Source.PUBLIC,
                                 register=Register.ENGLISH))
    return examples


def normalize_phishing_email(rows: list[dict]) -> list[Example]:
    examples = []
    for row in rows:
        text = (row.get("text_combined") or "").strip()
        if not text:
            continue
        label = Label.SCAM if int(row["label"]) == 1 else Label.LEGIT
        examples.append(Example(text=text, label=label, source=Source.PUBLIC,
                                 register=Register.ENGLISH))
    return examples


def fetch_all() -> list[Example]:
    from datasets import load_dataset  # imported lazily; only needed at fetch time

    sms_rows = load_dataset(SMS_SPAM_DATASET_ID, split="train")
    email_rows = load_dataset(PHISHING_EMAIL_DATASET_ID, split="train")
    return normalize_sms_spam(list(sms_rows)) + normalize_phishing_email(list(email_rows))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/raw/public.jsonl")
    args = parser.parse_args()

    examples = fetch_all()
    write_jsonl(examples, args.out)
    print(f"Wrote {len(examples)} public examples to {args.out}")


if __name__ == "__main__":
    main()
