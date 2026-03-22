"""Main control centre window."""

from __future__ import annotations

from pathlib import Path

from src.orchestrator.control_centre_controller import ControlCentreController
from src.ui.panels.game_panel import GamePanel
from src.ui.panels.robot_side_view_panel import RobotSideViewPanel
from src.ui.panels.robot_top_view_panel import RobotTopViewPanel
from src.ui.panels.vision_panel import VisionPanel
from src.ui.qt import (
    QAction,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    Qt,
    USING_PYSIDE6,
)


class ControlCentreWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RobotChessPlayer Control Centre")
        self.resize(1400, 800)

        self.controller = ControlCentreController()
        self._build_ui()
        self._wire_signals()

    def closeEvent(self, event) -> None:
        self.controller.shutdown()
        super().closeEvent(event)

    def _build_ui(self) -> None:
        self._build_toolbar()

        self.vision_panel = VisionPanel()
        self.robot_top_panel = RobotTopViewPanel()
        self.robot_side_panel = RobotSideViewPanel()
        self.game_panel = GamePanel()

        robot_splitter = QSplitter(Qt.Orientation.Vertical)
        robot_splitter.addWidget(self.robot_top_panel)
        robot_splitter.addWidget(self.robot_side_panel)
        robot_splitter.setSizes([400, 400])

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.vision_panel)
        main_splitter.addWidget(robot_splitter)
        main_splitter.addWidget(self.game_panel)
        main_splitter.setSizes([700, 420, 280])

        self.setCentralWidget(main_splitter)
        self.setStatusBar(QStatusBar())

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Controls")
        self.addToolBar(toolbar)

        load_action = QAction("Load Config", self)
        load_action.triggered.connect(self._load_config)
        toolbar.addAction(load_action)

        start_cam = QAction("Start Camera", self)
        start_cam.triggered.connect(self._start_camera_from_toolbar)
        toolbar.addAction(start_cam)

        stop_cam = QAction("Stop Camera", self)
        stop_cam.triggered.connect(self.controller.stop_camera)
        toolbar.addAction(stop_cam)

        reset_corners = QAction("Reset Corners", self)
        reset_corners.triggered.connect(self.controller.reset_corners)
        toolbar.addAction(reset_corners)

        run_inference = QAction("Run Inference", self)
        run_inference.triggered.connect(self.controller.run_inference)
        toolbar.addAction(run_inference)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel("Camera"))
        self.camera_device_selector = QComboBox()
        self.camera_device_selector.setToolTip("Detected camera devices (select by name)")
        toolbar.addWidget(self.camera_device_selector)
        refresh_cams = QAction("Refresh Cameras", self)
        refresh_cams.triggered.connect(self._refresh_camera_devices)
        toolbar.addAction(refresh_cams)

        toolbar.addSeparator()

        self.mode_selector = QComboBox()
        self.mode_selector.addItems(
            ["Vision Only", "Vision + Game", "Vision + Game + Mock Robot", "Full System"]
        )
        self.mode_selector.currentTextChanged.connect(self.controller.set_mode)
        toolbar.addWidget(self.mode_selector)

        self._refresh_camera_devices()

    def _wire_signals(self) -> None:
        self.vision_panel.raw_label.clicked.connect(self.controller.add_corner)

        self.controller.vision_frame.connect(lambda img: self._set_pixmap(self.vision_panel.set_raw_image, img))
        self.controller.vision_warped.connect(lambda img: self._set_pixmap(self.vision_panel.set_warped_image, img))
        self.controller.vision_overlay.connect(lambda img: self._set_pixmap(self.vision_panel.set_inference_image, img))
        self.controller.vision_status.connect(self._update_vision_status)

        self.controller.log_event.connect(self.game_panel.append_log)
        self.controller.game_status.connect(self.game_panel.update_status)
        self.controller.system_status.connect(self._update_system_status)

        self.controller.robot_plan.connect(self._handle_robot_plan)
        self.controller.robot_progress.connect(self._handle_robot_progress)
        self.controller.robot_gripper.connect(self._handle_robot_gripper)

    def _set_pixmap(self, setter, qimage) -> None:
        from src.ui.qt import QPixmap

        if qimage is None:
            return
        setter(QPixmap.fromImage(qimage))

    def _update_vision_status(self, payload: dict) -> None:
        status = payload.get("status")
        next_corner = payload.get("next_corner", "-")
        if status:
            self.vision_panel.update_status(
                status.camera_connected,
                status.corners_selected,
                status.grid_locked,
                next_corner,
            )

    def _handle_robot_plan(self, plan) -> None:
        if not self.controller._setup:
            return
        board = self.controller._setup.board
        self.robot_top_panel.set_board_geometry(board.origin_x_mm, board.origin_y_mm, board.square_size_mm)
        self.robot_side_panel.set_board_geometry(board.origin_x_mm, board.board_z_mm, board.square_size_mm)
        self.robot_top_panel.set_plan(plan)
        self.robot_side_panel.set_plan(plan)

    def _handle_robot_progress(self, payload: dict) -> None:
        pose = payload.get("pose")
        self.robot_top_panel.update_progress(pose)
        self.robot_side_panel.update_progress(pose)

    def _handle_robot_gripper(self, state: str) -> None:
        self.statusBar().showMessage(f"Gripper: {state}")

    def _update_system_status(self, status) -> None:
        self.statusBar().showMessage(
            f"Setup: {status.setup_name} | Robot: {status.robot_name} | Port: {status.serial_port}"
        )

    def _load_config(self) -> None:
        default_path = str(Path("config") / "physical_setup.example.json")
        path, _ = QFileDialog.getOpenFileName(self, "Load Setup Config", default_path, "JSON Files (*.json)")
        if path:
            self.controller.load_config(path)
        else:
            QMessageBox.information(self, "Config", "No config selected.")

    def _start_camera_from_toolbar(self) -> None:
        selected_index = self.camera_device_selector.currentData()
        if selected_index is None:
            QMessageBox.warning(self, "Camera", "No camera selected. Click 'Refresh Cameras' and choose a device.")
            return
        else:
            camera_index = int(selected_index)
        self.controller.start_camera(
            camera_index=camera_index,
            camera_backend="Auto",
        )

    def _refresh_camera_devices(self) -> None:
        current_text = self.camera_device_selector.currentText()
        self.camera_device_selector.clear()
        devices = self._enumerate_camera_devices()
        for idx, label in devices:
            self.camera_device_selector.addItem(label, idx)
        if not devices:
            self.camera_device_selector.addItem("No cameras detected (use Index/Source)", None)
        if current_text:
            pos = self.camera_device_selector.findText(current_text)
            if pos >= 0:
                self.camera_device_selector.setCurrentIndex(pos)

    def _enumerate_camera_devices(self) -> list[tuple[int, str]]:
        try:
            if USING_PYSIDE6:
                from PySide6.QtMultimedia import QMediaDevices
            else:
                from PyQt6.QtMultimedia import QMediaDevices
        except Exception:
            return [(i, f"Camera {i}") for i in range(5)]

        devices = []
        for idx, device in enumerate(QMediaDevices.videoInputs()):
            try:
                desc = device.description()
            except Exception:
                desc = f"Camera {idx}"
            devices.append((idx, f"{idx}: {desc}"))
        if not devices:
            return [(i, f"Camera {i}") for i in range(5)]
        return devices
