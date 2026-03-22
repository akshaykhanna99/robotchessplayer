"""Control-centre orchestrator for UI-driven flow."""

from __future__ import annotations

from pathlib import Path
import cv2

from src.game.engine import StockfishEngineClient
from src.game.session import ChessGameSession
from src.motion.board_mapper import BoardMapper
from src.motion.planner import MotionPlanner
from src.motion.task_planner import ChessTaskPlanner
from src.motion.trajectory import CartesianTrajectoryPlanner
from src.robot.adapters.mock_robot import MockRobotArm
from src.robot.config import PhysicalSetupConfig, load_physical_setup_config
from src.robot.kinematics import SimpleArmKinematics
from src.ui.qt import QObject, Signal, Slot, QThread, Qt
from src.orchestrator.events import make_event
from src.orchestrator.state import GameStatus, SystemStatus, VisionStatus
from src.orchestrator.workers import RobotExecutionPayload, RobotExecutionWorker, VisionWorker


class ControlCentreController(QObject):
    log_event = Signal(object)
    vision_frame = Signal(object)
    vision_warped = Signal(object)
    vision_overlay = Signal(object)
    vision_status = Signal(object)
    game_status = Signal(object)
    system_status = Signal(object)
    robot_plan = Signal(object)
    robot_progress = Signal(object)
    robot_gripper = Signal(object)
    robot_execution_state = Signal(object)
    _vision_reset_requested = Signal()
    _vision_inference_requested = Signal()
    _vision_stop_requested = Signal()
    _vision_corner_requested = Signal(int, int, int, int)

    def __init__(self) -> None:
        super().__init__()
        self.mode = "Vision Only"
        self._setup: PhysicalSetupConfig | None = None
        self._planner: MotionPlanner | None = None
        self._kinematics: SimpleArmKinematics | None = None
        self._robot_adapter: MockRobotArm | None = None
        self._game_session: ChessGameSession | None = None
        self._vision_thread: QThread | None = None
        self._vision_worker: VisionWorker | None = None
        self._robot_thread: QThread | None = None
        self._robot_worker: RobotExecutionWorker | None = None
        self._game_status = GameStatus(mode=self.mode)
        self._system_status = SystemStatus()
        self._vision_status = VisionStatus()
        self._stockfish_path = "/usr/local/bin/stockfish"
        self._model_path = str(Path("models") / "chess_piece_classifier_v7.h5")
        self._last_robot_executed_suggestion: str | None = None

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._game_status.mode = mode
        self.game_status.emit(self._game_status)

    def load_config(self, path: str) -> None:
        try:
            self._setup = load_physical_setup_config(path)
        except Exception as exc:
            self.log_event.emit(make_event("error", f"Failed to load config: {exc}"))
            return
        self._planner = MotionPlanner(
            task_planner=ChessTaskPlanner(),
            trajectory_planner=CartesianTrajectoryPlanner(BoardMapper(self._setup.board)),
        )
        try:
            self._kinematics = SimpleArmKinematics.from_robot_config(self._setup.robot)
            self._robot_adapter = MockRobotArm(config=self._setup.robot, kinematics=self._kinematics)
        except Exception as exc:
            self.log_event.emit(make_event("error", f"Robot config invalid: {exc}"))
        self._system_status = SystemStatus(
            setup_name=self._setup.setup_name,
            robot_name=self._setup.robot.name,
            serial_port=self._setup.robot.transport.port,
            square_size_mm=self._setup.board.square_size_mm,
        )
        self.system_status.emit(self._system_status)
        self.log_event.emit(make_event("system", f"Loaded config: {self._setup.setup_name}"))

    def start_camera(
        self,
        camera_index: int = 0,
        camera_backend: str = "Auto",
        camera_source: str | None = None,
    ) -> None:
        if self._vision_thread:
            return
        backend_id = self._resolve_camera_backend(camera_backend)
        self._vision_thread = QThread()
        self._vision_worker = VisionWorker(
            camera_index=camera_index,
            model_path=self._model_path,
            camera_backend=backend_id,
            camera_source=camera_source,
        )
        self._vision_worker.moveToThread(self._vision_thread)
        self._vision_thread.started.connect(self._vision_worker.start_capture)
        self._vision_worker.frame_ready.connect(self.vision_frame)
        self._vision_worker.warped_ready.connect(self.vision_warped)
        self._vision_worker.inference_ready.connect(self._handle_inference)
        self._vision_worker.status_changed.connect(self._handle_vision_status)
        self._vision_worker.error.connect(lambda msg: self.log_event.emit(make_event("error", msg)))
        self._vision_reset_requested.connect(self._vision_worker.reset_corners)
        self._vision_inference_requested.connect(self._vision_worker.request_inference)
        self._vision_stop_requested.connect(
            self._vision_worker.stop_capture,
            Qt.ConnectionType.BlockingQueuedConnection,
        )
        self._vision_corner_requested.connect(self._vision_worker.add_corner)
        self._vision_thread.finished.connect(self._vision_worker.deleteLater)
        self._vision_thread.start()
        backend_msg = camera_backend if camera_backend else "Auto"
        source_msg = camera_source.strip() if camera_source else str(camera_index)
        self.log_event.emit(make_event("vision", f"Camera started (source={source_msg}, backend={backend_msg})"))

    def stop_camera(self) -> None:
        if not self._vision_worker or not self._vision_thread:
            return
        if self._vision_thread.isRunning():
            self._vision_stop_requested.emit()
        self._vision_thread.quit()
        self._vision_thread.wait()
        self._vision_thread = None
        self._vision_worker = None
        self.log_event.emit(make_event("vision", "Camera stopped"))

    def reset_corners(self) -> None:
        if self._vision_worker:
            self._vision_reset_requested.emit()
            self.log_event.emit(make_event("vision", "Corners reset"))

    def add_corner(self, x: int, y: int, w: int, h: int) -> None:
        if self._vision_worker:
            self._vision_corner_requested.emit(x, y, w, h)

    def run_inference(self) -> None:
        if self._vision_worker:
            self._vision_inference_requested.emit()
            self.log_event.emit(make_event("vision", "Inference requested"))

    def shutdown(self) -> None:
        self.stop_camera()
        if self._robot_worker:
            self._robot_worker.stop()
        if self._robot_thread:
            self._robot_thread.quit()
            self._robot_thread.wait()
            self._robot_thread = None
            self._robot_worker = None
        if self._game_session:
            self._game_session.close()
            self._game_session = None

    def _handle_vision_status(self, status: dict) -> None:
        self._vision_status.camera_connected = status.get("camera_connected", False)
        self._vision_status.corners_selected = status.get("corners_selected", 0)
        self._vision_status.grid_locked = status.get("grid_locked", False)
        self.vision_status.emit({"status": self._vision_status, "next_corner": status.get("corner_label")})

    def _resolve_camera_backend(self, backend_name: str) -> int | None:
        name = (backend_name or "Auto").strip().lower()
        if name in ("", "auto", "default"):
            return None
        if name == "avfoundation":
            if hasattr(cv2, "CAP_AVFOUNDATION"):
                return int(cv2.CAP_AVFOUNDATION)
            self.log_event.emit(make_event("error", "OpenCV build does not expose CAP_AVFOUNDATION; using default backend"))
            return None
        self.log_event.emit(make_event("error", f"Unknown camera backend '{backend_name}', using default backend"))
        return None

    def _handle_inference(self, payload: dict) -> None:
        board_state = payload.get("board_state")
        detected_move = payload.get("detected_move")
        overlay = payload.get("overlay")
        if overlay is not None:
            self.vision_overlay.emit(overlay)
        if detected_move:
            self._game_status.last_detected_move = detected_move
            self.log_event.emit(make_event("game", f"Detected move: {detected_move}"))
        else:
            self.log_event.emit(make_event("game", "No move detected"))

        if self.mode == "Vision Only":
            self.game_status.emit(self._game_status)
            return

        self._ensure_game_session()
        if not self._game_session:
            self.game_status.emit(self._game_status)
            return
        prev_suggestion = self._game_session.black_suggested_move
        messages = self._game_session.process_detected_move(detected_move, board_state)
        generated_new_suggestion = False
        if messages:
            for message in messages:
                if message.startswith("Suggested move for Black:"):
                    generated_new_suggestion = True
                self.log_event.emit(make_event("game", message))

        if self._game_session.black_suggested_move:
            self._game_status.suggested_move = self._game_session.black_suggested_move
        self._game_status.side_to_move = "White" if self._game_session.board.turn else "Black"
        self._game_status.fen = self._game_session.board.fen()
        self.game_status.emit(self._game_status)

        if self.mode in ("Vision + Game + Mock Robot", "Full System"):
            if (
                generated_new_suggestion
                and self._game_session.black_suggested_move
                and self._game_session.black_suggested_move != self._last_robot_executed_suggestion
            ):
                self._run_robot_for_move(self._game_session.black_suggested_move)

    def _ensure_game_session(self) -> None:
        if self._game_session:
            return
        try:
            engine = StockfishEngineClient(self._stockfish_path)
            self._game_session = ChessGameSession(engine)
            self.log_event.emit(make_event("system", "Stockfish engine connected"))
        except Exception as exc:
            self.log_event.emit(make_event("error", f"Stockfish init failed: {exc}"))

    def _run_robot_for_move(self, uci_move: str) -> None:
        if not self._planner or not self._kinematics or not self._robot_adapter:
            self.log_event.emit(make_event("error", "Robot is not configured"))
            return
        task, plan = self._planner.plan_uci_move(uci_move)
        self._last_robot_executed_suggestion = uci_move
        self.robot_plan.emit(plan)
        self.log_event.emit(make_event("motion", f"Planned task {task.name}"))
        if self._robot_thread:
            return
        payload = RobotExecutionPayload(plan=plan, adapter=self._robot_adapter, kinematics=self._kinematics)
        self._robot_thread = QThread()
        self._robot_worker = RobotExecutionWorker(payload)
        self._robot_worker.moveToThread(self._robot_thread)
        self._robot_thread.started.connect(self._robot_worker.run)
        self._robot_worker.progress.connect(self.robot_progress)
        self._robot_worker.gripper.connect(self.robot_gripper)
        self._robot_worker.error.connect(lambda msg: self.log_event.emit(make_event("error", msg)))
        self._robot_worker.finished.connect(self._on_robot_finished)
        self._robot_thread.start()
        self.robot_execution_state.emit({"executing": True})

    def _on_robot_finished(self) -> None:
        if self._robot_thread:
            self._robot_thread.quit()
            self._robot_thread.wait()
        self._robot_thread = None
        self._robot_worker = None
        self.robot_execution_state.emit({"executing": False})
