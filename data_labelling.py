import cv2
import os
import numpy as np

# Paths for saving images
DATASET_PATH = "chess_dataset"
CATEGORIES = {"e": "empty", "b": "black_piece", "w": "white_piece"}

# Create dataset folders if they don’t exist
for category in CATEGORIES.values():
    os.makedirs(os.path.join(DATASET_PATH, category), exist_ok=True)

# Initialize webcam
cap = cv2.VideoCapture(0)

# Stores the manually clicked corners
clicked_corners = []
grid_locked = False  # Flag to indicate if grid is finalized


def get_unique_filename(folder, i, j):
    """ Generates a unique filename to prevent overwriting previous images. """
    existing_files = os.listdir(folder)
    existing_indices = [
        int(f.split("_")[-1].split(".")[0]) for f in existing_files if f.startswith(f"square_{i}_{j}_")
    ]
    new_index = max(existing_indices, default=0) + 1
    return f"{folder}/square_{i}_{j}_{new_index}.png"


def capture_and_save_squares(warped_board_clean, grid_points):
    """ Displays each square and allows the user to manually label it. """
    board_state = np.empty((8, 8), dtype=object)

    for i in range(8):
        for j in range(8):
            x1, y1 = grid_points[i, j].astype(int)
            x2, y2 = grid_points[i + 1, j + 1].astype(int)

            # Extract the square from the clean warped board (without text)
            square_img = warped_board_clean[y1:y2, x1:x2]

            # Display the square and ask for a label
            cv2.imshow("Label Square", square_img)
            key = input(f"Enter label for square [{i},{j}] (e=empty, b=black, w=white): ").strip().lower()

            while key not in CATEGORIES:
                print("Invalid input! Please enter 'e', 'b', or 'w'.")
                key = input(f"Enter label for square [{i},{j}]: ").strip().lower()

            board_state[i, j] = CATEGORIES[key]

            # Generate a unique filename
            folder = f"{DATASET_PATH}/{CATEGORIES[key]}"
            filename = get_unique_filename(folder, i, j)
            cv2.imwrite(filename, square_img)

            cv2.destroyAllWindows()  # Close window before showing the next square

    print("[INFO] Board state saved!")
    print("[INFO] Press 'S' after making a move to label again, or 'F' to finish.")

