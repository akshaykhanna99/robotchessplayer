"""Helpers for converting observed 8x8 board-state changes into UCI moves."""

FILES = ["a", "b", "c", "d", "e", "f", "g", "h"]
RANKS = ["8", "7", "6", "5", "4", "3", "2", "1"]
PIECES = {"black", "white"}


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


def coordinate_to_square(coord, board_state):
    """Map a matrix coordinate to chess square notation, handling board flip."""
    flipped = is_board_flipped(board_state)
    row, col = coord
    if flipped:
        return f"{FILES[7 - col]}{RANKS[7 - row]}"
    return f"{FILES[col]}{RANKS[row]}"


def detect_castling_move(departures, arrivals, board_state):
    """Detect castling from a four-square occupancy change pattern."""
    if len(departures) != 2 or len(arrivals) != 2:
        return None

    departure_squares = {coordinate_to_square(coord, board_state) for coord, _piece in departures}
    arrival_squares = {coordinate_to_square(coord, board_state) for coord, _prev, _curr in arrivals}

    castling_patterns = {
        (frozenset({"e1", "h1"}), frozenset({"f1", "g1"})): "e1g1",
        (frozenset({"e1", "a1"}), frozenset({"c1", "d1"})): "e1c1",
        (frozenset({"e8", "h8"}), frozenset({"f8", "g8"})): "e8g8",
        (frozenset({"e8", "a8"}), frozenset({"c8", "d8"})): "e8c8",
    }

    return castling_patterns.get((frozenset(departure_squares), frozenset(arrival_squares)))


def detect_observed_move(previous_state, current_state):
    """Infer a simple move from departure/arrival differences in board states."""
    departures = []
    arrivals = []

    for i in range(8):
        for j in range(8):
            previous_value = previous_state[i, j]
            current_value = current_state[i, j]
            if previous_value == current_value:
                continue

            if previous_value in PIECES and current_value == "empty":
                departures.append(((i, j), previous_value))

            if current_value in PIECES and previous_value != current_value:
                arrivals.append(((i, j), previous_value, current_value))

    castling_move = detect_castling_move(departures, arrivals, current_state)
    if castling_move is not None:
        return castling_move

    if len(departures) != 1 or len(arrivals) != 1:
        return None

    departure, moving_piece = departures[0]
    arrival, previous_arrival_value, arrival_piece = arrivals[0]

    # The arriving piece must match the color that departed. This supports normal
    # moves (`empty -> mover`) and captures (`opponent -> mover`) while rejecting
    # single-square color flips caused by noisy classification.
    if arrival_piece != moving_piece:
        return None
    if previous_arrival_value in PIECES and previous_arrival_value == moving_piece:
        return None

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
