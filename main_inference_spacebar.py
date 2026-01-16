import cv2
import numpy as np
from tensorflow import keras
from tensorflow.keras import models
import chess
from chess import svg
from chess import engine

# Load the trained model (v7 with multi-layer reasoning)
model = models.load_model("chess_piece_classifier_v7.h5")

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
chess_board = chess.Board()
engine = chess.engine.SimpleEngine.popen_uci("/usr/local/bin/stockfish")  # Make sure Stockfish is installed

# Stores manually clicked corners
clicked_corners = []
grid_locked = False
run_inference = False  # Flag to trigger inference on key press
waiting_for_black = False  # Track if it's Black's turn


# Chessboard file (columns) and rank (rows) identifiers
FILES = ["a", "b", "c", "d", "e", "f", "g", "h"]
RANKS = ["8", "7", "6", "5", "4", "3", "2", "1"]

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
black_suggested_move = None  # Store Black's suggested move

CATEGORIES = ["empty", "black", "white"]
IMG_SIZE = 64  # Resize images to 64x64 pixels

def preprocess_square(square_img):
    """ 
    Multi-layer preprocessing to distinguish pieces from empty squares.
    - Focuses on CENTER of square (ignores board line edges)
    - Uses gradients to detect 3D piece shapes
    """
    square_img = cv2.resize(square_img, (IMG_SIZE, IMG_SIZE))
    
    # Layer 1: Normalize color channels
    bgr = square_img.astype(np.float32) / 255.0
    
    # Layer 2: Edge detection focused on center (ignore board boundaries)
    gray = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200).astype(np.float32) / 255.0
    
    # Mask out outer 15% (where board lines are)
    mask = np.ones_like(edges)
    border = int(IMG_SIZE * 0.15)
    mask[:border, :] = 0
    mask[-border:, :] = 0
    mask[:, :border] = 0
    mask[:, -border:] = 0
    edges = edges * mask
    edges = np.expand_dims(edges, axis=-1)
    
    # Layer 3: Gradient magnitude (3D pieces have strong gradients)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_mag = np.sqrt(sobelx**2 + sobely**2)
    gradient_mag = (gradient_mag / gradient_mag.max()).astype(np.float32) if gradient_mag.max() > 0 else gradient_mag
    gradient_mag = np.expand_dims(gradient_mag, axis=-1)
    
    # Combine all layers: [B, G, R, Edges, Gradients] = 5 channels
    enhanced = np.concatenate([bgr, edges, gradient_mag], axis=-1)
    
    return np.expand_dims(enhanced, axis=0)  # Add batch dimension

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
            square_img = preprocess_square(square_img)  # Preprocess
            
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

def detect_move(previous_state, current_state):
    """ Detects a move by comparing the previous and current board state. """
    departure = None
    arrival = None

    for i in range(8):
        for j in range(8):
            if previous_state[i, j] != current_state[i, j]:  # Something changed
                if previous_state[i, j] in ["black", "white"] and current_state[i, j] == "empty":
                    departure = (i, j)  # Piece moved from here
                if previous_state[i, j] == "empty" and current_state[i, j] in ["black", "white"]:
                    arrival = (i, j)  # Piece moved to here

    if departure and arrival:
        # Automatically adjust board orientation if needed
        from_square, to_square = map_board_coordinates(departure, arrival)
        move = from_square + to_square
        return move
    return None

def map_board_coordinates(departure, arrival):
    """ Maps the detected move to the correct orientation based on the physical board. """
    # Determine if the board needs flipping
    flipped = is_board_flipped()

    if flipped:
        # If flipped, invert files and ranks
        from_square = f"{FILES[7 - departure[1]]}{RANKS[7 - departure[0]]}"
        to_square = f"{FILES[7 - arrival[1]]}{RANKS[7 - arrival[0]]}"
    else:
        # Standard mapping
        from_square = f"{FILES[departure[1]]}{RANKS[departure[0]]}"
        to_square = f"{FILES[arrival[1]]}{RANKS[arrival[0]]}"

    return from_square, to_square

def is_board_flipped():
    """ Detects if the board orientation is flipped compared to the expected layout. """
    # Check known reference squares (e.g., A1 should be white)
    # Adjust logic here based on your camera's physical setup
    a1_square = board_state[7, 0]  # Bottom-left in our expected layout
    if a1_square in ["black", "white"]:
        return False  # Standard orientation
    return True  # Board is flipped

def flip_move(move):
    """ Converts a move to the flipped perspective if needed. """
    from_square = move[:2]  # Example: "d7"
    to_square = move[2:4]   # Example: "d5"

    # Convert notation to flipped ranks/files
    flipped_from = f"{FILES[7 - FILES.index(from_square[0])]}{RANKS[7 - RANKS.index(from_square[1])]}"
    flipped_to = f"{FILES[7 - FILES.index(to_square[0])]}{RANKS[7 - RANKS.index(to_square[1])]}"

    return flipped_from + flipped_to

def suggest_black_move():
    """ Uses Stockfish to suggest a move for Black and applies board flipping correction if needed. """
    global black_suggested_move

    result = engine.play(chess_board, chess.engine.Limit(time=0.1))
    suggested_move = result.move.uci()

    # If the board is flipped, remap suggested move
    if is_board_flipped():
        suggested_move = flip_move(suggested_move)

    return suggested_move

def update_chess_game(move):
    """ Updates the chess game with the detected move. """
    try:
        chess_move = chess.Move.from_uci(move)
        if chess_move in chess_board.legal_moves:
            chess_board.push(chess_move)
            print(f"Move played: {move}")
            print(chess_board)  # Display board in terminal
        else:
            print(f"Illegal move detected: {move}")
    except ValueError:
        print(f"Invalid move format: {move}")

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
                detected_move = detect_move(previous_board_state, board_state)

                if detected_move:
                    if chess_board.turn == chess.WHITE:
                        chess_board.push(chess.Move.from_uci(detected_move))
                        print(f"White played: {detected_move}")

                        black_suggested_move = suggest_black_move()
                        print(f"Suggested move for Black: {black_suggested_move}")
                        waiting_for_black = True

                    elif chess_board.turn == chess.BLACK and waiting_for_black:
                        if detected_move == black_suggested_move:
                            chess_board.push(chess.Move.from_uci(detected_move))
                            print(f"Black played the suggested move: {detected_move}")
                            waiting_for_black = False
                        else:
                            print(f"Expected {black_suggested_move}, but detected {detected_move}")

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
engine.quit()
cv2.destroyAllWindows()
