"""Fine-tune MuRIL as a binary scam/legit text classifier.

Run (after backend/ml/requirements.txt is installed and ml/data/processed/
has been produced by build_dataset.py):

    python -m ml.train --train ml/data/processed/train.jsonl \
        --val ml/data/processed/val.jsonl --out ml/models/muril-scam-classifier

MuRIL (google/muril-base-cased) is used instead of an English-only model
because it is trained on Indian languages including transliterated/
code-mixed text, which is what the Hinglish portion of the dataset needs.
"""
from __future__ import annotations

import argparse

import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from ml.schema import read_jsonl

MODEL_NAME = "google/muril-base-cased"
label2id = {"legit": 0, "scam": 1}
id2label = {0: "legit", 1: "scam"}


def build_model_and_tokenizer(model_name: str = MODEL_NAME):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=2, label2id=label2id, id2label=id2label,
    )
    return model, tokenizer


def load_split(path: str):
    from datasets import Dataset

    examples = read_jsonl(path)
    return Dataset.from_dict({
        "text": [e.text for e in examples],
        "label": [label2id[e.label.value] for e in examples],
    })


def compute_metrics(eval_pred) -> dict:
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="binary", zero_division=0,
    )
    return {
        "accuracy": accuracy_score(labels, predictions),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def main() -> None:
    from transformers import Trainer, TrainingArguments

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", default="ml/data/processed/train.jsonl")
    parser.add_argument("--val", default="ml/data/processed/val.jsonl")
    parser.add_argument("--out", default="ml/models/muril-scam-classifier")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    args = parser.parse_args()

    model, tokenizer = build_model_and_tokenizer()
    train_ds = load_split(args.train)
    val_ds = load_split(args.val)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=256)

    train_ds = train_ds.map(tokenize, batched=True)
    val_ds = val_ds.map(tokenize, batched=True)

    training_args = TrainingArguments(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        processing_class=tokenizer,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model(args.out)
    tokenizer.save_pretrained(args.out)
    print(f"Saved model to {args.out}")


if __name__ == "__main__":
    main()
