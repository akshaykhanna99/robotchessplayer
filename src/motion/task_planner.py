"""Convert chess moves into hardware-agnostic manipulation tasks."""

from src.motion.types import BoardSquareRef, GripperAction, MotionAction, RobotTask


class ChessTaskPlanner:
    """Plan high-level manipulation tasks from UCI chess moves."""

    def plan_move(self, uci_move: str, is_capture: bool = False) -> RobotTask:
        """Create a pick-and-place task for a standard move.

        `is_capture` is a placeholder flag until piece-type-aware game state is integrated.
        """
        if len(uci_move) < 4:
            raise ValueError(f"Invalid UCI move '{uci_move}'")

        from_sq = uci_move[:2]
        to_sq = uci_move[2:4]
        actions: list[MotionAction] = []

        if is_capture:
            actions.extend(self._capture_sequence(to_sq))

        actions.extend(
            [
                MotionAction(kind="move_to_square", square=BoardSquareRef(from_sq), label="move to source"),
                MotionAction(kind="gripper", gripper=GripperAction("close"), label="grip piece"),
                MotionAction(
                    kind="retreat_from_square",
                    square=BoardSquareRef(from_sq),
                    label="lift from source",
                ),
                MotionAction(kind="move_to_square", square=BoardSquareRef(to_sq), label="move to destination"),
                MotionAction(kind="gripper", gripper=GripperAction("open"), label="release piece"),
                MotionAction(
                    kind="retreat_from_square",
                    square=BoardSquareRef(to_sq),
                    label="retreat from destination",
                ),
            ]
        )
        return RobotTask(name=f"move_{uci_move}", actions=tuple(actions))

    def _capture_sequence(self, square: str) -> list[MotionAction]:
        # Capture tray routing can be added once robot config includes tray pose execution.
        return [
            MotionAction(kind="move_to_square", square=BoardSquareRef(square), label="approach capture square"),
            MotionAction(kind="gripper", gripper=GripperAction("close"), label="grip captured piece"),
            MotionAction(kind="retreat_from_square", square=BoardSquareRef(square), label="lift captured piece"),
            MotionAction(kind="gripper", gripper=GripperAction("open"), label="release captured piece (placeholder)"),
        ]
