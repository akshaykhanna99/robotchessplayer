"""Dataset loading helpers for chess-square classifier training."""

from pathlib import Path

import cv2
import numpy as np
from tensorflow.keras import utils


def load_labeled_square_dataset(dataset_path, categories, preprocess_fn):
    """Load labeled square images and return (X, y_one_hot)."""
    dataset_path = Path(dataset_path)
    X, y = [], []

    print(f"Loading data from {dataset_path}...")
    for label, category in enumerate(categories):
        folder = dataset_path / category
        count = 0

        for img_path in sorted(folder.iterdir()):
            if img_path.suffix.lower() != ".png":
                continue

            img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
            if img is None:
                print(f"[WARNING] Skipping invalid image: {img_path}")
                continue

            X.append(preprocess_fn(img))
            y.append(label)
            count += 1

        print(f"  Loaded {count} images from {category}")

    X = np.array(X)
    y = np.array(y)
    y = utils.to_categorical(y, num_classes=len(categories))
    return X, y


def compute_balanced_class_weights(one_hot_labels, num_classes):
    """Compute inverse-frequency class weights from one-hot encoded labels."""
    y_labels = np.argmax(one_hot_labels, axis=1)
    class_counts = np.bincount(y_labels, minlength=num_classes)
    total_samples = len(y_labels)
    return {
        i: total_samples / (num_classes * class_counts[i])
        for i in range(num_classes)
        if class_counts[i] > 0
    }
