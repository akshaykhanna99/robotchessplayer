"""Helpers for converting observed 8x8 board-state changes into UCI moves."""

FILES = ["a", "b", "c", "d", "e", "f", "g", "h"]
RANKS = ["8", "7", "6", "5", "4", "3", "2", "1"]


def is_board_flipped(board_state):
    """Heuristic orientation check based on expected A1 occupancy."""
    a1_square = board_state[7, 0]  # Bottom-left in expected layout.
    return a1_square not in ["black", "white"]


def map_board_coordinates(departure, arrival, board_state):
    """Map matrix coordinates to chess square notation, handling board flip."""
    flipped = is_board_flipped(board_state)

    if flipped:
        from_square = f"{FILES[7 - departure[1]]}{RANKS[7 - departure[0]]}"
        to_square = f"{FILES[7 - arrival[1]]}{RANKS[7 - arrival[0]]}"
    else:
        from_square = f"{FILES[departure[1]]}{RANKS[departure[0]]}"
        to_square = f"{FILES[arrival[1]]}{RANKS[arrival[0]]}"

    return from_square, to_square


def detect_observed_move(previous_state, current_state):
    """Infer a simple move from departure/arrival differences in board states."""
    departure = None
    arrival = None

    for i in range(8):
        for j in range(8):
            if previous_state[i, j] != current_state[i, j]:
                if previous_state[i, j] in ["black", "white"] and current_state[i, j] == "empty":
                    departure = (i, j)
                if previous_state[i, j] == "empty" and current_state[i, j] in ["black", "white"]:
                    arrival = (i, j)

    if departure and arrival:
        from_square, to_square = map_board_coordinates(departure, arrival, current_state)
        return from_square + to_square
    return None


def flip_uci_move(move):
    """Flip a UCI move to match the observed board orientation."""
    from_square = move[:2]
    to_square = move[2:4]
    flipped_from = f"{FILES[7 - FILES.index(from_square[0])]}{RANKS[7 - RANKS.index(from_square[1])]}"
    flipped_to = f"{FILES[7 - FILES.index(to_square[0])]}{RANKS[7 - RANKS.index(to_square[1])]}"
    return flipped_from + flipped_to
