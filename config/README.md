# Config

Configuration files for physical setups and runtime paths.

## Current files

- `physical_setup.example.json`
  - Example combined board + robot setup profile used by `src/robot/config.py`
- `physical_setup_v1.json`
  - Current local hardware setup used by the web command centre for real robot control
- `digital_twin_setup.example.json`
  - Example 3D twin scene/geometry profile for the React visualizer and future simulation work
- `digital_twin_setup_v1.json`
  - Current working digital twin scene / geometry profile used by the web UI

## Notes

- `digital_twin_setup_v1.json` is the current source for viewer geometry and virtual joint ranges
- `physical_setup_v1.json` is the current source for real robot serial transport, channels, pulse calibration, and gripper calibration
