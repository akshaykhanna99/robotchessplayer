"""Stockfish engine adapter for the game layer."""

from pathlib import Path

import chess
from chess import engine as chess_engine

from src.game.move_detection import flip_uci_move, is_board_flipped


class StockfishEngineClient:
    """Thin wrapper around python-chess Stockfish engine integration."""

    def __init__(self, engine_path, think_time_sec=0.1):
        self.engine_path = str(Path(engine_path))
        self.think_time_sec = think_time_sec
        self._engine = chess_engine.SimpleEngine.popen_uci(self.engine_path)

    def suggest_move(self, chess_board, observed_board_state):
        """Return suggested UCI move, remapped if observed board orientation is flipped."""
        result = self._engine.play(chess_board, chess_engine.Limit(time=self.think_time_sec))
        suggested_move = result.move.uci()
        if is_board_flipped(observed_board_state):
            suggested_move = flip_uci_move(suggested_move)
        return suggested_move

    def close(self):
        self._engine.quit()
