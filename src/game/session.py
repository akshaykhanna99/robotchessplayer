"""Game-session controller for move application and engine-response flow."""

import chess


class ChessGameSession:
    """Encapsulates chess state and Black-response suggestion workflow."""

    def __init__(self, engine_client):
        self.board = chess.Board()
        self.engine_client = engine_client
        self.waiting_for_black = False
        self.black_suggested_move = None

    def evaluate_detected_move(self, detected_move, observed_board_state):
        """Apply a detected move and optionally produce a Black suggestion.

        Returns `(accepted, messages)` where `accepted` indicates whether the
        detected move was incorporated into tracked game state.
        """
        messages = []
        if not detected_move:
            return False, messages

        try:
            chess_move = chess.Move.from_uci(detected_move)
        except ValueError:
            return False, [f"Invalid move format: {detected_move}"]

        if self.board.turn == chess.WHITE:
            if chess_move not in self.board.legal_moves:
                return False, [f"Illegal move detected: {detected_move}"]

            self.board.push(chess_move)
            messages.append(f"White played: {detected_move}")

            self.black_suggested_move = self.engine_client.suggest_move(self.board, observed_board_state)
            self.waiting_for_black = True
            messages.append(f"Suggested move for Black: {self.black_suggested_move}")
            return True, messages

        if self.board.turn == chess.BLACK and self.waiting_for_black:
            if detected_move == self.black_suggested_move:
                if chess_move in self.board.legal_moves:
                    self.board.push(chess_move)
                    messages.append(f"Black played the suggested move: {detected_move}")
                    self.waiting_for_black = False
                    self.black_suggested_move = None
                    return True, messages
                else:
                    messages.append(f"Detected move is not legal for Black: {detected_move}")
            else:
                messages.append(f"Expected {self.black_suggested_move}, but detected {detected_move}")

        return False, messages

    def process_detected_move(self, detected_move, observed_board_state):
        """Backward-compatible wrapper returning only the UI messages."""
        _accepted, messages = self.evaluate_detected_move(detected_move, observed_board_state)
        return messages

    def close(self):
        self.engine_client.close()
