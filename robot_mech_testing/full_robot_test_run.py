import tkinter as tk
from tkinter import ttk
import serial
import time

# CHANGE THIS to your Arduino port
SERIAL_PORT = "/dev/tty.usbmodem143301"  
BAUD_RATE = 115200
UPDATE_MS = 20
MAX_SPEED_PER_TICK = {
    0: 4.0,
    1: 4.0,
    2: 3.0,
    3: 4.0,
    4: 2.0,
}
MAX_ACCEL_PER_TICK = {
    0: 0.7,
    1: 0.7,
    2: 0.5,
    3: 0.7,
    4: 0.35,
}

# Default values
defaults = {
    0: 375,  # base
    1: 375,  # shoulder
    2: 385,  # elbow
    3: 375,  # wrist
    4: 340   # gripper
}

# Conservative test ranges
ranges = {
    0: (250, 500),
    1: (250, 500),
    2: (250, 500),
    3: (250, 500),
    4: (180, 340)
}

labels = {
    0: "Base",
    1: "Shoulder",
    2: "Elbow",
    3: "Wrist",
    4: "Gripper"
}

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)

def send_value(channel, value):
    int_value = int(round(value))
    cmd = f"{channel},{int_value}\n"
    ser.write(cmd.encode("utf-8"))
    if channel in value_labels:
        value_labels[channel].config(text=str(int_value))

def on_slider_change(channel, value):
    target_values[channel] = float(value)

def step_toward_zero(velocity, amount):
    if velocity > 0:
        return max(0.0, velocity - amount)
    if velocity < 0:
        return min(0.0, velocity + amount)
    return 0.0

def update_motion():
    for channel in range(5):
        current = current_values[channel]
        target = target_values[channel]
        velocity = velocities[channel]
        delta = target - current

        if abs(delta) < 0.5 and abs(velocity) < 0.1:
            current_values[channel] = target
            velocities[channel] = 0.0
            continue

        direction = 1.0 if delta > 0 else -1.0
        desired_velocity = direction * min(MAX_SPEED_PER_TICK[channel], abs(delta))

        if velocity < desired_velocity:
            velocity = min(velocity + MAX_ACCEL_PER_TICK[channel], desired_velocity)
        elif velocity > desired_velocity:
            velocity = max(velocity - MAX_ACCEL_PER_TICK[channel], desired_velocity)

        if abs(delta) <= abs(velocity):
            current = target
            velocity = 0.0
        else:
            current += velocity
            braking_distance = (velocity * velocity) / (2 * max(MAX_ACCEL_PER_TICK[channel], 0.001))
            if abs(delta) <= braking_distance + 1.0:
                velocity = step_toward_zero(velocity, MAX_ACCEL_PER_TICK[channel])

        current_values[channel] = current
        velocities[channel] = velocity
        rounded_value = int(round(current))
        if rounded_value != last_sent_values[channel]:
            send_value(channel, rounded_value)
            last_sent_values[channel] = rounded_value

    root.after(UPDATE_MS, update_motion)

def reset_all():
    for ch, val in defaults.items():
        sliders[ch].set(val)
        target_values[ch] = float(val)

def on_close():
    ser.close()
    root.destroy()

root = tk.Tk()
root.title("Chess Robot Arm Servo Tester")

main = ttk.Frame(root, padding=12)
main.grid(row=0, column=0, sticky="nsew")

sliders = {}
value_labels = {}
target_values = {ch: float(defaults[ch]) for ch in defaults}
current_values = {ch: float(defaults[ch]) for ch in defaults}
velocities = {ch: 0.0 for ch in defaults}
last_sent_values = {ch: None for ch in defaults}

for ch in range(5):
    ttk.Label(main, text=labels[ch]).grid(row=ch, column=0, sticky="w", padx=5, pady=8)

    min_val, max_val = ranges[ch]
    slider = ttk.Scale(
        main,
        from_=min_val,
        to=max_val,
        orient="horizontal",
        length=350,
        command=lambda value, channel=ch: on_slider_change(channel, value)
    )
    slider.grid(row=ch, column=1, padx=5, pady=8)
    slider.set(defaults[ch])
    sliders[ch] = slider

    val_label = ttk.Label(main, text=str(defaults[ch]), width=6)
    val_label.grid(row=ch, column=2, padx=5)
    value_labels[ch] = val_label

ttk.Button(main, text="Reset to Defaults", command=reset_all).grid(row=6, column=0, columnspan=3, pady=15)

root.protocol("WM_DELETE_WINDOW", on_close)
reset_all()
update_motion()
root.mainloop()
