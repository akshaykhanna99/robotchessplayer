import os
import re

# Dataset path
DATASET_PATH = "chess_dataset"
CATEGORIES = ["empty", "black_piece", "white_piece"]

def get_next_index(folder, i, j):
    """Finds the next available index for a file in the given folder."""
    existing_files = os.listdir(folder)
    existing_indices = [
        int(re.search(r'square_\d+_\d+_(\d+)\.png', f).group(1))
        for f in existing_files if re.match(rf'square_{i}_{j}_\d+\.png', f)
    ]
    new_index = max(existing_indices, default=0) + 1
    return new_index

def rename_augmented_files():
    """Renames files with _rotXX suffix to standard get_unique_filename format."""
    for category in CATEGORIES:
        folder_path = os.path.join(DATASET_PATH, category)

        for filename in os.listdir(folder_path):
            # Match rotated filenames like: square_0_0_1_rot90.png
            match = re.match(r'square_(\d+)_(\d+)_(\d+)_rot(\d+)\.png', filename)
            if match:
                i, j, old_index, rot_angle = match.groups()
                i, j, old_index = int(i), int(j), int(old_index)

                # Generate new unique filename
                new_index = get_next_index(folder_path, i, j)
                new_filename = f"square_{i}_{j}_{new_index}.png"
                
                # Rename the file
                old_path = os.path.join(folder_path, filename)
                new_path = os.path.join(folder_path, new_filename)
                os.rename(old_path, new_path)

                print(f"[INFO] Renamed {filename} → {new_filename}")

# Run renaming script
rename_augmented_files()
print("[INFO] Filename standardization complete!")
