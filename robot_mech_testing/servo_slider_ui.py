#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import serial
from serial.tools import list_ports

BAUD = 115200
DEFAULT_CHANNEL = 0
UPDATE_MS = 20
MAX_STEP_PER_TICK = 6
SLOWDOWN_DEGREES = 25
MIN_STEP_PER_TICK = 1

class ServoUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Servo Tester - PCA9686")
        self.ser = None
        self.target_angle = 90
        self.current_angle = 90

        self.port_var = tk.StringVar(value=self._auto_port())
        self.base_channel_var = tk.IntVar(value=0)
        self.shoulder_channel_var = tk.IntVar(value=1)
        self.elbow_channel_var = tk.IntVar(value=2)
        self.wrist_channel_var = tk.IntVar(value=3)
        self.gripper_channel_var = tk.IntVar(value=4)
        self.base_angle_var = tk.IntVar(value=90)
        self.shoulder_angle_var = tk.IntVar(value=90)
        self.elbow_angle_var = tk.IntVar(value=90)
        self.wrist_angle_var = tk.IntVar(value=90)
        self.gripper_angle_var = tk.IntVar(value=90)
        self.status_var = tk.StringVar(value="Disconnected")
        self.base_target = 90
        self.base_current = 90
        self.shoulder_target = 90
        self.shoulder_current = 90
        self.elbow_target = 90
        self.elbow_current = 90
        self.wrist_target = 90
        self.wrist_current = 90
        self.gripper_target = 90
        self.gripper_current = 90

        self._build_ui()
        self._tick()

    def _auto_port(self):
        ports = list_ports.comports()
        if ports:
            return ports[0].device
        return ""

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        ttk.Label(main, text="Serial Port:").grid(row=0, column=0, sticky="w")
        port_entry = ttk.Entry(main, textvariable=self.port_var, width=32)
        port_entry.grid(row=0, column=1, sticky="ew", padx=6)

        refresh_btn = ttk.Button(main, text="Refresh", command=self._refresh_ports)
        refresh_btn.grid(row=0, column=2, sticky="ew")

        self.connect_btn = ttk.Button(main, text="Connect", command=self._toggle_connect)
        self.connect_btn.grid(row=0, column=3, sticky="ew", padx=(6, 0))

        ttk.Label(main, text="Base (PCA9686):").grid(row=1, column=0, sticky="w", pady=(10, 0))
        base_channel = ttk.Spinbox(main, from_=0, to=15, textvariable=self.base_channel_var, width=5)
        base_channel.grid(row=1, column=1, sticky="w", pady=(10, 0))
        base_scale = ttk.Scale(main, from_=0, to=180, orient="horizontal", command=self._on_base_slider)
        base_scale.set(self.base_angle_var.get())
        base_scale.grid(row=1, column=2, columnspan=2, sticky="ew", pady=(10, 0))
        base_label = ttk.Label(main, textvariable=self.base_angle_var, width=4)
        base_label.grid(row=1, column=4, sticky="w", padx=(6, 0), pady=(10, 0))

        ttk.Label(main, text="Shoulder (PCA9686):").grid(row=2, column=0, sticky="w", pady=(10, 0))
        shoulder_channel = ttk.Spinbox(main, from_=0, to=15, textvariable=self.shoulder_channel_var, width=5)
        shoulder_channel.grid(row=2, column=1, sticky="w", pady=(10, 0))
        shoulder_scale = ttk.Scale(main, from_=0, to=180, orient="horizontal", command=self._on_shoulder_slider)
        shoulder_scale.set(self.shoulder_angle_var.get())
        shoulder_scale.grid(row=2, column=2, columnspan=2, sticky="ew", pady=(10, 0))
        shoulder_label = ttk.Label(main, textvariable=self.shoulder_angle_var, width=4)
        shoulder_label.grid(row=2, column=4, sticky="w", padx=(6, 0), pady=(10, 0))

        ttk.Label(main, text="Elbow (PCA9686):").grid(row=3, column=0, sticky="w", pady=(10, 0))
        elbow_channel = ttk.Spinbox(main, from_=0, to=15, textvariable=self.elbow_channel_var, width=5)
        elbow_channel.grid(row=3, column=1, sticky="w", pady=(10, 0))
        elbow_scale = ttk.Scale(main, from_=0, to=180, orient="horizontal", command=self._on_elbow_slider)
        elbow_scale.set(self.elbow_angle_var.get())
        elbow_scale.grid(row=3, column=2, columnspan=2, sticky="ew", pady=(10, 0))
        elbow_label = ttk.Label(main, textvariable=self.elbow_angle_var, width=4)
        elbow_label.grid(row=3, column=4, sticky="w", padx=(6, 0), pady=(10, 0))

        ttk.Label(main, text="Wrist (PCA9686):").grid(row=4, column=0, sticky="w", pady=(10, 0))
        wrist_channel = ttk.Spinbox(main, from_=0, to=15, textvariable=self.wrist_channel_var, width=5)
        wrist_channel.grid(row=4, column=1, sticky="w", pady=(10, 0))
        wrist_scale = ttk.Scale(main, from_=0, to=180, orient="horizontal", command=self._on_wrist_slider)
        wrist_scale.set(self.wrist_angle_var.get())
        wrist_scale.grid(row=4, column=2, columnspan=2, sticky="ew", pady=(10, 0))
        wrist_label = ttk.Label(main, textvariable=self.wrist_angle_var, width=4)
        wrist_label.grid(row=4, column=4, sticky="w", padx=(6, 0), pady=(10, 0))

        ttk.Label(main, text="Gripper (PCA9686):").grid(row=5, column=0, sticky="w", pady=(10, 0))
        gripper_channel = ttk.Spinbox(main, from_=0, to=15, textvariable=self.gripper_channel_var, width=5)
        gripper_channel.grid(row=5, column=1, sticky="w", pady=(10, 0))
        gripper_scale = ttk.Scale(main, from_=0, to=180, orient="horizontal", command=self._on_gripper_slider)
        gripper_scale.set(self.gripper_angle_var.get())
        gripper_scale.grid(row=5, column=2, columnspan=2, sticky="ew", pady=(10, 0))
        gripper_label = ttk.Label(main, textvariable=self.gripper_angle_var, width=4)
        gripper_label.grid(row=5, column=4, sticky="w", padx=(6, 0), pady=(10, 0))

        ttk.Label(main, textvariable=self.status_var).grid(
            row=6, column=0, columnspan=4, sticky="w", pady=(10, 0)
        )

        main.columnconfigure(1, weight=1)

    def _refresh_ports(self):
        ports = list_ports.comports()
        if ports:
            self.port_var.set(ports[0].device)

    def _toggle_connect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
            self.status_var.set("Disconnected")
            self.connect_btn.config(text="Connect")
            return

        port = self.port_var.get().strip()
        if not port:
            self.status_var.set("No serial port selected")
            return

        try:
            self.ser = serial.Serial(port, BAUD, timeout=1)
            self.status_var.set(f"Connected to {port}")
            self.connect_btn.config(text="Disconnect")
            self._send_current()
        except serial.SerialException as exc:
            self.status_var.set(f"Failed to connect: {exc}")

    def _on_base_slider(self, value):
        angle = int(float(value))
        self.base_angle_var.set(angle)
        self.base_target = angle

    def _on_shoulder_slider(self, value):
        angle = int(float(value))
        self.shoulder_angle_var.set(angle)
        self.shoulder_target = angle

    def _on_elbow_slider(self, value):
        angle = int(float(value))
        self.elbow_angle_var.set(angle)
        self.elbow_target = angle

    def _on_wrist_slider(self, value):
        angle = int(float(value))
        self.wrist_angle_var.set(angle)
        self.wrist_target = angle

    def _on_gripper_slider(self, value):
        angle = int(float(value))
        self.gripper_angle_var.set(angle)
        self.gripper_target = angle

    def _send_pca(self, channel, angle):
        if not self.ser or not self.ser.is_open:
            return
        line = f"PCA {channel} {angle}\n"
        try:
            self.ser.write(line.encode("ascii"))
        except serial.SerialException as exc:
            self.status_var.set(f"Serial error: {exc}")

    def _tick(self):
        self._step_motion(
            self.base_target,
            "base_current",
            self._send_base
        )
        self._step_motion(
            self.shoulder_target,
            "shoulder_current",
            self._send_shoulder
        )
        self._step_motion(
            self.elbow_target,
            "elbow_current",
            self._send_elbow
        )
        self._step_motion(
            self.wrist_target,
            "wrist_current",
            self._send_wrist
        )
        self._step_motion(
            self.gripper_target,
            "gripper_current",
            self._send_gripper
        )
        self.root.after(UPDATE_MS, self._tick)

    def _step_motion(self, target, current_attr, send_fn):
        current = getattr(self, current_attr)
        delta = target - current
        if delta == 0:
            return
        distance = abs(delta)
        if distance <= SLOWDOWN_DEGREES:
            step = max(MIN_STEP_PER_TICK, int(distance / 4))
        else:
            step = MAX_STEP_PER_TICK
        step = min(step, distance)
        current += step if delta > 0 else -step
        setattr(self, current_attr, current)
        send_fn(current)

    def _send_base(self, angle):
        channel = self.base_channel_var.get()
        self._send_pca(channel, angle)

    def _send_shoulder(self, angle):
        channel = self.shoulder_channel_var.get()
        self._send_pca(channel, angle)

    def _send_elbow(self, angle):
        channel = self.elbow_channel_var.get()
        self._send_pca(channel, angle)

    def _send_wrist(self, angle):
        channel = self.wrist_channel_var.get()
        self._send_pca(channel, angle)

    def _send_gripper(self, angle):
        channel = self.gripper_channel_var.get()
        self._send_pca(channel, angle)

def main():
    root = tk.Tk()
    app = ServoUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
