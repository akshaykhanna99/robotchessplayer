import { Tile } from "./Tile";

export function KinematicsTile() {
  return (
    <Tile title="Robot Kinematics" className="tile-kinematics" aside={<span className="pill pill-muted">3D slot</span>}>
      <div className="kinematics-stage">
        <div className="arm-stage">
          <div className="arm-base" />
          <div className="arm-link arm-link-1" />
          <div className="arm-joint arm-joint-1" />
          <div className="arm-link arm-link-2" />
          <div className="arm-joint arm-joint-2" />
          <div className="arm-link arm-link-3" />
          <div className="arm-effector" />
        </div>
        <div className="kinematics-copy">
          <p>Reserved for the real-time 3D robot view.</p>
          <p>Next step: replace this placeholder with a React Three Fiber scene using the same geometry config as the backend.</p>
        </div>
      </div>
    </Tile>
  );
}
