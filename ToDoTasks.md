# Robot Chess Player To-Do

## Hardware

- Replace the elbow micro servo with an MG996R or equivalent higher-torque servo.
- Redesign the elbow joint mount and linkage to fit the new servo cleanly.
- Re-check elbow alignment, horn position, and mechanical clearances after the redesign.
- Verify the servo power supply can handle the elbow load without voltage sag.

## Calibration

- Recalibrate the elbow joint after installing the new servo.
- Record safe elbow minimum, maximum, and default pulse values.
- Re-test the gripper, wrist, shoulder, and base after the elbow redesign.
- Update Python and Arduino test ranges with final calibrated values.

## Motion Testing

- Test full-arm movement again using `robot_mech_testing/full_robot_test_run.py`.
- Tune smoothing, max speed, and max acceleration values for each joint.
- Confirm `Reset to Defaults` moves all joints smoothly and safely.
- Verify there are no hard stops, stalls, or unstable movements across the usable range.

## Robot Model

- Measure the final robot geometry: base position, link lengths, offsets, and joint directions.
- Measure the chessboard position relative to the robot base frame.
- Define joint limits, home pose, pickup height, and safe travel height.
- Store this geometry in a shared config for both simulation and real control.

## Kinematics And Simulation

- Implement forward kinematics for the robot arm.
- Implement inverse kinematics for board-square target positions.
- Build a lightweight visual simulator for the arm and chessboard.
- Add reachability checks for every square on the board.
- Add simple path planning between home, pickup, travel, and drop-off poses.

## Integration

- Connect the kinematics layer to the robot serial control layer.
- Map board squares to robot target coordinates.
- Test piece pickup and placement on a subset of squares first.
- Expand to full-board move execution once the motion is reliable.
