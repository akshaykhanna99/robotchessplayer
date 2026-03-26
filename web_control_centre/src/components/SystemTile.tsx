import type { RobotState, SystemState, VisionState } from "../types";
import { Tile } from "./Tile";

type SystemTileProps = {
  system: SystemState;
  vision: VisionState;
  robot: RobotState;
};

export function SystemTile({ system, vision, robot }: SystemTileProps) {
  return (
    <Tile
      title="System Status"
      className="tile-system"
      aside={
        <span className="pill">{vision.camera_connected ? "Camera online" : "Camera offline"}</span>
      }
    >
      <div className="metric-grid">
        <article className="metric-card">
          <span className="metric-label">Setup</span>
          <strong className="metric-value">{system.setup_name}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Robot</span>
          <strong className="metric-value">{system.robot_name}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Serial Port</span>
          <strong className="metric-value">{system.serial_port}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Camera</span>
          <strong className="metric-value">{system.camera_source}</strong>
        </article>
      </div>

      <div className="status-strips">
        <div className="status-strip">
          <span>Execution</span>
          <strong>{robot.executing ? "Executing" : "Idle"}</strong>
        </div>
        <div className="status-strip">
          <span>Gripper</span>
          <strong>{robot.gripper_state}</strong>
        </div>
        <div className="status-strip">
          <span>Grid Lock</span>
          <strong>{vision.grid_locked ? "Locked" : "Unlocked"}</strong>
        </div>
      </div>
    </Tile>
  );
}
