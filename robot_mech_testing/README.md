# Robot Mechanical Testing

This folder contains a minimal Arduino sketch + a simple macOS UI to test servos
through a PCA9686 (I2C) board.

## How to find the I2C address
The PCA9686 defaults to `0x40` unless A0-A5 jumpers are set.

If you are unsure, upload `i2c_scanner.ino` and check the Serial Monitor output.

## Arduino setup
1. Install the **Adafruit PWM Servo Driver** library in Arduino IDE:
   - Library Manager -> search "Adafruit PWM Servo Driver Library"
2. Open `servo_pca9686_serial/servo_pca9686_serial.ino` and upload.
3. Open Serial Monitor at `115200` to confirm it starts.

## macOS UI setup
1. Install Python deps:
   - `python3 -m pip install pyserial`
2. Run the UI:
   - `python3 servo_slider_ui.py`
3. Pick your serial port (e.g., `/dev/tty.usbmodemXXXX`) and click Connect.

## Serial protocol (simple)
Each command is a line: `channel angle`
Example: `0 90`

Channels are PCA9686 channels (0-15).
Angles are 0-180 (mapped to pulse width in the Arduino sketch).
