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

def get_warp_matrix():
    """Computes perspective transform matrix using manually selected corners."""
    global clicked_corners

    if len(clicked_corners) != 4:
        return None

    # Define destination points (warped board)
    board_size = 400  # Define size of final unwarped board (adjustable)
    dest_corners = np.array([
        [0, 0], [board_size - 1, 0],
        [board_size - 1, board_size - 1], [0, board_size - 1]
    ], dtype="float32")

    # Compute perspective transform matrix
    matrix = cv2.getPerspectiveTransform(np.array(clicked_corners, dtype="float32"), dest_corners)
    return matrix, board_size

def divide_board_into_squares(board_size):
    """Divides the unwarped board into an 8x8 grid of square coordinates."""
    square_size = board_size // 8
    grid_points = np.zeros((9, 9, 2), dtype=np.float32)

    for i in range(9):
        for j in range(9):
            grid_points[i, j] = [j * square_size, i * square_size]

    return grid_points

def mouse_callback(event, x, y, flags, param):
    """Handles mouse clicks to select chessboard corners."""
    global clicked_corners, grid_locked

    if event == cv2.EVENT_LBUTTONDOWN and not grid_locked:
        clicked_corners.append([x, y])
        print(f"[INFO] Corner {len(clicked_corners)} selected: ({x}, {y})")

        # Once 4 corners are selected, lock the grid
        if len(clicked_corners) == 4:
            grid_locked = True
            print("[INFO] Corners locked! Warping board...")



