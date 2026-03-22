"""Shared preprocessing functions for chess-square vision models."""

import cv2
import numpy as np

IMG_SIZE = 64


def preprocess_square_baseline(square_img, img_size=IMG_SIZE, add_batch_dim=True):
    """Resize + normalize a square crop for baseline 3-channel models."""
    square_img = cv2.resize(square_img, (img_size, img_size))
    tensor = square_img.astype(np.float32) / 255.0
    if add_batch_dim:
        tensor = np.expand_dims(tensor, axis=0)
    return tensor


def preprocess_square_enhanced_v7(square_img, img_size=IMG_SIZE, add_batch_dim=True):
    """Build 5-channel tensor: BGR + center-masked edges + gradient magnitude."""
    square_img = cv2.resize(square_img, (img_size, img_size))

    bgr = square_img.astype(np.float32) / 255.0
    gray = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray, 100, 200).astype(np.float32) / 255.0

    # Ignore board-line-heavy borders and focus on the center of each square.
    mask = np.ones_like(edges, dtype=np.float32)
    border = int(img_size * 0.15)
    mask[:border, :] = 0
    mask[-border:, :] = 0
    mask[:, :border] = 0
    mask[:, -border:] = 0
    edges = np.expand_dims(edges * mask, axis=-1)

    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_mag = np.sqrt(sobelx**2 + sobely**2)
    max_val = gradient_mag.max()
    if max_val > 0:
        gradient_mag = (gradient_mag / max_val).astype(np.float32)
    else:
        gradient_mag = gradient_mag.astype(np.float32)
    gradient_mag = np.expand_dims(gradient_mag, axis=-1)

    tensor = np.concatenate([bgr, edges, gradient_mag], axis=-1)
    if add_batch_dim:
        tensor = np.expand_dims(tensor, axis=0)
    return tensor


PREPROCESSORS = {
    "baseline": preprocess_square_baseline,
    "enhanced_v7": preprocess_square_enhanced_v7,
}


def get_preprocessor(variant):
    """Return a preprocessing function by variant name."""
    try:
        return PREPROCESSORS[variant]
    except KeyError as exc:
        valid = ", ".join(sorted(PREPROCESSORS))
        raise ValueError(f"Unknown preprocessing variant '{variant}'. Valid options: {valid}") from exc
