import cv2
import numpy as np
from keras import models

CATEGORIES = ["empty", "black_piece", "white_piece"]
IMG_SIZE = 64  # Resize images to 64x64 pixels

def preprocess_square(square_img):
    """ Prepares a chessboard square for prediction. """
    square_img = cv2.resize(square_img, (IMG_SIZE, IMG_SIZE))  # Resize
    square_img = square_img / 255.0  # Normalize
    square_img = np.expand_dims(square_img, axis=0)  # Add batch dimension
    return square_img

def classify_chessboard(frame, grid_points, model):
    """ Predicts piece placement on the chessboard. """
    board_state = np.empty((8, 8), dtype=object)
    
    for i in range(8):
        for j in range(8):
            x1, y1 = int(grid_points[i, j][0]), int(grid_points[i, j][1])
            x2, y2 = int(grid_points[i + 1, j + 1][0]), int(grid_points[i + 1, j + 1][1])
            
            square_img = frame[y1:y2, x1:x2]  # Crop square
            square_img = preprocess_square(square_img)  # Preprocess for model
            
            prediction = model.predict(square_img)
            class_idx = np.argmax(prediction)
            board_state[i, j] = CATEGORIES[class_idx]
    
    return board_state

def overlay_predictions(warped_board, board_state, grid_points):
    """ Overlays model predictions on the warped chessboard image. """
    for i in range(8):
        for j in range(8):
            x, y = int(grid_points[i, j][0]), int(grid_points[i, j][1])
            label = board_state[i, j]
            
            cv2.putText(warped_board, label, (x + 10, y + 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    return warped_board
