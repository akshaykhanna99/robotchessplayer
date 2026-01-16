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

# Stores manually clicked corners
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

def get_unique_filename(folder, i, j):
    """Generates a unique filename to prevent overwriting previous images."""
    existing_files = os.listdir(folder)
    existing_indices = [
        int(f.split("_")[-1].split(".")[0]) for f in existing_files if f.startswith(f"square_{i}_{j}_")
    ]
    new_index = max(existing_indices, default=0) + 1
    return f"{folder}/square_{i}_{j}_{new_index}.png"

def rotate_and_save(image, folder, i, j):
    """Saves original image and generates rotated copies (90°, 180°, 270°)."""
    angles = [90, 180, 270]
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)

    for angle in angles:
        # Rotation matrix
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h))

        # Get unique filename for rotated image
        save_path = get_unique_filename(folder, i, j)
        cv2.imwrite(save_path, rotated)

def capture_and_save_squares(warped_board_clean, grid_points):
    """Displays each square, allows manual labeling, and saves rotated versions."""
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

            # Generate a unique filename for original image
            folder = f"{DATASET_PATH}/{CATEGORIES[key]}"
            filename = get_unique_filename(folder, i, j)
            cv2.imwrite(filename, square_img)

            # Generate rotated images immediately
            rotate_and_save(square_img, folder, i, j)

            cv2.destroyAllWindows()  # Close window before showing the next square

    print("[INFO] Board state saved!")
    print("[INFO] Press 'S' after making a move to label again, or 'F' to finish.")

# Set up mouse click event
cv2.namedWindow("Raw Frame")
cv2.setMouseCallback("Raw Frame", mouse_callback)

while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Failed to grab frame")
        break

    # Draw selected points
    for point in clicked_corners:
        cv2.circle(frame, tuple(point), 5, (0, 0, 255), -1)

    # Warp board after selecting 4 corners
    if grid_locked:
        transform_matrix, board_size = get_warp_matrix()
        if transform_matrix is not None:
            # Create two copies of the warped board (one for labeling, one for reference)
            warped_board = cv2.warpPerspective(frame, transform_matrix, (board_size, board_size))
            # Apply contrast enhancement using CLAHE (Adaptive Histogram Equalization)
            lab = cv2.cvtColor(warped_board, cv2.COLOR_BGR2LAB)  # Convert to LAB color space
            l, a, b = cv2.split(lab)  # Split channels
            
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))  # Define CLAHE
            l = clahe.apply(l)  # Apply CLAHE to the L (lightness) channel
            
            enhanced_lab = cv2.merge((l, a, b))  # Merge back the LAB channels
            warped_board = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)  # Convert back to BGR
            warped_board_clean = warped_board.copy()
            grid_points = divide_board_into_squares(board_size)

            # Draw grid lines & square coordinates on the coordinate view
            for i in range(9):
                for j in range(8):
                    pt1 = tuple(grid_points[i, j].astype(int))
                    pt2 = tuple(grid_points[i, j + 1].astype(int))
                    cv2.line(warped_board, pt1, pt2, (0, 255, 0), 2)

                    pt3 = tuple(grid_points[j, i].astype(int))
                    pt4 = tuple(grid_points[j + 1, i].astype(int))
                    cv2.line(warped_board, pt3, pt4, (0, 255, 0), 2)

            # Add square coordinates on the coordinate view (not on labeled images)
            for i in range(8):
                for j in range(8):
                    x, y = grid_points[i, j].astype(int)
                    cv2.putText(warped_board, f"{i},{j}", (x + 5, y + 15), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

            
            # Show the two warped views
            cv2.imshow("Warped View (Grid & Coordinates)", warped_board)
            cv2.imshow("Warped View (For Labeling)", warped_board_clean)
    
    # Keep the original raw frame for reference
    cv2.imshow("Raw Frame", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('s') and grid_locked:  # Press 'S' to start labeling squares after a move
        capture_and_save_squares(warped_board_clean, grid_points)
    elif key == ord('f'):  # Press 'F' to finish labeling process
        print("[INFO] Labelling finished. Exiting...")
        break
    elif key == ord('r'):  # Reset the selection
        clicked_corners = []
        grid_locked = False
        print("[INFO] Resetting corner selection.")
    elif key == ord('q'):  # Quit
        break

cap.release()
cv2.destroyAllWindows()
