import cv2
import numpy as np
from pathlib import Path
from keras import models

# Load the trained model
PROJECT_ROOT = Path(__file__).resolve().parents[2]
model = models.load_model(PROJECT_ROOT / "models" / "archive" / "chess_piece_classifier_v4.h5")

# Initialize webcam
cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Stores manually clicked corners
clicked_corners = []
grid_locked = False
frame_count = 0  # Track frames for inference reduction
INFERENCE_INTERVAL = 2  # Run inference every N frames

# Initialize board state before inference runs
board_state = np.full((8, 8), "empty", dtype=object)


CATEGORIES = ["empty", "black", "white"]
IMG_SIZE = 64  # Resize images to 64x64 pixels

def preprocess_square(square_img):
    """ Prepares a chessboard square for prediction. """
    square_img = cv2.resize(square_img, (IMG_SIZE, IMG_SIZE))  # Resize
    square_img = square_img / 255.0  # Normalize
    return np.expand_dims(square_img, axis=0)  # Add batch dimension

def classify_chessboard(frame, grid_points):
    """ Predicts piece placement on the chessboard every N frames. """
    global frame_count
    board_state = np.empty((8, 8), dtype=object)
    
    for i in range(8):
        for j in range(8):
            x1, y1 = int(grid_points[i, j][0]), int(grid_points[i, j][1])
            x2, y2 = int(grid_points[i + 1, j + 1][0]), int(grid_points[i + 1, j + 1][1])
            
            square_img = frame[y1:y2, x1:x2]  # Crop square
            square_img = preprocess_square(square_img)  # Preprocess
            
            prediction = model.predict(square_img, verbose=0)
            class_idx = np.argmax(prediction)
            board_state[i, j] = CATEGORIES[class_idx]

    return board_state

def overlay_predictions(warped_board, board_state, grid_points):
    """ Overlays model predictions on the warped chessboard image. """
    for i in range(8):
        for j in range(8):
            x, y = int(grid_points[i + 1, j][0]), int(grid_points[i + 1, j][1])  # Bottom-left corner
            label = board_state[i, j]

            # Small font, bottom left of each square
            cv2.putText(warped_board, label, (x + 5, y - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1)
    
    return warped_board

def get_warp_matrix():
    """Computes perspective transform matrix using manually selected corners."""
    global clicked_corners
    if len(clicked_corners) != 4:
        return None

    board_size = 400  # Define size of final unwarped board
    dest_corners = np.array([[0, 0], [board_size - 1, 0], [board_size - 1, board_size - 1], [0, board_size - 1]], dtype="float32")
    return cv2.getPerspectiveTransform(np.array(clicked_corners, dtype="float32"), dest_corners), board_size

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

        if len(clicked_corners) == 4:
            grid_locked = True
            print("[INFO] Corners locked! Warping board...")

# Set up mouse click event
cv2.namedWindow("Raw Frame")
cv2.setMouseCallback("Raw Frame", mouse_callback)

while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Failed to grab frame")
        break

    frame_count += 1  # Increase frame count

    # Draw selected points with red markers
    for point in clicked_corners:
        cv2.circle(frame, tuple(point), 5, (0, 0, 255), -1)

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

            # Draw grid
            for i in range(9):
                for j in range(8):
                    pt1 = tuple(grid_points[i, j].astype(int))
                    pt2 = tuple(grid_points[i, j + 1].astype(int))
                    cv2.line(warped_board, pt1, pt2, (0, 255, 0), 2)

                    pt3 = tuple(grid_points[j, i].astype(int))
                    pt4 = tuple(grid_points[j + 1, i].astype(int))
                    cv2.line(warped_board, pt3, pt4, (0, 255, 0), 2)

            # Add square coordinates for reference
            for i in range(8):
                for j in range(8):
                    x, y = grid_points[i, j].astype(int)
                    cv2.putText(warped_board, f"{i},{j}", (x + 5, y + 15), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

            cv2.imshow("Warped View (Grid & Coordinates)", warped_board)

            # Run CNN model inference at reduced frequency
            # Ensure first inference runs immediately, then reduce frequency
            if frame_count == 1 or frame_count % INFERENCE_INTERVAL == 0:
                board_state = classify_chessboard(warped_board_clean, grid_points)

            # Overlay predictions
            result_overlay = overlay_predictions(warped_board_clean, board_state, grid_points)
            cv2.imshow("Warped Board with Predictions", result_overlay)

    cv2.imshow("Raw Frame", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('r'):
        clicked_corners = []
        grid_locked = False
        print("[INFO] Resetting corner selection.")
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
