# Robot Mechanical Testing

This folder contains the Arduino sketches and quick Python utilities used to test
the robot servos through a PCA9686 (I2C) board.

## How to find the I2C address
The PCA9686 defaults to `0x40` unless A0-A5 jumpers are set.

If you are unsure, upload `i2c_scanner.ino` and check the Serial Monitor output.

## Arduino setup
1. Install the **Adafruit PWM Servo Driver** library in Arduino IDE:
   - Library Manager -> search "Adafruit PWM Servo Driver Library"
2. Upload the sketch that matches the protocol you want to test.
3. Open Serial Monitor at `115200` to confirm it starts.

## Common sketch options

- `servo_pca9686_serial/servo_pca9686_serial.ino`
  - simple `channel angle` protocol
- `servo_mixed_serial/servo_mixed_serial.ino`
  - `PCA <channel> <angle>` protocol
- `full_robot_serial/full_robot_serial.ino`
  - current full robot raw-pulse protocol: `<channel>,<pulse>`
  - also supports `STATUS`, `STATUS_JSON`, `GET <channel>`, `RESET`

## Python utilities
1. Install Python deps:
   - `python3 -m pip install pyserial`
2. For direct angle testing with `PCA <channel> <angle>`, run:
   - `python3 servo_slider_ui.py`
3. For the current full robot raw-pulse workflow, run:
   - `python3 full_robot_test_run.py`
4. Pick your serial port (e.g., `/dev/tty.usbmodemXXXX`) and click Connect if the script provides a selector.

## Protocol summary

- `servo_slider_ui.py` sends: `PCA <channel> <angle>`
- `full_robot_test_run.py` sends: `<channel>,<pulse>`
- `full_robot_serial/full_robot_serial.ino` expects: `<channel>,<pulse>`

Channels are PCA9686 channels (`0-15`).
