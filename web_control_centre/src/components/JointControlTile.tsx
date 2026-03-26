import type { JointState } from "../types";
import { Tile } from "./Tile";

type JointControlTileProps = {
  joints: Record<string, JointState>;
  onJointChange: (joint: string, value: number) => void;
};

function widthPercent(value: number, min: number, max: number) {
  if (max <= min) {
    return 0;
  }
  return ((value - min) / (max - min)) * 100;
}

export function JointControlTile({ joints, onJointChange }: JointControlTileProps) {
  return (
    <Tile title="Joint Control" className="tile-joints" aside={<span className="pill pill-muted">Target vs actual</span>}>
      <div className="joint-list">
        {Object.entries(joints).map(([name, joint]) => (
          <article className="joint-card" key={name}>
            <div className="joint-card-head">
              <div>
                <h3>{joint.label}</h3>
                <span className="joint-meta">
                  {joint.minimum} - {joint.maximum} | vel {joint.velocity}
                </span>
              </div>
              <div className="joint-readout">
                <span>Target {joint.target}</span>
                <span>Actual {joint.current}</span>
              </div>
            </div>
            <input
              className="joint-slider"
              type="range"
              min={joint.minimum}
              max={joint.maximum}
              step={1}
              value={joint.target}
              onChange={(event) => onJointChange(name, Number(event.target.value))}
            />
            <div className="joint-rail">
              <div className="joint-target-bar" style={{ width: `${widthPercent(joint.target, joint.minimum, joint.maximum)}%` }} />
              <div className="joint-current-bar" style={{ width: `${widthPercent(joint.current, joint.minimum, joint.maximum)}%` }} />
            </div>
          </article>
        ))}
      </div>
    </Tile>
  );
}
