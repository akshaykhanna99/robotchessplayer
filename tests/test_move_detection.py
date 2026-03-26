import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game.move_detection import detect_observed_move


def empty_board():
    return np.full((8, 8), "empty", dtype=object)


def anchored_board():
    board = empty_board()
    board[7, 0] = "white"
    return board


def test_detects_simple_non_capture_move():
    previous = anchored_board()
    current = anchored_board()

    previous[6, 4] = "white"  # e2
    current[4, 4] = "white"   # e4

    assert detect_observed_move(previous, current) == "e2e4"


def test_detects_capture_move():
    previous = anchored_board()
    current = anchored_board()

    previous[3, 2] = "black"  # c5
    previous[4, 3] = "white"  # d4
    current[4, 3] = "black"   # c5xd4

    assert detect_observed_move(previous, current) == "c5d4"


def test_ignores_single_square_color_flip_noise():
    previous = anchored_board()
    current = anchored_board()

    previous[4, 3] = "white"
    current[4, 3] = "black"

    assert detect_observed_move(previous, current) is None


def test_detects_white_kingside_castle():
    previous = anchored_board()
    current = anchored_board()

    previous[7, 4] = "white"  # e1 king
    previous[7, 7] = "white"  # h1 rook
    current[7, 5] = "white"   # f1 rook
    current[7, 6] = "white"   # g1 king

    assert detect_observed_move(previous, current) == "e1g1"


def test_detects_black_kingside_castle():
    previous = anchored_board()
    current = anchored_board()

    previous[0, 4] = "black"  # e8 king
    previous[0, 7] = "black"  # h8 rook
    current[0, 5] = "black"   # f8 rook
    current[0, 6] = "black"   # g8 king

    assert detect_observed_move(previous, current) == "e8g8"
