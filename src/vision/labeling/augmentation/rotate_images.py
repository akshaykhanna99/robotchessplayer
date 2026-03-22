import cv2
import os
import numpy as np

# Path to dataset
DATASET_PATH = "chess_dataset"
CATEGORIES = ["empty", "black_piece", "white_piece"]

def get_unique_filename(folder, i, j):
    """Generates a unique filename to prevent overwriting previous images."""
    existing_files = os.listdir(folder)
    existing_indices = [
        int(f.split("_")[-1].split(".")[0]) for f in existing_files if f.startswith(f"square_{i}_{j}_")
    ]
    new_index = max(existing_indices, default=0) + 1
    return f"{folder}/square_{i}_{j}_{new_index}.png"

def rotate_and_save(image, angle, folder, i, j):
    """Rotates an image by a given angle and saves it with a unique filename."""
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)

    # Rotation matrix
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h))

    # Get unique filename for rotated image
    save_path = get_unique_filename(folder, i, j)
    cv2.imwrite(save_path, rotated)

def augment_dataset():
    """Loops through dataset, generates rotated images, and saves them with unique names."""
    for category in CATEGORIES:
        folder_path = os.path.join(DATASET_PATH, category)

        for filename in os.listdir(folder_path):
            img_path = os.path.join(folder_path, filename)

            # Extract square coordinates from filename
            try:
                parts = filename.split("_")
                i, j = int(parts[1]), int(parts[2])
            except (IndexError, ValueError):
                print(f"[WARNING] Skipping {filename}, filename format incorrect.")
                continue

            # Load the image
            image = cv2.imread(img_path)
            if image is None:
                print(f"[WARNING] Could not load {img_path}. Skipping...")
                continue

            # Generate rotated versions (90°, 180°, 270°)
            for angle in [90, 180, 270]:
                rotate_and_save(image, angle, folder_path, i, j)

            print(f"[INFO] Augmented {filename} with rotations.")

# Run dataset augmentation
augment_dataset()
print("[INFO] Dataset augmentation complete!")
