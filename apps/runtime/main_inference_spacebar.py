import cv2
import numpy as np
from pathlib import Path
from tensorflow.keras import models
from src.game.engine import StockfishEngineClient
from src.game.move_detection import FILES, RANKS, detect_observed_move
from src.game.session import ChessGameSession
from src.vision.preprocessing import preprocess_square_enhanced_v7

# Load the trained model (v7 with multi-layer reasoning)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
model = models.load_model(PROJECT_ROOT / "models" / "chess_piece_classifier_v7.h5")

# Initialize webcam - Try different indices for USB camera
# Common indices: 0 (built-in), 1 or 2 (external USB)
CAMERA_INDEX = 0  # Change this to 0, 1, or 2 to find your USB camera

print(f"[INFO] Attempting to open camera at index {CAMERA_INDEX}...")
cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    print(f"[ERROR] Could not open camera at index {CAMERA_INDEX}")
    print("[INFO] Try changing CAMERA_INDEX to 0, 1, or 2 at the top of this file")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
print(f"[INFO] Camera {CAMERA_INDEX} opened successfully!")

# Initialize chess game
game_session = ChessGameSession(StockfishEngineClient("/usr/local/bin/stockfish"))

# Stores manually clicked corners
clicked_corners = []
grid_locked = False
run_inference = False  # Flag to trigger inference on key press

# Required corner selection order
CORNER_ORDER = [
    ("A1", "Black Rook on White Square"),  # Bottom-left
    ("H1", "Black Rook on Black Square"),  # Bottom-right
    ("H8", "White Rook on White Square"),  # Top-right
    ("A8", "White Rook on Black Square"),  # Top-left
]

# Initialize board state before inference runs
previous_board_state = np.full((8, 8), "empty", dtype=object)
board_state = np.full((8, 8), "empty", dtype=object)
CATEGORIES = ["empty", "black", "white"]

def classify_chessboard(frame, grid_points):
    """ Predicts piece placement on the chessboard when triggered. """
    global previous_board_state
    previous_board_state = board_state.copy()  # Store previous board state
    new_board_state = np.empty((8, 8), dtype=object)
    
    for i in range(8):
        for j in range(8):
            x1, y1 = int(grid_points[i, j][0]), int(grid_points[i, j][1])
            x2, y2 = int(grid_points[i + 1, j + 1][0]), int(grid_points[i + 1, j + 1][1])
            
            square_img = frame[y1:y2, x1:x2]  # Crop square
            square_img = preprocess_square_enhanced_v7(square_img, add_batch_dim=True)  # Preprocess
            
            prediction = model.predict(square_img, verbose=0)
            class_idx = np.argmax(prediction)
            new_board_state[i, j] = CATEGORIES[class_idx]

    return new_board_state

def overlay_predictions(warped_board, board_state, grid_points):
    """ Overlays model predictions on the warped chessboard image. """
    for i in range(8):
        for j in range(8):
            x, y = int(grid_points[i + 1, j][0]), int(grid_points[i + 1, j][1])  # Bottom-left corner
            label = board_state[i, j]  # Classification result ("empty", "black", "white")

            # Display classification label in yellow
            cv2.putText(warped_board, label, (x + 5, y - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

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
    """Handles mouse clicks to select chessboard corners in the correct order."""
    global clicked_corners, grid_locked

    if event == cv2.EVENT_LBUTTONDOWN and not grid_locked:
        if len(clicked_corners) < 4:
            square_id, description = CORNER_ORDER[len(clicked_corners)]
            clicked_corners.append([x, y])
            print(f"[INFO] Corner {square_id} ({description}) selected at ({x}, {y})")

        if len(clicked_corners) == 4:
            grid_locked = True
            print("[INFO] All corners selected! Warping board...")

# Set up mouse click event
cv2.namedWindow("Raw Frame")
cv2.setMouseCallback("Raw Frame", mouse_callback)

print("[INSTRUCTION] Please click the chessboard corners in this order:")
for square, description in CORNER_ORDER:
    print(f"- {square}: {description}")

while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Failed to grab frame")
        break

    # Draw selected points with red markers
    for point in clicked_corners:
        cv2.circle(frame, tuple(point), 5, (0, 0, 255), -1)

    if grid_locked:
        transform_matrix, board_size = get_warp_matrix()
        if transform_matrix is not None:
            warped_board = cv2.warpPerspective(frame, transform_matrix, (board_size, board_size))

            # Apply contrast enhancement
            lab = cv2.cvtColor(warped_board, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced_lab = cv2.merge((l, a, b))
            warped_board = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
            
            warped_board_clean = warped_board.copy()
            grid_points = divide_board_into_squares(board_size)

            # Draw grid and label squares with chess notation
            for i in range(9):
                for j in range(8):
                    pt1 = tuple(grid_points[i, j].astype(int))
                    pt2 = tuple(grid_points[i, j + 1].astype(int))
                    cv2.line(warped_board, pt1, pt2, (0, 255, 0), 2)

                    pt3 = tuple(grid_points[j, i].astype(int))
                    pt4 = tuple(grid_points[j + 1, i].astype(int))
                    cv2.line(warped_board, pt3, pt4, (0, 255, 0), 2)

            # Add file & rank labels to each square
            for i in range(8):
                for j in range(8):
                    x, y = grid_points[i + 1, j].astype(int)
                    square_label = f"{FILES[j]}{RANKS[i]}"  # Convert to chess notation
                    cv2.putText(warped_board, square_label, (x + 5, y - 5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

            cv2.imshow("Warped View (Grid & Coordinates)", warped_board)

            # Run inference only when the spacebar is pressed
            if run_inference:
                board_state = classify_chessboard(warped_board_clean, grid_points)
                detected_move = detect_observed_move(previous_board_state, board_state)

                for message in game_session.process_detected_move(detected_move, board_state):
                    print(message)

                run_inference = False

            # Overlay predictions (restore classification labels)
            predictions_overlay = overlay_predictions(warped_board_clean.copy(), board_state, grid_points)
            cv2.imshow("Warped Board with Predictions", predictions_overlay)

    cv2.imshow("Raw Frame", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('r'):
        clicked_corners = []
        grid_locked = False
        print("[INFO] Resetting corner selection.")
    elif key == ord('q'):
        break
    elif key == ord(' '):
        run_inference = True
        print("[INFO] Running inference...")

cap.release()
game_session.close()
cv2.destroyAllWindows()
