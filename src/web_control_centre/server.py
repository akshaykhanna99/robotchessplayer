"""Lightweight local web command-centre server."""

from __future__ import annotations

from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any
from urllib.parse import urlparse

import cv2
import numpy as np

from src.game.engine import StockfishEngineClient
from src.game.session import ChessGameSession
from src.game.move_detection import detect_observed_move
from src.robot.adapters.pca9686_serial_robot import Pca9686SerialRobotArm
from src.robot.config import load_physical_setup_config
from src.robot.kinematics import SimpleArmKinematics
from src.robot.web_kinematics import WebKinematicsModel


HOST = os.getenv("WEB_CONTROL_CENTRE_HOST", "127.0.0.1")
PORT = int(os.getenv("WEB_CONTROL_CENTRE_PORT", "8765"))
UPDATE_INTERVAL_S = 0.05
CAMERA_SCAN_INDICES = range(4)
DEFAULT_CAMERA_SOURCE = os.getenv("WEB_CONTROL_CENTRE_DEFAULT_CAMERA", "Camera 0")
MJPEG_BOUNDARY = "frame"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAINING_DATASET = os.getenv("WEB_CONTROL_CENTRE_TRAINING_DATASET", "chess_dataset_web")
DEFAULT_ACTIVE_CLASSIFIER = os.getenv("WEB_CONTROL_CENTRE_ACTIVE_CLASSIFIER", "models/chess_piece_classifier_v7.h5")
DEFAULT_STOCKFISH_PATH = os.getenv("WEB_CONTROL_CENTRE_STOCKFISH_PATH", "/usr/local/bin/stockfish")
DEFAULT_DIGITAL_TWIN_CONFIG = os.getenv(
    "WEB_CONTROL_CENTRE_DIGITAL_TWIN_CONFIG",
    str(PROJECT_ROOT / "config" / "digital_twin_setup_v1.json"),
)
DEFAULT_PHYSICAL_SETUP_CONFIG = os.getenv(
    "WEB_CONTROL_CENTRE_PHYSICAL_SETUP_CONFIG",
    str(PROJECT_ROOT / "config" / "physical_setup_v1.json"),
)
DEFAULT_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
TRAINING_LABEL_TO_FOLDER = {
    "empty": "empty",
    "black": "black_piece",
    "white": "white_piece",
}
INFERENCE_CATEGORIES = ["empty", "black", "white"]
STANDARD_START_OBSERVED_STATE = np.array(
    [
        ["black"] * 8,
        ["black"] * 8,
        ["empty"] * 8,
        ["empty"] * 8,
        ["empty"] * 8,
        ["empty"] * 8,
        ["white"] * 8,
        ["white"] * 8,
    ],
    dtype=object,
)


@dataclass
class JointState:
    label: str
    minimum: int
    maximum: int
    current: float
    target: float
    velocity: float = 0.0
    max_speed: float = 3.0
    max_accel: float = 0.45

    def to_dict(self, telemetry: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "label": self.label,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "current": round(self.current, 1),
            "target": round(self.target, 1),
            "velocity": round(self.velocity, 2),
        }
        if telemetry:
            payload.update(telemetry)
        return payload


@dataclass
class CommandCentreState:
    mode: str = "Vision + Game + Robot"
    setup_name: str = "Bench Prototype Alpha"
    robot_name: str = "PCA9686 Arm"
    serial_port: str = "/dev/tty.usbmodem143301"
    camera_source: str = "Camera 0"
    available_cameras: list[str] = field(default_factory=list)
    camera_connected: bool = False
    corners_selected: int = 0
    grid_locked: bool = False
    corner_selection_active: bool = False
    clicked_corners: list[tuple[float, float]] = field(default_factory=list)
    next_corner_label: str = "A1"
    next_corner_hint: str = "Bottom-left corner from White's perspective"
    side_to_move: str = "White"
    detected_move: str = "-"
    suggested_move: str = "-"
    fen: str = DEFAULT_START_FEN
    executing: bool = False
    gripper_state: str = "open"
    control_target: str = "virtual"
    hardware_available: bool = False
    hardware_status: str = "Hardware control unavailable"
    board_origin_mm: tuple[float, float] = (118.0, 86.0)
    square_size_mm: float = 38.0
    last_action: str = "Initialised web command centre"
    logs: list[dict[str, str]] = field(default_factory=list)
    joints: dict[str, JointState] = field(default_factory=dict)
    training_snapshot_count: int = 0
    training_active_snapshot_index: int = -1
    training_label_mode: str = "white"
    training_revision: int = 0
    training_saved_snapshot_count: int = 0
    training_dataset_path: str = DEFAULT_TRAINING_DATASET
    training_job_status: str = "idle"
    training_job_message: str = "No training run started"
    training_job_output_model: str = ""
    active_classifier_path: str = DEFAULT_ACTIVE_CLASSIFIER
    available_classifiers: list[str] = field(default_factory=list)
    joint_telemetry: dict[str, dict[str, Any]] = field(default_factory=dict)
    ik_test_square: str = "e4"
    ik_test_status: str = "idle"
    ik_test_message: str = "Choose a square to solve inverse kinematics."
    ik_test_active_joint: str | None = None
    ik_test_step_index: int = 0
    ik_test_step_total: int = 0
    ik_test_pose: dict[str, float] | None = None
    ik_test_joint_deg: dict[str, float] | None = None

    def snapshot(self) -> dict[str, Any]:
        joint_payload = {}
        for name, joint in self.joints.items():
            telemetry = self.joint_telemetry.get(name)
            joint_payload[name] = joint.to_dict(telemetry)
        return {
            "system": {
                "mode": self.mode,
                "setup_name": self.setup_name,
                "robot_name": self.robot_name,
                "serial_port": self.serial_port,
                "camera_source": self.camera_source,
                "available_cameras": self.available_cameras,
                "last_action": self.last_action,
            },
            "vision": {
                "camera_connected": self.camera_connected,
                "corners_selected": self.corners_selected,
                "grid_locked": self.grid_locked,
                "corner_selection_active": self.corner_selection_active,
                "board_initialized": self.grid_locked and len(self.clicked_corners) == 4,
                "next_corner_label": self.next_corner_label,
                "next_corner_hint": self.next_corner_hint,
                "stream_url": "/api/camera/stream",
                "board_stream_url": "/api/board/stream",
            },
            "game": {
                "side_to_move": self.side_to_move,
                "detected_move": self.detected_move,
                "suggested_move": self.suggested_move,
                "fen": self.fen,
                "observed_board": [],
                "observed_board_initialized": False,
                "session_active": False,
            },
            "robot": {
                "executing": self.executing,
                "gripper_state": self.gripper_state,
                "control_target": self.control_target,
                "hardware_available": self.hardware_available,
                "hardware_status": self.hardware_status,
            },
            "board": {
                "origin_x_mm": self.board_origin_mm[0],
                "origin_y_mm": self.board_origin_mm[1],
                "square_size_mm": self.square_size_mm,
            },
            "training": {
                "snapshot_count": self.training_snapshot_count,
                "active_snapshot_index": self.training_active_snapshot_index,
                "label_mode": self.training_label_mode,
                "revision": self.training_revision,
                "saved_snapshot_count": self.training_saved_snapshot_count,
                "active_snapshot_url": "/api/training/active-snapshot",
                "dataset_path": self.training_dataset_path,
                "job_status": self.training_job_status,
                "job_message": self.training_job_message,
                "job_output_model": self.training_job_output_model,
            },
            "settings": {
                "active_classifier_path": self.active_classifier_path,
                "available_classifiers": self.available_classifiers,
            },
            "ik_test": {
                "square": self.ik_test_square,
                "status": self.ik_test_status,
                "message": self.ik_test_message,
                "active_joint": self.ik_test_active_joint,
                "step_index": self.ik_test_step_index,
                "step_total": self.ik_test_step_total,
                "pose": self.ik_test_pose,
                "joint_deg": self.ik_test_joint_deg,
            },
            "joints": joint_payload,
            "logs": self.logs[-14:],
        }


@dataclass
class TrainingSnapshot:
    image: np.ndarray
    labels: np.ndarray
    saved: bool = False


@dataclass
class BoardInferenceResult:
    board_state: np.ndarray
    probabilities: np.ndarray


class CameraManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._capture_thread: threading.Thread | None = None
        self._cap: cv2.VideoCapture | None = None
        self._current_source: int | None = None
        self._latest_jpeg: bytes | None = None
        self._latest_frame: np.ndarray | None = None
        self._latest_frame_event = threading.Event()

    def list_sources(self) -> list[str]:
        # Do not probe every device at startup on macOS. Aggressive probing can wake
        # Continuity Camera and trigger unwanted iPhone connection attempts.
        return [f"Camera {index}" for index in CAMERA_SCAN_INDICES]

    def start(self, source_label: str) -> tuple[bool, str]:
        source_index = self._label_to_index(source_label)
        with self._lock:
            if self._current_source == source_index and self._cap is not None:
                return True, "Camera already active"
            self._release_locked()
            cap = cv2.VideoCapture(source_index)
            if not cap.isOpened():
                cap.release()
                return False, f"Could not open {source_label}"
            self._cap = cap
            self._current_source = source_index
            self._latest_jpeg = None
            self._latest_frame_event.clear()
            self._stop_event.clear()
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()
        return True, f"{source_label} connected"

    def stop(self) -> None:
        with self._lock:
            thread = self._capture_thread
            self._stop_event.set()
            self._release_locked()
        if thread is not None:
            thread.join(timeout=1.0)
        with self._lock:
            self._capture_thread = None
            self._stop_event.clear()

    def is_running(self) -> bool:
        with self._lock:
            return self._cap is not None

    def get_latest_jpeg(self, timeout_s: float = 2.0) -> bytes | None:
        self._latest_frame_event.wait(timeout_s)
        with self._lock:
            return self._latest_jpeg

    def get_latest_frame(self, timeout_s: float = 2.0) -> np.ndarray | None:
        self._latest_frame_event.wait(timeout_s)
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def _capture_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                cap = self._cap
            if cap is None:
                break
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue
            encoded_ok, jpeg = cv2.imencode(".jpg", frame)
            if not encoded_ok:
                continue
            with self._lock:
                self._latest_jpeg = jpeg.tobytes()
                self._latest_frame = frame.copy()
            self._latest_frame_event.set()
            time.sleep(0.03)

    def _release_locked(self) -> None:
        if self._cap is not None:
            self._cap.release()
        self._cap = None
        self._current_source = None
        self._latest_jpeg = None
        self._latest_frame = None
        self._latest_frame_event.clear()

    @staticmethod
    def _label_to_index(source_label: str) -> int:
        if source_label.startswith("Camera "):
            suffix = source_label.removeprefix("Camera ").strip()
            try:
                return int(suffix)
            except ValueError:
                return 0
        try:
            return int(source_label)
        except ValueError:
            return 0


class MockCommandCentre:
    CORNER_SEQUENCE = [
        ("A1", "Bottom-left corner from White's perspective"),
        ("H1", "Bottom-right corner from White's perspective"),
        ("H8", "Top-right corner from White's perspective"),
        ("A8", "Top-left corner from White's perspective"),
    ]

    def __init__(self) -> None:
        self._camera_manager = CameraManager()
        self._web_kinematics = WebKinematicsModel.from_digital_twin_config(DEFAULT_DIGITAL_TWIN_CONFIG)
        self._hardware_robot: Pca9686SerialRobotArm | None = None
        self._hardware_poll_interval_s = 0.35
        self._hardware_poll_block_until_s = 0.0
        self._last_hardware_poll_s = 0.0
        self._ik_joint_order = ["base", "shoulder", "elbow", "wrist"]
        self._ik_pending_targets: dict[str, float] = {}
        self._ik_pending_joint_deg: dict[str, float] = {}
        self._ik_step_cursor = 0
        available_cameras = self._camera_manager.list_sources()
        self._training_snapshots: list[TrainingSnapshot] = []
        self._training_process: subprocess.Popen[str] | None = None
        self._inference_model = None
        self._inference_model_path: str | None = None
        self._previous_observed_board_state = np.full((8, 8), "empty", dtype=object)
        self._play_overlay_state: np.ndarray | None = None
        self._play_overlay_probabilities: np.ndarray | None = None
        self._game_session: ChessGameSession | None = None
        self.state = CommandCentreState(
            camera_source=DEFAULT_CAMERA_SOURCE,
            available_cameras=available_cameras,
            training_dataset_path=DEFAULT_TRAINING_DATASET,
            active_classifier_path=DEFAULT_ACTIVE_CLASSIFIER,
            available_classifiers=self._discover_available_classifiers(),
            logs=[
                {"level": "system", "message": "Loaded Bench Prototype Alpha"},
                {"level": "vision", "message": f"Default camera set to {DEFAULT_CAMERA_SOURCE}."},
                {"level": "robot", "message": "Joint targets set to defaults."},
            ],
            joints={
                "base": JointState("Base", 250, 500, 375.0, 375.0, max_speed=4.0, max_accel=0.65),
                "shoulder": JointState("Shoulder", 250, 500, 375.0, 375.0, max_speed=4.0, max_accel=0.65),
                "elbow": JointState("Elbow", 250, 500, 385.0, 385.0, max_speed=2.8, max_accel=0.35),
                "wrist": JointState("Wrist", 250, 500, 375.0, 375.0, max_speed=4.0, max_accel=0.65),
                "gripper": JointState("Gripper", 180, 340, 340.0, 340.0, max_speed=2.0, max_accel=0.3),
            },
        )
        self._initialize_hardware_robot()
        self._refresh_joint_telemetry_locked()
        self._session_home_joint_deg = self._capture_session_home_from_state()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._normalize_classifier_state()
        ok, message = self._camera_manager.start(DEFAULT_CAMERA_SOURCE)
        self.state.camera_connected = ok
        if ok:
            self.state.last_action = f"Camera source set to {DEFAULT_CAMERA_SOURCE}"
            self._append_log("vision", f"{DEFAULT_CAMERA_SOURCE} connected")
        else:
            self.state.last_action = "Default camera connection failed"
            self._append_log("error", message)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._camera_manager.stop()
        if self._hardware_robot is not None:
            try:
                self._hardware_robot.disconnect()
            except Exception:
                pass
        self._thread.join(timeout=1.0)

    def _initialize_hardware_robot(self) -> None:
        config_path = Path(DEFAULT_PHYSICAL_SETUP_CONFIG)
        if not DEFAULT_PHYSICAL_SETUP_CONFIG or not config_path.exists():
            self.state.hardware_available = False
            self.state.hardware_status = "No physical setup config configured"
            return
        try:
            setup = load_physical_setup_config(config_path)
            kinematics = SimpleArmKinematics.from_robot_config(setup.robot)
            robot = Pca9686SerialRobotArm(config=setup.robot, kinematics=kinematics)
            robot.connect()
        except Exception as exc:
            self._hardware_robot = None
            self.state.hardware_available = False
            self.state.hardware_status = f"Hardware unavailable: {exc}"
            self._append_log("error", self.state.hardware_status)
            return

        self._hardware_robot = robot
        self._apply_hardware_joint_profile(setup)
        self.state.hardware_available = True
        self.state.setup_name = setup.setup_name
        self.state.robot_name = setup.robot.name
        self.state.serial_port = setup.robot.transport.port
        self.state.hardware_status = f"Connected on {setup.robot.transport.port}"
        self._append_log("robot", f"Hardware adapter connected on {setup.robot.transport.port}")

    def _apply_hardware_joint_profile(self, setup) -> None:
        calibration = setup.robot.calibration
        if calibration is None:
            return
        pulse_limits = calibration.pulse_limits
        for joint_name, pulse_range in pulse_limits.items():
            joint = self.state.joints.get(joint_name)
            if joint is None:
                continue
            joint.minimum = int(round(pulse_range.min_pulse))
            joint.maximum = int(round(pulse_range.max_pulse))
            joint.current = float(pulse_range.home_pulse)
            joint.target = float(pulse_range.home_pulse)
            joint.velocity = 0.0

    def _capture_session_home_from_state(self) -> dict[str, float]:
        home: dict[str, float] = {}
        for name, telemetry in self.state.joint_telemetry.items():
            value = telemetry.get("target_deg", telemetry.get("current_deg"))
            if value is None:
                continue
            home[name] = float(value)
        return home

    def _gripper_target_pulse_locked(self, closed: bool) -> float:
        joint = self.state.joints["gripper"]
        if self._hardware_robot is not None and self._hardware_robot.config.gripper:
            calibration = self._hardware_robot.config.calibration
            pulse_limits = calibration.pulse_limits.get("gripper") if calibration else None
            gripper_config = self._hardware_robot.config.gripper
            if pulse_limits is not None:
                open_deg = float(gripper_config.open_deg)
                close_deg = float(gripper_config.close_deg)
                open_pulse = float(pulse_limits.max_pulse)
                close_pulse = float(pulse_limits.min_pulse)
                angle = close_deg if closed else open_deg
                if abs(close_deg - open_deg) < 1e-6:
                    pulse = close_pulse if closed else open_pulse
                else:
                    ratio = (angle - open_deg) / (close_deg - open_deg)
                    pulse = open_pulse + ratio * (close_pulse - open_pulse)
                return float(max(joint.minimum, min(joint.maximum, round(pulse))))
        return 180.0 if closed else 340.0

    def _send_targets_to_hardware_locked(self, joint_names: list[str] | None = None) -> tuple[bool, str]:
        if self._hardware_robot is None or not self.state.hardware_available:
            return False, self.state.hardware_status
        try:
            protocol = self._hardware_robot.config.transport.protocol.strip().lower()
            if protocol == "channel_pulse":
                if joint_names is None:
                    joint_targets = {name: joint.target for name, joint in self.state.joints.items()}
                else:
                    joint_targets = {
                        name: self.state.joints[name].target for name in joint_names if name in self.state.joints
                    }
                self._hardware_robot.send_joint_pulses(joint_targets)
            else:
                full_joint_targets = self._web_kinematics.target_joint_degrees_from_pulses(self.state.joints)
                if joint_names is None:
                    joint_targets = full_joint_targets
                else:
                    joint_targets = {name: full_joint_targets[name] for name in joint_names if name in full_joint_targets}
                self._hardware_robot.send_joint_positions(joint_targets)
            self._hardware_poll_block_until_s = time.time() + 0.25
        except Exception as exc:
            self.state.hardware_status = f"Hardware command failed: {exc}"
            self.state.hardware_available = False
            self._append_log("error", self.state.hardware_status)
            return False, self.state.hardware_status
        return True, "ok"

    def _refresh_hardware_joint_currents_locked(self) -> None:
        if self._hardware_robot is None or not self.state.hardware_available:
            return
        try:
            channel_pulses = self._hardware_robot.read_channel_pulses()
        except Exception as exc:
            self.state.hardware_status = f"Hardware status failed: {exc}"
            self._append_log("error", self.state.hardware_status)
            return

        channel_map = {
            "base": self._hardware_robot.config.channels.base,
            "shoulder": self._hardware_robot.config.channels.shoulder,
            "elbow": self._hardware_robot.config.channels.elbow,
            "wrist": self._hardware_robot.config.channels.wrist,
            "gripper": self._hardware_robot.config.channels.gripper,
        }
        for joint_name, channel in channel_map.items():
            if channel not in channel_pulses or joint_name not in self.state.joints:
                continue
            joint = self.state.joints[joint_name]
            joint.current = float(channel_pulses[channel])
            joint.velocity = 0.0

    def set_joint_angle_target(self, name: str, degrees: float) -> tuple[bool, str]:
        with self._lock:
            joint = self.state.joints.get(name)
            if joint is None:
                return False, f"Unknown joint '{name}'"
            if self.state.control_target == "virtual" and name == "wrist":
                return False, "Wrist is auto-leveled in virtual mode"
            telemetry = self.state.joint_telemetry.get(name)
            minimum_deg = telemetry["minimum_deg"] if telemetry else None
            maximum_deg = telemetry["maximum_deg"] if telemetry else None
            if minimum_deg is None or maximum_deg is None:
                return False, f"No degree mapping configured for joint '{name}'"
            clamped_deg = max(float(minimum_deg), min(float(maximum_deg), float(degrees)))
            pulse = self._web_kinematics.degrees_to_pulse(name, clamped_deg, joint.minimum, joint.maximum)
            joint.target = float(max(joint.minimum, min(joint.maximum, round(pulse))))
            if self.state.control_target == "virtual" and name in {"shoulder", "elbow"}:
                shoulder_joint = self.state.joints.get("shoulder")
                elbow_joint = self.state.joints.get("elbow")
                wrist_joint = self.state.joints.get("wrist")
                if shoulder_joint is not None and elbow_joint is not None and wrist_joint is not None:
                    shoulder_deg = self._web_kinematics.pulse_to_degrees(
                        "shoulder", shoulder_joint.target, shoulder_joint.minimum, shoulder_joint.maximum
                    )
                    elbow_deg = self._web_kinematics.pulse_to_degrees(
                        "elbow", elbow_joint.target, elbow_joint.minimum, elbow_joint.maximum
                    )
                    wrist_deg = self._web_kinematics.auto_wrist_degrees(shoulder_deg, elbow_deg)
                    wrist_pulse = self._web_kinematics.degrees_to_pulse(
                        "wrist", wrist_deg, wrist_joint.minimum, wrist_joint.maximum
                    )
                    wrist_joint.target = float(max(wrist_joint.minimum, min(wrist_joint.maximum, round(wrist_pulse))))
            self._refresh_joint_telemetry_locked()
            self.state.last_action = f"Updated {joint.label} target angle"
            self._append_log("robot", f"{joint.label} target set to {clamped_deg:.1f} deg")
            if self.state.control_target == "hardware":
                ok, message = self._send_targets_to_hardware_locked([name])
                if not ok:
                    return False, message
        return True, "ok"

    def save_session_home(self) -> tuple[bool, str]:
        with self._lock:
            self._refresh_joint_telemetry_locked()
            self._session_home_joint_deg = self._capture_session_home_from_state()
            self.state.last_action = "Saved session home pose"
            self._append_log("robot", "Session home pose saved")
        return True, "ok"

    def go_to_session_home(self) -> tuple[bool, str]:
        with self._lock:
            if not self._session_home_joint_deg:
                return False, "No session home pose saved"
            for joint_name, degrees in self._session_home_joint_deg.items():
                joint = self.state.joints.get(joint_name)
                if joint is None:
                    continue
                pulse = self._web_kinematics.degrees_to_pulse(joint_name, degrees, joint.minimum, joint.maximum)
                joint.target = float(max(joint.minimum, min(joint.maximum, round(pulse))))
            self._refresh_joint_telemetry_locked()
            self.state.last_action = "Moving to session home pose"
            self._append_log("robot", "Moving to session home pose")
            if self.state.control_target == "hardware":
                ok, message = self._send_targets_to_hardware_locked()
                if not ok:
                    return False, message
        return True, "ok"

    def _refresh_joint_telemetry_locked(self) -> None:
        telemetry: dict[str, dict[str, Any]] = {}
        for name, joint in self.state.joints.items():
            joint_telemetry = self._web_kinematics.telemetry_for_joint(
                name=name,
                current=joint.current,
                target=joint.target,
                pulse_min=joint.minimum,
                pulse_max=joint.maximum,
                virtual_auto_wrist=self.state.control_target == "virtual",
            )
            if joint_telemetry is None:
                continue
            telemetry[name] = {
                "minimum_deg": round(joint_telemetry.minimum_deg, 1),
                "maximum_deg": round(joint_telemetry.maximum_deg, 1),
                "target_deg": round(joint_telemetry.target_deg, 1),
                "current_deg": round(joint_telemetry.current_deg, 1),
                "control_mode": joint_telemetry.control_mode,
            }
        self.state.joint_telemetry = telemetry

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._refresh_joint_telemetry_locked()
            self.state.camera_connected = self._camera_manager.is_running()
            self.state.training_snapshot_count = len(self._training_snapshots)
            self.state.training_saved_snapshot_count = sum(1 for snapshot in self._training_snapshots if snapshot.saved)
            self.state.available_classifiers = self._discover_available_classifiers()
            self._normalize_classifier_state()
            payload = self.state.snapshot()
            if self._play_overlay_state is not None:
                payload["game"]["observed_board"] = self._play_overlay_state.tolist()
                payload["game"]["observed_board_initialized"] = True
            payload["game"]["session_active"] = self._game_session is not None
            return payload

    def get_latest_camera_frame(self) -> bytes | None:
        frame = self._camera_manager.get_latest_frame()
        if frame is None:
            return None
        with self._lock:
            corners = list(self.state.clicked_corners)
            next_corner_label = self.state.next_corner_label
            selecting = self.state.corner_selection_active
            grid_locked = self.state.grid_locked
        annotated = self._draw_camera_overlay(
            frame,
            normalized_corners=corners,
            selecting=selecting,
            grid_locked=grid_locked,
            next_corner_label=next_corner_label,
        )
        encoded_ok, jpeg = cv2.imencode(".jpg", annotated)
        if not encoded_ok:
            return None
        return jpeg.tobytes()

    def get_latest_board_frame(self) -> bytes | None:
        frame = self._camera_manager.get_latest_frame()
        if frame is None:
            return None
        with self._lock:
            corners = list(self.state.clicked_corners)
            grid_locked = self.state.grid_locked
            play_overlay_state = None if self._play_overlay_state is None else self._play_overlay_state.copy()
            play_overlay_probabilities = (
                None if self._play_overlay_probabilities is None else self._play_overlay_probabilities.copy()
            )
        if not grid_locked or len(corners) != 4:
            return None
        warped = self._warp_board(frame, corners)
        if warped is None:
            return None
        gridded = self._draw_board_grid_overlay(warped)
        if play_overlay_state is not None:
            gridded = self._draw_play_inference_overlay(gridded, play_overlay_state, play_overlay_probabilities)
        encoded_ok, jpeg = cv2.imencode(".jpg", gridded)
        if not encoded_ok:
            return None
        return jpeg.tobytes()

    def get_active_training_snapshot_frame(self) -> bytes | None:
        with self._lock:
            snapshot = self._get_active_training_snapshot_locked()
            if snapshot is None:
                return None
            rendered = self._draw_training_snapshot_overlay(snapshot)
        encoded_ok, jpeg = cv2.imencode(".jpg", rendered)
        if not encoded_ok:
            return None
        return jpeg.tobytes()

    def set_joint_target(self, name: str, value: float) -> tuple[bool, str]:
        with self._lock:
            joint = self.state.joints.get(name)
            if joint is None:
                return False, f"Unknown joint '{name}'"
            joint.target = float(max(joint.minimum, min(joint.maximum, round(value))))
            self._refresh_joint_telemetry_locked()
            self.state.last_action = f"Updated {joint.label} target"
            self._append_log("robot", f"{joint.label} target set to {int(joint.target)}")
            if self.state.control_target == "hardware":
                ok, message = self._send_targets_to_hardware_locked()
                if not ok:
                    return False, message
        return True, "ok"

    def set_control_target(self, target: str) -> tuple[bool, str]:
        normalized = target.strip().lower()
        if normalized not in {"virtual", "hardware"}:
            return False, f"Unknown control target '{target}'"
        with self._lock:
            if normalized == "hardware" and not self.state.hardware_available:
                return False, self.state.hardware_status
            self.state.control_target = normalized
            if normalized == "virtual":
                shoulder_joint = self.state.joints.get("shoulder")
                elbow_joint = self.state.joints.get("elbow")
                wrist_joint = self.state.joints.get("wrist")
                if shoulder_joint is not None and elbow_joint is not None and wrist_joint is not None:
                    shoulder_deg = self._web_kinematics.pulse_to_degrees(
                        "shoulder", shoulder_joint.target, shoulder_joint.minimum, shoulder_joint.maximum
                    )
                    elbow_deg = self._web_kinematics.pulse_to_degrees(
                        "elbow", elbow_joint.target, elbow_joint.minimum, elbow_joint.maximum
                    )
                    wrist_deg = self._web_kinematics.auto_wrist_degrees(shoulder_deg, elbow_deg)
                    wrist_pulse = self._web_kinematics.degrees_to_pulse(
                        "wrist", wrist_deg, wrist_joint.minimum, wrist_joint.maximum
                    )
                    wrist_joint.target = float(max(wrist_joint.minimum, min(wrist_joint.maximum, round(wrist_pulse))))
                    self._refresh_joint_telemetry_locked()
            self.state.last_action = f"Control target set to {normalized}"
            self._append_log("robot", f"Control target set to {normalized}")
            if normalized == "hardware":
                ok, message = self._send_targets_to_hardware_locked()
                if not ok:
                    return False, message
        return True, "ok"

    def solve_square_inverse_kinematics(self, square: str) -> tuple[bool, str]:
        normalized = square.strip().lower()
        if not normalized:
            return False, "Square is required"
        try:
            pose, solved = self._web_kinematics.solve_square_pickup(normalized)
        except Exception as exc:
            with self._lock:
                self.state.ik_test_square = normalized
                self.state.ik_test_status = "error"
                self.state.ik_test_message = str(exc)
                self.state.ik_test_active_joint = None
                self.state.ik_test_step_index = 0
                self.state.ik_test_step_total = 0
                self.state.ik_test_pose = None
                self.state.ik_test_joint_deg = None
                self._ik_pending_targets = {}
                self._ik_pending_joint_deg = {}
                self._ik_step_cursor = 0
                self._append_log("error", f"IK solve failed for {normalized}: {exc}")
            return False, str(exc)

        with self._lock:
            pending_targets: dict[str, float] = {}
            for name, angle in solved.to_dict().items():
                joint = self.state.joints.get(name)
                if joint is None or not self._web_kinematics.has_joint(name):
                    continue
                pulse = self._web_kinematics.degrees_to_pulse(name, angle, joint.minimum, joint.maximum)
                pending_targets[name] = float(max(joint.minimum, min(joint.maximum, round(pulse))))
            self._ik_pending_targets = pending_targets
            self._ik_pending_joint_deg = solved.to_dict()
            self._ik_step_cursor = 0
            for name, angle in solved.to_dict().items():
                if name not in self._ik_pending_joint_deg:
                    continue
            self.state.ik_test_square = normalized
            self.state.ik_test_status = "ready"
            self.state.ik_test_message = f"Solution staged for {normalized}. Apply one joint at a time."
            self.state.ik_test_active_joint = self._ik_joint_order[0] if self._ik_pending_targets else None
            self.state.ik_test_step_index = 0
            self.state.ik_test_step_total = len(self._ik_pending_targets)
            self.state.ik_test_pose = {
                "x_mm": round(pose.x_mm, 1),
                "y_mm": round(pose.y_mm, 1),
                "z_mm": round(pose.z_mm, 1),
            }
            self.state.ik_test_joint_deg = {name: round(angle, 1) for name, angle in solved.to_dict().items()}
            self.state.last_action = f"IK square test staged for {normalized}"
            self._append_log("robot", f"IK square test staged for {normalized}")
        return True, "ok"

    def advance_square_inverse_kinematics(self) -> tuple[bool, str]:
        with self._lock:
            while self._ik_step_cursor < len(self._ik_joint_order):
                joint_name = self._ik_joint_order[self._ik_step_cursor]
                self._ik_step_cursor += 1
                if joint_name not in self._ik_pending_targets:
                    continue
                joint = self.state.joints.get(joint_name)
                if joint is None:
                    continue
                joint.target = self._ik_pending_targets[joint_name]
                self._refresh_joint_telemetry_locked()
                self.state.ik_test_step_index = self._ik_step_cursor
                remaining = [
                    name for name in self._ik_joint_order[self._ik_step_cursor :] if name in self._ik_pending_targets
                ]
                self.state.ik_test_active_joint = remaining[0] if remaining else None
                self.state.ik_test_status = "stepping" if remaining else "complete"
                self.state.ik_test_message = (
                    f"Applied {joint_name}. Click Next Joint to continue."
                    if remaining
                    else "All staged joints applied."
                )
                self.state.last_action = f"IK joint step applied: {joint_name}"
                self._append_log("robot", f"IK staged joint applied: {joint_name}")
                return True, "ok"

            self.state.ik_test_status = "complete"
            self.state.ik_test_active_joint = None
            self.state.ik_test_message = "All staged joints already applied."
            return False, "No more staged joints"

    def set_camera_source(self, source_label: str) -> tuple[bool, str]:
        source = source_label.strip()
        if not source:
            return False, "Camera source is required"
        ok, message = self._camera_manager.start(source)
        with self._lock:
            self.state.available_cameras = self._camera_manager.list_sources()
            if ok:
                self.state.camera_source = source
                self.state.camera_connected = True
                self.state.last_action = f"Camera source set to {source}"
                self._append_log("vision", f"{source} connected")
            else:
                self.state.camera_connected = False
                self.state.last_action = "Camera connection failed"
                self._append_log("error", message)
        return ok, message

    def refresh_camera_sources(self) -> list[str]:
        sources = self._camera_manager.list_sources()
        with self._lock:
            self.state.available_cameras = sources
        return sources

    def trigger_action(self, action: str) -> tuple[bool, str]:
        upper = action.strip().lower()
        if upper == "run_inference":
            with self._lock:
                if not self.state.grid_locked or len(self.state.clicked_corners) != 4:
                    return False, "Select and lock all four board corners first"
                if self._play_overlay_state is None:
                    return False, "Start play mode first to capture the initial board baseline"
            return self.run_play_inference()

        with self._lock:
            if upper == "select_corners":
                self.state.corners_selected = 0
                self.state.grid_locked = False
                self.state.corner_selection_active = True
                self.state.clicked_corners = []
                self._play_overlay_state = None
                self._play_overlay_probabilities = None
                self._reset_game_session_locked()
                self._reset_training_state_locked()
                self._set_next_corner_locked_state()
                self.state.last_action = "Corner selection started"
                self._append_log("vision", "Corner selection mode enabled")
                return True, "ok"
            if upper == "reset_corners":
                self.state.corners_selected = 0
                self.state.grid_locked = False
                self.state.corner_selection_active = False
                self.state.clicked_corners = []
                self._play_overlay_state = None
                self._play_overlay_probabilities = None
                self._reset_game_session_locked()
                self._reset_training_state_locked()
                self._set_next_corner_locked_state()
                self.state.last_action = "Vision corners reset"
                self._append_log("vision", "Board corners reset")
                return True, "ok"
            if upper == "reset_board":
                self._previous_observed_board_state = np.full((8, 8), "empty", dtype=object)
                self._play_overlay_state = None
                self._play_overlay_probabilities = None
                self._reset_game_session_locked()
                self.state.last_action = "Tracked board reset"
                self._append_log("vision", "Tracked board reset. Press Play to capture a new baseline.")
                return True, "ok"
            if upper == "toggle_execution":
                self.state.executing = not self.state.executing
                self.state.last_action = "Robot execution toggled"
                status = "started" if self.state.executing else "paused"
                self._append_log("robot", f"Robot execution {status}")
                return True, "ok"
            if upper == "reset_pose":
                for joint in self.state.joints.values():
                    joint.target = joint.current
                for name, joint in self.state.joints.items():
                    if self._web_kinematics.has_joint(name):
                        joint.target = self._web_kinematics.home_pulse(name, joint.minimum, joint.maximum)
                coupled_targets = self._web_kinematics.maybe_apply_coupled_targets(self.state.joints, "shoulder")
                for joint_name, target in coupled_targets.items():
                    if joint_name in self.state.joints:
                        self.state.joints[joint_name].target = float(target)
                self.state.joints["gripper"].target = 340.0
                self._refresh_joint_telemetry_locked()
                self.state.last_action = "Resetting joints to defaults"
                self._append_log("robot", "Resetting all joints to default pose")
                return True, "ok"
            if upper == "toggle_gripper":
                self.state.gripper_state = "closed" if self.state.gripper_state == "open" else "open"
                self.state.joints["gripper"].target = self._gripper_target_pulse_locked(
                    self.state.gripper_state == "closed"
                )
                if self.state.control_target == "hardware":
                    ok, message = self._send_targets_to_hardware_locked(["gripper"])
                    if not ok:
                        return False, message
                self.state.last_action = f"Gripper {self.state.gripper_state}"
                self._append_log("robot", f"Gripper {self.state.gripper_state}")
                return True, "ok"
            if upper == "estop":
                self.state.executing = False
                for joint in self.state.joints.values():
                    joint.target = joint.current
                    joint.velocity = 0.0
                self.state.last_action = "Emergency stop"
                self._append_log("error", "Emergency stop triggered")
                return True, "ok"
        return False, f"Unknown action '{action}'"

    def add_corner_click(self, normalized_x: float, normalized_y: float) -> tuple[bool, str]:
        with self._lock:
            if not self.state.corner_selection_active:
                return False, "Corner selection is not active"
            if self.state.grid_locked:
                return False, "Corners already locked"

            current_index = self.state.corners_selected
            label = self.CORNER_SEQUENCE[current_index][0]
            self.state.clicked_corners.append((normalized_x, normalized_y))
            self.state.corners_selected += 1
            self._append_log(
                "vision",
                f"Captured {label} at ({normalized_x:.3f}, {normalized_y:.3f})",
            )
            if self.state.corners_selected >= len(self.CORNER_SEQUENCE):
                self.state.corners_selected = len(self.CORNER_SEQUENCE)
                self.state.grid_locked = True
                self.state.corner_selection_active = False
                self.state.last_action = "Board corners locked"
                self._append_log("vision", "All four board corners captured")
                self._append_log("vision", "Warped board and 8x8 grid preview enabled")
            else:
                self.state.last_action = f"{label} corner captured"
            self._set_next_corner_locked_state()
            return True, "ok"

    def capture_training_snapshot(self) -> tuple[bool, str]:
        frame = self._camera_manager.get_latest_frame()
        if frame is None:
            return False, "No live camera frame available"
        with self._lock:
            corners = list(self.state.clicked_corners)
            if not self.state.grid_locked or len(corners) != 4:
                return False, "Lock the board corners before capturing training snapshots"
        warped = self._warp_board(frame, corners)
        if warped is None:
            return False, "Could not warp the current board frame"
        with self._lock:
            labels = np.full((8, 8), "", dtype=object)
            self._training_snapshots.append(TrainingSnapshot(image=warped, labels=labels))
            self.state.training_active_snapshot_index = len(self._training_snapshots) - 1
            self.state.training_snapshot_count = len(self._training_snapshots)
            self._bump_training_revision_locked()
            snapshot_num = self.state.training_active_snapshot_index + 1
            self.state.last_action = f"Captured training snapshot {snapshot_num}"
            self._append_log("vision", f"Training snapshot {snapshot_num} captured")
        return True, "ok"

    def set_training_label_mode(self, mode: str) -> tuple[bool, str]:
        normalized = mode.strip().lower()
        if normalized not in TRAINING_LABEL_TO_FOLDER:
            return False, f"Unknown training label mode '{mode}'"
        with self._lock:
            self.state.training_label_mode = normalized
            self._bump_training_revision_locked()
            self.state.last_action = f"Training label mode set to {normalized}"
        return True, "ok"

    def set_active_training_snapshot(self, index: int) -> tuple[bool, str]:
        with self._lock:
            if not self._training_snapshots:
                return False, "No training snapshots captured yet"
            if index < 0 or index >= len(self._training_snapshots):
                return False, f"Training snapshot index {index} is out of range"
            self.state.training_active_snapshot_index = index
            self._bump_training_revision_locked()
            self.state.last_action = f"Viewing training snapshot {index + 1}"
        return True, "ok"

    def annotate_training_square(self, normalized_x: float, normalized_y: float) -> tuple[bool, str]:
        with self._lock:
            snapshot = self._get_active_training_snapshot_locked()
            if snapshot is None:
                return False, "No active training snapshot"
            col = min(max(int(normalized_x * 8), 0), 7)
            row = min(max(int(normalized_y * 8), 0), 7)
            label = self.state.training_label_mode
            current = snapshot.labels[row, col]
            snapshot.labels[row, col] = "" if current == label else label
            snapshot.saved = False
            self._bump_training_revision_locked()
            self.state.last_action = f"Labeled training square {row},{col} as {label}"
        return True, "ok"

    def reset_active_training_snapshot_labels(self) -> tuple[bool, str]:
        with self._lock:
            snapshot = self._get_active_training_snapshot_locked()
            if snapshot is None:
                return False, "No active training snapshot"
            snapshot.labels[:, :] = ""
            snapshot.saved = False
            self._bump_training_revision_locked()
            self.state.last_action = "Training labels reset"
            self._append_log("vision", "Active training snapshot labels reset")
        return True, "ok"

    def complete_active_training_snapshot(self) -> tuple[bool, str]:
        with self._lock:
            snapshot = self._get_active_training_snapshot_locked()
            if snapshot is None:
                return False, "No active training snapshot"
            missing = int(np.count_nonzero(snapshot.labels == ""))
            if missing > 0:
                return False, f"Annotate all 64 squares before saving. {missing} remaining."
            snapshot_index = self.state.training_active_snapshot_index
            image = snapshot.image.copy()
            labels = snapshot.labels.copy()
        saved = self._save_training_snapshot_dataset(snapshot_index, image, labels)
        with self._lock:
            active_snapshot = self._get_active_training_snapshot_locked()
            if active_snapshot is not None:
                active_snapshot.saved = True
            self.state.training_saved_snapshot_count = sum(1 for item in self._training_snapshots if item.saved)
            self._bump_training_revision_locked()
            self.state.last_action = f"Training snapshot {snapshot_index + 1} saved"
            self._append_log("vision", f"Saved training snapshot {snapshot_index + 1} to {saved}")
        return True, "ok"

    def set_training_dataset_path(self, dataset_path: str) -> tuple[bool, str]:
        normalized = dataset_path.strip().strip("/").strip()
        if not normalized:
            return False, "Dataset folder is required"
        if normalized.startswith("..") or "/../" in normalized:
            return False, "Dataset folder must stay within the project directory"
        with self._lock:
            self.state.training_dataset_path = normalized
            self._bump_training_revision_locked()
            self.state.last_action = f"Labelling dataset set to {normalized}"
            self._append_log("vision", f"Labelling dataset path set to {normalized}")
        return True, "ok"

    def start_model_training(self, dataset_path: str, model_name: str) -> tuple[bool, str]:
        dataset_rel = dataset_path.strip().strip("/").strip() or self.state.training_dataset_path
        if dataset_rel.startswith("..") or "/../" in dataset_rel:
            return False, "Training dataset must stay within the project directory"
        dataset_root = PROJECT_ROOT / dataset_rel
        if not dataset_root.exists():
            return False, f"Dataset folder '{dataset_rel}' does not exist"

        model_stem = model_name.strip()
        if not model_stem:
            model_stem = f"classifier_{time.strftime('%Y%m%d_%H%M%S')}"
        if model_stem.endswith(".h5"):
            model_stem = model_stem[:-3]
        if "/" in model_stem or "\\" in model_stem or model_stem.startswith("."):
            return False, "Model name must be a simple file name"
        output_rel = f"models/{model_stem}.h5"

        with self._lock:
            if self.state.training_job_status == "running":
                return False, "A training job is already running"
            self.state.training_job_status = "running"
            self.state.training_job_message = f"Training started using {dataset_rel}"
            self.state.training_job_output_model = output_rel
            self.state.last_action = "Model training started"
            self._append_log("vision", f"Training model {output_rel} from dataset {dataset_rel}")

        command = [
            sys.executable,
            "-m",
            "src.vision.training.modelTraining",
            "--dataset",
            dataset_rel,
            "--variant",
            "enhanced_v7",
            "--output",
            output_rel,
        ]
        thread = threading.Thread(
            target=self._run_training_job,
            args=(command, dataset_rel, output_rel),
            daemon=True,
        )
        thread.start()
        return True, "ok"

    def start_play_mode(self) -> tuple[bool, str]:
        warped, classifier_path, error = self._capture_current_play_board()
        if error is not None or warped is None:
            return False, error or "Could not capture play board"
        try:
            inference = self._run_batched_board_inference(warped, classifier_path)
        except Exception as exc:
            return False, f"Play-mode inference failed: {exc}"
        board_state = inference.board_state

        white_count = int(np.count_nonzero(board_state == "white"))
        black_count = int(np.count_nonzero(board_state == "black"))
        empty_count = int(np.count_nonzero(board_state == "empty"))
        looks_like_standard_start = bool(np.array_equal(board_state, STANDARD_START_OBSERVED_STATE))

        with self._lock:
            self._previous_observed_board_state = board_state.copy()
            self._play_overlay_state = board_state.copy()
            self._play_overlay_probabilities = inference.probabilities.copy()
            self.state.detected_move = "-"
            self.state.suggested_move = "-"
            self.state.side_to_move = "White"
            if looks_like_standard_start:
                self._reset_game_session_locked()
                self._ensure_game_session_locked()
                self.state.fen = DEFAULT_START_FEN
                self._append_log("vision", "Play mode baseline captured as the standard starting position")
                self._append_log("game", "Starting board confirmed. White to move.")
                self._append_log("game", f"Turn: {self.state.side_to_move}")
            else:
                self._reset_game_session_locked()
                self._append_log(
                    "vision",
                    "Play mode baseline captured from observed occupancy. FEN kept unchanged because the classifier only infers empty/black/white.",
                )
            self.state.last_action = "Play mode initial inference completed"
            self._append_log(
                "vision",
                f"Initial play inference using {classifier_path}: white={white_count}, black={black_count}, empty={empty_count}",
            )
        return True, "ok"

    def run_play_inference(self) -> tuple[bool, str]:
        warped, classifier_path, error = self._capture_current_play_board()
        if error is not None or warped is None:
            return False, error or "Could not capture play board"
        try:
            inference = self._run_batched_board_inference(warped, classifier_path)
        except Exception as exc:
            return False, f"Inference failed: {exc}"
        board_state = inference.board_state

        with self._lock:
            previous_state = self._previous_observed_board_state.copy()
        detected_move = detect_observed_move(previous_state, board_state)

        with self._lock:
            self._play_overlay_probabilities = inference.probabilities.copy()
            self.state.detected_move = detected_move or "-"
            if detected_move:
                if self._game_session is None:
                    self._append_log("vision", f"Observed move {detected_move}")
                    self._play_overlay_state = board_state.copy()
                    self._append_log("error", "No active chess session. Re-enter Play from the starting position to track FEN and suggestions.")
                else:
                    accepted, messages = self._game_session.evaluate_detected_move(detected_move, board_state)
                    if messages:
                        for message in messages:
                            self._append_log("game", message)
                    if accepted:
                        self._previous_observed_board_state = board_state.copy()
                        self._play_overlay_state = board_state.copy()
                        self.state.side_to_move = "White" if self._game_session.board.turn else "Black"
                        self.state.fen = self._game_session.board.fen()
                        self.state.suggested_move = self._game_session.black_suggested_move or "-"
                        self._append_log("game", f"Turn: {self.state.side_to_move}")
                    else:
                        # Keep the last valid observed baseline so the next legal
                        # inference is compared against tracked game state.
                        self._append_log("vision", "Tracked board unchanged because the detected move was not accepted")
            else:
                self._play_overlay_state = board_state.copy()
                self._append_log("vision", "Run inference completed with no detected board change")
                if self._game_session is not None:
                    self._append_log("game", f"Turn unchanged: {self.state.side_to_move}")
            self.state.last_action = "Play-mode inference updated"
        return True, "ok"

    def set_active_classifier(self, classifier_path: str) -> tuple[bool, str]:
        normalized = classifier_path.strip()
        available = self._discover_available_classifiers()
        if normalized not in available:
            return False, f"Classifier '{classifier_path}' is not available"
        with self._lock:
            self.state.available_classifiers = available
            self.state.active_classifier_path = normalized
            self.state.last_action = f"Active classifier set to {normalized}"
            self._append_log("vision", f"Active classifier set to {normalized}")
        return True, "ok"

    def _set_next_corner_locked_state(self) -> None:
        if self.state.grid_locked:
            self.state.next_corner_label = "Locked"
            self.state.next_corner_hint = "Board corners captured"
            return
        index = min(self.state.corners_selected, len(self.CORNER_SEQUENCE) - 1)
        self.state.next_corner_label, self.state.next_corner_hint = self.CORNER_SEQUENCE[index]

    def _append_log(self, level: str, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.state.logs.append({"level": level, "message": f"[{timestamp}] {message}"})

    def _reset_training_state_locked(self) -> None:
        self._training_snapshots = []
        self.state.training_snapshot_count = 0
        self.state.training_active_snapshot_index = -1
        self.state.training_label_mode = "white"
        self.state.training_saved_snapshot_count = 0
        self._bump_training_revision_locked()

    def _reset_game_session_locked(self) -> None:
        if self._game_session is not None:
            try:
                self._game_session.close()
            except Exception:
                pass
        self._game_session = None
        self.state.side_to_move = "White"
        self.state.detected_move = "-"
        self.state.suggested_move = "-"
        self.state.fen = DEFAULT_START_FEN

    def _ensure_game_session_locked(self) -> bool:
        if self._game_session is not None:
            return True
        try:
            engine = StockfishEngineClient(DEFAULT_STOCKFISH_PATH)
            self._game_session = ChessGameSession(engine)
            self._append_log("system", f"Stockfish engine connected at {DEFAULT_STOCKFISH_PATH}")
            return True
        except Exception as exc:
            self._append_log("error", f"Stockfish init failed: {exc}")
            self._game_session = None
            return False

    def _discover_available_classifiers(self) -> list[str]:
        models_root = PROJECT_ROOT / "models"
        if not models_root.exists():
            return []
        return sorted(str(path.relative_to(PROJECT_ROOT)) for path in models_root.rglob("*.h5"))

    def _normalize_classifier_state(self) -> None:
        available = self.state.available_classifiers
        if self.state.active_classifier_path in available:
            return
        if available:
            self.state.active_classifier_path = available[0]

    def _run_training_job(self, command: list[str], dataset_rel: str, output_rel: str) -> None:
        try:
            process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._training_process = process
            if process.stdout is not None:
                for raw_line in process.stdout:
                    line = raw_line.strip()
                    if not line:
                        continue
                    with self._lock:
                        self.state.training_job_message = line[:240]
                        self._append_log("vision", f"[training] {line}")
            return_code = process.wait()
            with self._lock:
                self.state.available_classifiers = self._discover_available_classifiers()
                self._normalize_classifier_state()
                if return_code == 0:
                    self.state.training_job_status = "completed"
                    self.state.training_job_message = f"Training completed: {output_rel}"
                    self._append_log("vision", f"Training completed for dataset {dataset_rel}")
                else:
                    self.state.training_job_status = "failed"
                    self.state.training_job_message = f"Training failed with exit code {return_code}"
                    self._append_log("error", f"Training failed with exit code {return_code}")
        except Exception as exc:
            with self._lock:
                self.state.training_job_status = "failed"
                self.state.training_job_message = f"Training failed: {exc}"
                self._append_log("error", f"Training launch failed: {exc}")
        finally:
            self._training_process = None

    def _bump_training_revision_locked(self) -> None:
        self.state.training_revision += 1

    def _get_active_training_snapshot_locked(self) -> TrainingSnapshot | None:
        index = self.state.training_active_snapshot_index
        if index < 0 or index >= len(self._training_snapshots):
            return None
        return self._training_snapshots[index]

    def _draw_training_snapshot_overlay(self, snapshot: TrainingSnapshot) -> np.ndarray:
        overlay = self._draw_board_grid_overlay(snapshot.image)
        step = overlay.shape[0] // 8
        colors = {
            "white": (245, 245, 245),
            "black": (35, 35, 35),
            "empty": (40, 130, 220),
        }

        for row in range(8):
            for col in range(8):
                label = snapshot.labels[row, col]
                if not label:
                    continue
                x1 = col * step
                y1 = row * step
                x2 = min((col + 1) * step, overlay.shape[1] - 1)
                y2 = min((row + 1) * step, overlay.shape[0] - 1)
                color = colors.get(str(label), (80, 80, 80))
                tile = overlay[y1:y2, x1:x2]
                tint = np.full_like(tile, color, dtype=np.uint8)
                overlay[y1:y2, x1:x2] = cv2.addWeighted(tile, 0.7, tint, 0.3, 0)
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    overlay,
                    str(label)[0].upper(),
                    (x1 + 8, y1 + 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255) if label != "white" else (20, 20, 20),
                    2,
                    cv2.LINE_AA,
                )

        return overlay

    def _save_training_snapshot_dataset(self, snapshot_index: int, image: np.ndarray, labels: np.ndarray) -> str:
        dataset_root = PROJECT_ROOT / self.state.training_dataset_path
        snapshots_root = dataset_root / "_snapshots"
        snapshots_root.mkdir(parents=True, exist_ok=True)
        for folder_name in TRAINING_LABEL_TO_FOLDER.values():
            (dataset_root / folder_name).mkdir(parents=True, exist_ok=True)

        snapshot_number = self._get_next_training_snapshot_number(dataset_root)
        snapshot_path = snapshots_root / f"snapshot_{snapshot_number:03d}.png"
        cv2.imwrite(str(snapshot_path), image)

        board_size = image.shape[0]
        step = board_size // 8
        for row in range(8):
            for col in range(8):
                y1, y2 = row * step, (row + 1) * step
                x1, x2 = col * step, (col + 1) * step
                square = image[y1:y2, x1:x2]
                label = str(labels[row, col])
                category_dir = dataset_root / TRAINING_LABEL_TO_FOLDER[label]
                stem = f"snapshot_{snapshot_number:03d}_r{row}_c{col}"
                self._save_training_square_variants(category_dir, stem, square)

        return str(dataset_root.relative_to(PROJECT_ROOT))

    def _get_next_training_snapshot_number(self, dataset_root: Path) -> int:
        highest_index = 0

        for path in dataset_root.rglob("snapshot_*.png"):
            stem = path.stem
            parts = stem.split("_")
            if len(parts) < 2 or parts[0] != "snapshot":
                continue
            try:
                highest_index = max(highest_index, int(parts[1]))
            except ValueError:
                continue

        return highest_index + 1

    def _save_training_square_variants(self, category_dir: Path, stem: str, image: np.ndarray) -> None:
        variants = {
            "0": image,
            "90": cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE),
            "180": cv2.rotate(image, cv2.ROTATE_180),
            "270": cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE),
        }
        for suffix, variant in variants.items():
            output_path = category_dir / f"{stem}_{suffix}.png"
            cv2.imwrite(str(output_path), variant)

    def _load_inference_model(self, classifier_path: str):
        normalized_path = classifier_path.strip() or DEFAULT_ACTIVE_CLASSIFIER
        model_path = PROJECT_ROOT / normalized_path
        if not model_path.exists():
            raise FileNotFoundError(f"Classifier '{normalized_path}' does not exist")
        if self._inference_model is not None and self._inference_model_path == normalized_path:
            return self._inference_model

        from tensorflow.keras import models

        self._inference_model = models.load_model(model_path, compile=False)
        self._inference_model_path = normalized_path
        return self._inference_model

    def _capture_current_play_board(self) -> tuple[np.ndarray | None, str, str | None]:
        frame = self._camera_manager.get_latest_frame()
        if frame is None:
            return None, "", "No live camera frame available"
        with self._lock:
            corners = list(self.state.clicked_corners)
            if not self.state.grid_locked or len(corners) != 4:
                return None, "", "Lock the board corners before running play inference"
            classifier_path = self.state.active_classifier_path
        warped = self._warp_board(frame, corners)
        if warped is None:
            return None, "", "Could not warp the current board frame"
        return warped, classifier_path, None

    def _run_batched_board_inference(self, warped: np.ndarray, classifier_path: str) -> BoardInferenceResult:
        model = self._load_inference_model(classifier_path)
        from src.vision.preprocessing import preprocess_square_enhanced_v7

        board_state = np.empty((8, 8), dtype=object)
        board_size = warped.shape[0]
        step = board_size // 8
        squares = []

        for row in range(8):
            for col in range(8):
                y1, y2 = row * step, (row + 1) * step
                x1, x2 = col * step, (col + 1) * step
                square_image = warped[y1:y2, x1:x2]
                squares.append(preprocess_square_enhanced_v7(square_image, add_batch_dim=False))

        batch = np.stack(squares, axis=0)
        outputs = model(batch, training=False)
        predictions = outputs.numpy() if hasattr(outputs, "numpy") else np.asarray(outputs)

        square_index = 0
        for row in range(8):
            for col in range(8):
                class_index = int(np.argmax(predictions[square_index]))
                board_state[row, col] = INFERENCE_CATEGORIES[class_index]
                square_index += 1

        probabilities = predictions.reshape(8, 8, len(INFERENCE_CATEGORIES))
        return BoardInferenceResult(board_state=board_state, probabilities=probabilities)

    def _draw_camera_overlay(
        self,
        frame: np.ndarray,
        normalized_corners: list[tuple[float, float]],
        selecting: bool,
        grid_locked: bool,
        next_corner_label: str,
    ) -> np.ndarray:
        annotated = frame.copy()
        frame_h, frame_w = annotated.shape[:2]
        corner_labels = [label for label, _hint in self.CORNER_SEQUENCE]
        points: list[tuple[int, int]] = []

        for index, (normalized_x, normalized_y) in enumerate(normalized_corners):
            px = int(round(normalized_x * frame_w))
            py = int(round(normalized_y * frame_h))
            points.append((px, py))
            cv2.circle(annotated, (px, py), 8, (30, 80, 255), -1)
            cv2.circle(annotated, (px, py), 16, (255, 255, 255), 2)
            label = corner_labels[index] if index < len(corner_labels) else f"C{index + 1}"
            cv2.putText(
                annotated,
                label,
                (px + 12, py - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        for start, end in zip(points, points[1:]):
            cv2.line(annotated, start, end, (60, 220, 160), 2, cv2.LINE_AA)

        if grid_locked and len(points) == 4:
            cv2.line(annotated, points[-1], points[0], (60, 220, 160), 2, cv2.LINE_AA)

        if selecting and not grid_locked:
            cv2.putText(
                annotated,
                f"Click next corner: {next_corner_label}",
                (18, 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
        elif grid_locked:
            cv2.putText(
                annotated,
                "Corners locked",
                (18, 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (60, 220, 160),
                2,
                cv2.LINE_AA,
            )

        return annotated

    def _warp_board(self, frame: np.ndarray, normalized_corners: list[tuple[float, float]]) -> np.ndarray | None:
        if len(normalized_corners) != 4:
            return None
        frame_h, frame_w = frame.shape[:2]
        source_corners = np.array(
            [[x * frame_w, y * frame_h] for x, y in normalized_corners],
            dtype="float32",
        )
        board_size = 400
        dest_corners = np.array(
            [[0, board_size - 1], [board_size - 1, board_size - 1], [board_size - 1, 0], [0, 0]],
            dtype="float32",
        )
        matrix = cv2.getPerspectiveTransform(source_corners, dest_corners)
        return cv2.warpPerspective(frame, matrix, (board_size, board_size))

    def _draw_board_grid_overlay(self, warped: np.ndarray) -> np.ndarray:
        overlay = warped.copy()
        board_size = overlay.shape[0]
        step = board_size // 8
        line_color = (72, 235, 188)

        for index in range(9):
            offset = min(index * step, board_size - 1)
            cv2.line(overlay, (0, offset), (board_size - 1, offset), line_color, 1, cv2.LINE_AA)
            cv2.line(overlay, (offset, 0), (offset, board_size - 1), line_color, 1, cv2.LINE_AA)

        return overlay

    def _draw_play_inference_overlay(
        self,
        board: np.ndarray,
        board_state: np.ndarray,
        probabilities: np.ndarray | None,
    ) -> np.ndarray:
        overlay = board.copy()
        step = overlay.shape[0] // 8
        label_map = {
            "empty": (56, 136, 226),
            "black": (24, 24, 24),
            "white": (242, 242, 242),
        }
        probability_labels = [("E", 0), ("B", 1), ("W", 2)]

        for row in range(8):
            for col in range(8):
                label = str(board_state[row, col])
                color = label_map.get(label, (90, 90, 90))
                x1 = col * step
                y1 = row * step
                x2 = min((col + 1) * step, overlay.shape[1] - 1)
                y2 = min((row + 1) * step, overlay.shape[0] - 1)
                cv2.rectangle(overlay, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), color, 1, cv2.LINE_AA)
                text_color = (22, 22, 22) if label == "white" else ((245, 245, 245) if label == "black" else color)
                cv2.putText(
                    overlay,
                    label[:1].upper(),
                    (x1 + 4, y1 + 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.32,
                    text_color,
                    1,
                    cv2.LINE_AA,
                )
                if probabilities is None:
                    continue
                square_probs = probabilities[row, col]
                for line_index, (short_label, class_index) in enumerate(probability_labels):
                    probability = float(square_probs[class_index]) * 100.0
                    cv2.putText(
                        overlay,
                        f"{short_label}:{probability:4.1f}",
                        (x1 + 4, y1 + 24 + (line_index * 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.26,
                        text_color,
                        1,
                        cv2.LINE_AA,
                    )

        return overlay

    def _run(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                self.state.camera_connected = self._camera_manager.is_running()
                now_s = time.time()
                if (
                    self.state.control_target == "hardware"
                    and self.state.hardware_available
                    and self._hardware_robot is not None
                    and now_s >= self._hardware_poll_block_until_s
                    and (now_s - self._last_hardware_poll_s) >= self._hardware_poll_interval_s
                ):
                    self._refresh_hardware_joint_currents_locked()
                    self._last_hardware_poll_s = now_s
                else:
                    for joint in self.state.joints.values():
                        delta = joint.target - joint.current
                        if abs(delta) < 0.05 and abs(joint.velocity) < 0.05:
                            joint.current = joint.target
                            joint.velocity = 0.0
                            continue
                        direction = 1.0 if delta > 0 else -1.0
                        desired_velocity = direction * min(joint.max_speed, abs(delta))
                        if joint.velocity < desired_velocity:
                            joint.velocity = min(joint.velocity + joint.max_accel, desired_velocity)
                        elif joint.velocity > desired_velocity:
                            joint.velocity = max(joint.velocity - joint.max_accel, desired_velocity)
                        if abs(delta) <= abs(joint.velocity):
                            joint.current = joint.target
                            joint.velocity = 0.0
                        else:
                            joint.current += joint.velocity
                if self.state.executing and self.state.camera_connected:
                    self.state.last_action = "Robot executing planned move"
            time.sleep(UPDATE_INTERVAL_S)


class CommandCentreRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, app: MockCommandCentre, **kwargs) -> None:
        self._app = app
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self._write_json(HTTPStatus.OK, self._app.get_snapshot())
            return
        if parsed.path == "/api/cameras":
            self._write_json(HTTPStatus.OK, {"cameras": self._app.refresh_camera_sources()})
            return
        if parsed.path == "/api/camera/stream":
            self._write_mjpeg_stream()
            return
        if parsed.path == "/api/board/stream":
            self._write_mjpeg_stream(board_stream=True)
            return
        if parsed.path == "/api/training/active-snapshot":
            self._write_training_snapshot()
            return
        if parsed.path == "/":
            self._write_json(
                HTTPStatus.NOT_FOUND,
                {
                    "ok": False,
                    "message": "API only. Run the React frontend from web_control_centre with npm run dev.",
                },
            )
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "message": "Not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self._read_json_body()
        if body is None:
            return
        if parsed.path == "/api/action":
            action = str(body.get("action", ""))
            ok, message = self._app.trigger_action(action)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/joint-target":
            joint = str(body.get("joint", ""))
            try:
                value = float(body.get("value", 0))
            except (TypeError, ValueError):
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "Invalid joint value"})
                return
            ok, message = self._app.set_joint_target(joint, value)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/joint-angle-target":
            joint = str(body.get("joint", ""))
            try:
                value = float(body.get("value", 0))
            except (TypeError, ValueError):
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "Invalid joint angle"})
                return
            ok, message = self._app.set_joint_angle_target(joint, value)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/camera/select":
            source = str(body.get("source", ""))
            ok, message = self._app.set_camera_source(source)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/vision/corner":
            try:
                normalized_x = float(body.get("x", 0))
                normalized_y = float(body.get("y", 0))
            except (TypeError, ValueError):
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "Invalid corner coordinates"})
                return
            ok, message = self._app.add_corner_click(normalized_x, normalized_y)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/training/capture":
            ok, message = self._app.capture_training_snapshot()
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/training/label-mode":
            mode = str(body.get("mode", ""))
            ok, message = self._app.set_training_label_mode(mode)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/training/dataset-path":
            dataset_path = str(body.get("dataset_path", ""))
            ok, message = self._app.set_training_dataset_path(dataset_path)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/training/start":
            dataset_path = str(body.get("dataset_path", ""))
            model_name = str(body.get("model_name", ""))
            ok, message = self._app.start_model_training(dataset_path, model_name)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/training/snapshot":
            try:
                index = int(body.get("index", -1))
            except (TypeError, ValueError):
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "Invalid training snapshot index"})
                return
            ok, message = self._app.set_active_training_snapshot(index)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/training/square":
            try:
                normalized_x = float(body.get("x", 0))
                normalized_y = float(body.get("y", 0))
            except (TypeError, ValueError):
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "Invalid training square coordinates"})
                return
            ok, message = self._app.annotate_training_square(normalized_x, normalized_y)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/training/reset-labels":
            ok, message = self._app.reset_active_training_snapshot_labels()
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/training/complete-snapshot":
            ok, message = self._app.complete_active_training_snapshot()
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/play/start":
            ok, message = self._app.start_play_mode()
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/kinematics/square-test":
            square = str(body.get("square", ""))
            ok, message = self._app.solve_square_inverse_kinematics(square)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/kinematics/square-test/next":
            ok, message = self._app.advance_square_inverse_kinematics()
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/settings/active-classifier":
            classifier_path = str(body.get("classifier_path", ""))
            ok, message = self._app.set_active_classifier(classifier_path)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/robot/control-target":
            target = str(body.get("target", ""))
            ok, message = self._app.set_control_target(target)
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/robot/home":
            ok, message = self._app.go_to_session_home()
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        if parsed.path == "/api/robot/home/save":
            ok, message = self._app.save_session_home()
            self._write_json(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, {"ok": ok, "message": message})
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "message": "Not found"})

    def _write_mjpeg_stream(self, board_stream: bool = False) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}")
        self.end_headers()
        try:
            while True:
                frame = self._app.get_latest_board_frame() if board_stream else self._app.get_latest_camera_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                self.wfile.write(f"--{MJPEG_BOUNDARY}\r\n".encode("ascii"))
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
                time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _write_training_snapshot(self) -> None:
        frame = self._app.get_active_training_snapshot_frame()
        if frame is None:
            self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "message": "No active training snapshot"})
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(frame)))
        self.end_headers()
        self.wfile.write(frame)

    def _read_json_body(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "Invalid JSON"})
            return None

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class CommandCentreHTTPServer(ThreadingHTTPServer):
    daemon_threads = True


def run_server(host: str = HOST, port: int = PORT) -> None:
    app = MockCommandCentre()
    app.start()

    def handler(*args, **kwargs):
        CommandCentreRequestHandler(*args, app=app, **kwargs)

    try:
        server = CommandCentreHTTPServer((host, port), handler)
        print(f"Web control centre running at http://{host}:{port}")
        server.serve_forever()
    except OSError as exc:
        app.stop()
        if exc.errno == 48:
            raise OSError(
                48,
                f"Address {host}:{port} is already in use. Stop the existing process or set WEB_CONTROL_CENTRE_PORT.",
            ) from exc
        raise
    except KeyboardInterrupt:
        pass
    finally:
        if "server" in locals():
            server.server_close()
        app.stop()
