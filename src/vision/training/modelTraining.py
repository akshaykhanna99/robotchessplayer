import argparse
from pathlib import Path
import numpy as np
from sklearn.model_selection import train_test_split
from src.vision.models.builders import get_model_builder
from src.vision.preprocessing import get_preprocessor
from src.vision.training.dataset_loader import (
    compute_balanced_class_weights,
    load_labeled_square_dataset,
)

CATEGORIES = ["empty", "black_piece", "white_piece"]

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_PATH = "chess_dataset_v1"
DEFAULT_VARIANT = "enhanced_v7"
DEFAULT_OUTPUTS = {
    "baseline": "models/chess_piece_classifier_baseline.h5",
    "enhanced_v7": "models/chess_piece_classifier_v7.h5",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Train chess-square vision classifier.")
    parser.add_argument(
        "--variant",
        default=DEFAULT_VARIANT,
        choices=sorted(DEFAULT_OUTPUTS.keys()),
        help="Model/preprocessing variant to train.",
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET_PATH,
        help="Path to labeled dataset root (contains class subfolders).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output model path (.h5). Defaults to a variant-specific path under models/.",
    )
    parser.add_argument("--epochs", type=int, default=15, help="Training epochs.")
    parser.add_argument("--batch-size", type=int, default=32, help="Training batch size.")
    return parser.parse_args()


def main():
    args = parse_args()
    preprocess_fn = get_preprocessor(args.variant)
    build_model = get_model_builder(args.variant)

    X, y = load_labeled_square_dataset(
        args.dataset,
        CATEGORIES,
        lambda img: preprocess_fn(img, add_batch_dim=False),
    )

    print(f"\nTotal images loaded: {len(X)}")
    print(f"Image shape: {X[0].shape}")
    print(f"Training variant: {args.variant}")

    # Split into training (80%) and validation (20%) sets.
    # Stratify ensures each class is proportionally represented in both sets.
    y_labels = np.argmax(y, axis=1)  # Convert one-hot back to labels for stratification
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y_labels
    )

    print(f"\nTraining samples: {len(X_train)}, Validation samples: {len(X_val)}")

    # Calculate class weights to handle imbalance.
    class_weights = compute_balanced_class_weights(y_train, len(CATEGORIES))

    print(f"\nClass weights (to balance training):")
    for i, category in enumerate(CATEGORIES):
        print(f"  {category}: {class_weights[i]:.2f}")

    # Build model for 5-channel input (BGR + Edges + Gradients).
    print("\nBuilding model...")
    model_enhanced = build_model()

    print("\n" + "="*60)
    print("TRAINING STARTED")
    print("="*60)

    # Train the model with class weights.
    history = model_enhanced.fit(
        X_train, y_train,
        epochs=args.epochs,
        validation_data=(X_val, y_val),
        batch_size=args.batch_size,
        class_weight=class_weights,  # Apply class weights
        verbose=1,
    )

    # Save the trained model.
    output_rel = args.output or DEFAULT_OUTPUTS[args.variant]
    MODEL_OUTPUT_PATH = PROJECT_ROOT / output_rel
    MODEL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    model_enhanced.save(MODEL_OUTPUT_PATH)
    print(f"\n[INFO] Model saved as {MODEL_OUTPUT_PATH}")

    # Print training results.
    final_acc = history.history['accuracy'][-1]
    val_acc = history.history['val_accuracy'][-1]
    print("\n" + "="*60)
    print("TRAINING COMPLETE")
    print("="*60)
    print(f"Final Training Accuracy: {final_acc:.4f}")
    print(f"Final Validation Accuracy: {val_acc:.4f}")

    # Test predictions on validation set.
    print("\nTesting on validation samples...")
    y_pred = model_enhanced.predict(X_val[:20], verbose=0)
    y_true = np.argmax(y_val[:20], axis=1)
    y_pred_classes = np.argmax(y_pred, axis=1)

    print("\nSample predictions:")
    for i in range(20):
        true_label = CATEGORIES[y_true[i]]
        pred_label = CATEGORIES[y_pred_classes[i]]
        confidence = y_pred[i][y_pred_classes[i]] * 100
        status = "✓" if y_true[i] == y_pred_classes[i] else "✗"
        print(
            f"  {status} True: {true_label:12s} | Predicted: {pred_label:12s} | Confidence: {confidence:.1f}%"
        )

    print("\n" + "="*60)
    print("IMPORTANT:")
    print("  Ensure runtime inference uses the same preprocessing/model variant.")
    print("="*60)


if __name__ == "__main__":
    main()
