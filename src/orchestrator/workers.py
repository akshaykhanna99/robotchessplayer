"""Background workers for vision capture/inference and robot execution."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.game.move_detection import detect_observed_move
from src.ui.qt import QObject, Signal, Slot, QTimer
from src.ui.utils import bgr_to_qimage


CORNER_ORDER = [
    ("A1", "Black Rook on White Square"),
    ("H1", "Black Rook on Black Square"),
    ("H8", "White Rook on White Square"),
    ("A8", "White Rook on Black Square"),
]


class VisionWorker(QObject):
    frame_ready = Signal(object)
    warped_ready = Signal(object)
    status_changed = Signal(object)
    inference_ready = Signal(object)
    error = Signal(object)

    def __init__(
        self,
        camera_index: int = 0,
        model_path: str | None = None,
        camera_backend: int | None = None,
        camera_source: str | None = None,
    ) -> None:
        super().__init__()
        self.camera_index = camera_index
        self.model_path = model_path
        self.camera_backend = camera_backend
        self.camera_source = camera_source
        self._running = False
        self._cap: cv2.VideoCapture | None = None
        self._clicked_corners: list[list[int]] = []
        self._grid_locked = False
        self._last_frame: np.ndarray | None = None
        self._last_warped: np.ndarray | None = None
        self._previous_board_state = np.full((8, 8), "empty", dtype=object)
        self._model = None
        self._timer: QTimer | None = None

    @Slot()
    def start_capture(self) -> None:
        if self._running:
            return
        source = self._resolve_capture_source()
        if self.camera_backend is None:
            self._cap = cv2.VideoCapture(source)
        else:
            self._cap = cv2.VideoCapture(source, self.camera_backend)
        if not self._cap.isOpened():
            backend_label = f" (backend={self.camera_backend})" if self.camera_backend is not None else ""
            source_label = self.camera_source.strip() if self.camera_source else str(self.camera_index)
            self.error.emit(f"Could not open camera source '{source_label}'{backend_label}")
            return
        self._running = True
        self._emit_status()
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._capture_once)
        if not self._timer.isActive():
            self._timer.start(10)

    @Slot()
    def _capture_once(self) -> None:
        if not self._running or self._cap is None:
            return
        ret, frame = self._cap.read()
        if not ret:
            self.error.emit("Failed to grab frame")
            self.stop_capture()
            return
        self._last_frame = frame
        display = frame.copy()
        for point in self._clicked_corners:
            cv2.circle(display, tuple(point), 5, (0, 0, 255), -1)
        self.frame_ready.emit(bgr_to_qimage(display))

        if self._grid_locked:
            warped = self._warp_board(frame)
            if warped is not None:
                self._last_warped = warped
                overlay = self._draw_grid_overlay(warped)
                self.warped_ready.emit(bgr_to_qimage(overlay))

    @Slot()
    def stop_capture(self) -> None:
        if self._timer and self._timer.isActive():
            self._timer.stop()
        self._running = False
        if self._cap:
            self._cap.release()
        self._cap = None
        self._emit_status()

    @Slot()
    def reset_corners(self) -> None:
        self._clicked_corners = []
        self._grid_locked = False
        self._emit_status()

    @Slot(int, int, int, int)
    def add_corner(self, x: int, y: int, display_w: int, display_h: int) -> None:
        if self._grid_locked or self._last_frame is None:
            return
        frame_h, frame_w = self._last_frame.shape[:2]
        if display_w == 0 or display_h == 0:
            return
        scale_x = frame_w / display_w
        scale_y = frame_h / display_h
        mapped_x = int(x * scale_x)
        mapped_y = int(y * scale_y)
        self._clicked_corners.append([mapped_x, mapped_y])
        if len(self._clicked_corners) >= 4:
            self._grid_locked = True
        self._emit_status()

    @Slot()
    def request_inference(self) -> None:
        if not self._grid_locked or self._last_warped is None:
            self.error.emit("Corners not locked or warped board unavailable")
            return
        try:
            board_state = self._run_inference(self._last_warped)
        except Exception as exc:
            self.error.emit(f"Inference failed: {exc}")
            return
        detected_move = detect_observed_move(self._previous_board_state, board_state)
        self._previous_board_state = board_state.copy()
        overlay = self._draw_classification_overlay(self._last_warped, board_state)
        self.inference_ready.emit(
            {
                "board_state": board_state,
                "detected_move": detected_move,
                "overlay": bgr_to_qimage(overlay),
            }
        )

    def _emit_status(self) -> None:
        self.status_changed.emit(
            {
                "camera_connected": self._running,
                "corners_selected": len(self._clicked_corners),
                "grid_locked": self._grid_locked,
                "corner_label": CORNER_ORDER[len(self._clicked_corners)][0]
                if len(self._clicked_corners) < 4
                else "Locked",
            }
        )

    def _resolve_capture_source(self) -> int | str:
        if self.camera_source is None:
            return self.camera_index
        source = self.camera_source.strip()
        if not source:
            return self.camera_index
        try:
            return int(source)
        except ValueError:
            return source

    def _warp_board(self, frame: np.ndarray) -> np.ndarray | None:
        if len(self._clicked_corners) != 4:
            return None
        board_size = 400
        dest_corners = np.array(
            [[0, 0], [board_size - 1, 0], [board_size - 1, board_size - 1], [0, board_size - 1]],
            dtype="float32",
        )
        matrix = cv2.getPerspectiveTransform(np.array(self._clicked_corners, dtype="float32"), dest_corners)
        return cv2.warpPerspective(frame, matrix, (board_size, board_size))

    def _draw_grid_overlay(self, warped: np.ndarray) -> np.ndarray:
        board = warped.copy()
        board_size = board.shape[0]
        step = board_size // 8
        for i in range(9):
            cv2.line(board, (0, i * step), (board_size, i * step), (0, 255, 0), 1)
            cv2.line(board, (i * step, 0), (i * step, board_size), (0, 255, 0), 1)
        return board

    def _draw_classification_overlay(self, warped: np.ndarray, board_state: np.ndarray) -> np.ndarray:
        overlay = self._draw_grid_overlay(warped)
        step = overlay.shape[0] // 8
        for i in range(8):
            for j in range(8):
                label = board_state[i, j]
                cv2.putText(
                    overlay,
                    label,
                    (j * step + 5, (i + 1) * step - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35,
                    (0, 255, 255),
                    1,
                )
        return overlay

    def _load_model(self):
        if self._model is not None:
            return self._model
        model_path = self.model_path or str(Path("models") / "chess_piece_classifier_v7.h5")
        from tensorflow.keras import models

        # `compile=False` avoids rebuilding training-related state/metrics in runtime inference,
        # which reduces startup noise and avoids some Keras graph interactions in Qt worker threads.
        self._model = models.load_model(model_path, compile=False)
        return self._model

    def _run_inference(self, warped: np.ndarray) -> np.ndarray:
        model = self._load_model()
        from src.vision.preprocessing import preprocess_square_enhanced_v7

        board_state = np.empty((8, 8), dtype=object)
        categories = ["empty", "black", "white"]
        board_size = warped.shape[0]
        step = board_size // 8
        squares = []
        for i in range(8):
            for j in range(8):
                y1, y2 = i * step, (i + 1) * step
                x1, x2 = j * step, (j + 1) * step
                square_img = warped[y1:y2, x1:x2]
                squares.append(preprocess_square_enhanced_v7(square_img, add_batch_dim=False))
        batch = np.stack(squares, axis=0)
        # Call the model directly (eager path) instead of `predict()`, which is heavier and can
        # be less stable in background Qt threads on macOS.
        outputs = model(batch, training=False)
        predictions = outputs.numpy() if hasattr(outputs, "numpy") else np.asarray(outputs)
        k = 0
        for i in range(8):
            for j in range(8):
                class_idx = int(np.argmax(predictions[k]))
                board_state[i, j] = categories[class_idx]
                k += 1
        return board_state


@dataclass
class RobotExecutionPayload:
    plan: object
    adapter: object
    kinematics: object


class RobotExecutionWorker(QObject):
    progress = Signal(object)
    finished = Signal()
    error = Signal(object)
    gripper = Signal(object)

    def __init__(self, payload: RobotExecutionPayload) -> None:
        super().__init__()
        self.payload = payload
        self._stop = False

    @Slot()
    def run(self) -> None:
        plan = self.payload.plan
        adapter = self.payload.adapter
        kinematics = self.payload.kinematics
        try:
            adapter.connect()
            for segment in plan.segments:
                if self._stop:
                    break
                if segment.name == "gripper":
                    label = segment.waypoints[0].label if segment.waypoints else ""
                    action = "open" if "open" in label else "close"
                    if action == "open":
                        adapter.open_gripper()
                    else:
                        adapter.close_gripper()
                    self.gripper.emit(action)
                    continue
                for waypoint in segment.waypoints:
                    if self._stop:
                        break
                    joint_targets = kinematics.solve_cartesian_to_joint(waypoint.pose)
                    adapter.send_joint_positions(joint_targets.to_dict(), speed_mm_s=waypoint.speed_mm_s)
                    self.progress.emit({"pose": waypoint.pose, "label": waypoint.label})
                    time.sleep(0.2)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            try:
                adapter.disconnect()
            except Exception:
                pass
            self.finished.emit()

    @Slot()
    def stop(self) -> None:
        self._stop = True
