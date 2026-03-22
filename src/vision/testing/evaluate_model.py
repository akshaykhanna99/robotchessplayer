"""Evaluate a trained chess-square classifier on a labeled dataset."""

import argparse
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split
from tensorflow.keras import models

from src.vision.preprocessing import get_preprocessor
from src.vision.training.dataset_loader import load_labeled_square_dataset


CATEGORIES = ["empty", "black_piece", "white_piece"]
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate a trained chess-square classifier.")
    parser.add_argument(
        "--model",
        default="models/chess_piece_classifier_v7.h5",
        help="Path to saved Keras .h5 model (repo-relative or absolute).",
    )
    parser.add_argument(
        "--variant",
        default="enhanced_v7",
        choices=["baseline", "enhanced_v7"],
        help="Preprocessing variant expected by the model.",
    )
    parser.add_argument(
        "--dataset",
        default="chess_dataset_v1",
        help="Path to labeled dataset root (contains class subfolders).",
    )
    parser.add_argument(
        "--split",
        type=float,
        default=0.2,
        help="Validation split fraction used for holdout evaluation.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for train/validation split.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=20,
        help="Number of sample predictions to print.",
    )
    return parser.parse_args()


def resolve_path(path_str):
    path = Path(path_str)
    return path if path.is_absolute() else PROJECT_ROOT / path


def print_confusion_matrix(y_true, y_pred):
    matrix = np.zeros((len(CATEGORIES), len(CATEGORIES)), dtype=int)
    for t, p in zip(y_true, y_pred):
        matrix[t, p] += 1

    print("\nConfusion Matrix (rows=true, cols=pred):")
    header = " " * 16 + " ".join(f"{c[:5]:>8}" for c in CATEGORIES)
    print(header)
    for i, category in enumerate(CATEGORIES):
        row = " ".join(f"{matrix[i, j]:8d}" for j in range(len(CATEGORIES)))
        print(f"{category[:14]:>14} {row}")


def main():
    args = parse_args()
    model_path = resolve_path(args.model)
    dataset_path = resolve_path(args.dataset)

    preprocess_fn = get_preprocessor(args.variant)
    X, y = load_labeled_square_dataset(
        dataset_path,
        CATEGORIES,
        lambda img: preprocess_fn(img, add_batch_dim=False),
    )

    y_labels = np.argmax(y, axis=1)
    _, X_val, _, y_val = train_test_split(
        X, y, test_size=args.split, random_state=args.seed, stratify=y_labels
    )

    print("\n" + "=" * 60)
    print("MODEL EVALUATION")
    print("=" * 60)
    print(f"Model:   {model_path}")
    print(f"Variant: {args.variant}")
    print(f"Dataset: {dataset_path}")
    print(f"Val set: {len(X_val)} samples")

    model = models.load_model(model_path)
    loss, acc = model.evaluate(X_val, y_val, verbose=0)
    print(f"\nValidation Loss:     {loss:.4f}")
    print(f"Validation Accuracy: {acc:.4f}")

    y_pred_probs = model.predict(X_val, verbose=0)
    y_pred = np.argmax(y_pred_probs, axis=1)
    y_true = np.argmax(y_val, axis=1)

    print_confusion_matrix(y_true, y_pred)

    sample_count = min(args.samples, len(X_val))
    if sample_count > 0:
        print("\nSample predictions:")
        for i in range(sample_count):
            pred_idx = y_pred[i]
            true_idx = y_true[i]
            confidence = y_pred_probs[i][pred_idx] * 100
            status = "OK" if pred_idx == true_idx else "X"
            print(
                f"  {status} true={CATEGORIES[true_idx]:12s} pred={CATEGORIES[pred_idx]:12s} "
                f"conf={confidence:5.1f}%"
            )


if __name__ == "__main__":
    main()
