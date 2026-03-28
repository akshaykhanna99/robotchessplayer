import { useEffect, useMemo, useState } from "react";
import twinConfig from "../../../config/digital_twin_setup_v1.json";
import type { IkTestState, JointState, RobotState } from "../types";
import type { DigitalTwinConfig } from "../digitalTwinTypes";
import { DigitalTwinScene } from "./DigitalTwinScene";
import { Tile } from "./Tile";

type KinematicsTileProps = {
  joints: Record<string, JointState>;
  robot: RobotState;
  ikTest: IkTestState;
  onJointChange: (joint: string, value: number) => Promise<void> | void;
  onIkSquareTest: (square: string) => Promise<void> | void;
  onIkSquareStep: () => Promise<void> | void;
  onRobotControlTarget: (target: "virtual" | "hardware") => Promise<void> | void;
  onRobotHome: () => Promise<void> | void;
  onRobotSaveHome: () => Promise<void> | void;
  onToggleGripper: () => Promise<void> | void;
};

function widthPercent(value: number, min: number, max: number) {
  if (max <= min) {
    return 0;
  }
  return ((value - min) / (max - min)) * 100;
}

export function KinematicsTile({
  joints,
  robot,
  ikTest,
  onJointChange,
  onIkSquareTest,
  onIkSquareStep,
  onRobotControlTarget,
  onRobotHome,
  onRobotSaveHome,
  onToggleGripper,
}: KinematicsTileProps) {
  const config = twinConfig as DigitalTwinConfig;
  const [showLegend, setShowLegend] = useState(true);
  const [ikSquare, setIkSquare] = useState(ikTest.square || "e4");
  const jointLegend = [
    { name: "Base Joint", color: "#ffd166" },
    { name: "Shoulder Joint", color: "#ef476f" },
    { name: "Elbow Joint", color: "#06d6a0" },
    { name: "Wrist Joint", color: "#118ab2" },
    { name: "Wrist End Marker", color: "#8ecae6" },
    { name: "Tool Mount", color: "#f77f00" },
    { name: "Pickup Point", color: "#8338ec" },
  ];
  const links = config.robot.links;
  const orderedJointEntries = useMemo(
    () =>
      ["base", "shoulder", "elbow", "wrist"]
        .filter((name) => joints[name])
        .map((name) => [name, joints[name]] as const),
    [joints],
  );
  const defaultPose = useMemo(
    () =>
      Object.fromEntries(
        orderedJointEntries.map(([name]) => {
          const jointConfig = config.robot.joints[name];
          return [name, jointConfig.home_deg];
        }),
      ) as Record<string, number>,
    [config.robot.joints, orderedJointEntries],
  );
  const [localTargets, setLocalTargets] = useState<Record<string, number>>(defaultPose);
  const displayJointAngles = useMemo(
    () =>
      Object.fromEntries(
        orderedJointEntries.map(([name, joint]) => [name, joint.target_deg ?? config.robot.joints[name].home_deg]),
      ) as Record<string, number>,
    [config.robot.joints, orderedJointEntries],
  );

  useEffect(() => {
    setIkSquare(ikTest.square || "e4");
  }, [ikTest.square]);

  useEffect(() => {
    setLocalTargets((prev) => ({ ...defaultPose, ...prev }));
  }, [defaultPose]);

  useEffect(() => {
    setLocalTargets((prev) => {
      const next = { ...prev };
      for (const [name, joint] of orderedJointEntries) {
        next[name] = joint.target_deg ?? config.robot.joints[name].home_deg;
      }
      return next;
    });
  }, [config.robot.joints, orderedJointEntries]);

  async function handleSliderChange(jointName: string, value: number) {
    setLocalTargets((prev) => ({ ...prev, [jointName]: value }));
    await onJointChange(jointName, value);
  }

  return (
    <Tile title="Robot Kinematics" className="tile-kinematics">
      <div className="kinematics-layout">
        <div className="kinematics-stage">
          <DigitalTwinScene
            config={config}
            jointAngles={displayJointAngles}
            overlay={
              <>
                <button
                  type="button"
                  className="legend-toggle-button"
                  aria-label={showLegend ? "Hide legend" : "Show legend"}
                  title={showLegend ? "Hide legend" : "Show legend"}
                  onClick={() => setShowLegend((value) => !value)}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true" className="legend-toggle-icon">
                    {showLegend ? (
                      <>
                        <path
                          d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.8" />
                      </>
                    ) : (
                      <>
                        <path
                          d="M3 3l18 18"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                        />
                        <path
                          d="M10.6 6.3A11.4 11.4 0 0 1 12 6c6.5 0 10 6 10 6a18.4 18.4 0 0 1-3.2 3.8M6.7 6.8C3.9 8.5 2 12 2 12a18 18 0 0 0 6.2 5.1A11.2 11.2 0 0 0 12 18c1.4 0 2.7-.2 3.8-.6"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        <path
                          d="M9.9 9.9A3 3 0 0 0 14.1 14.1"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                        />
                      </>
                    )}
                  </svg>
                </button>
                {showLegend ? (
                  <aside className="kinematics-legend overlay">
                    <div className="kinematics-legend-section">
                      <h3>Joints</h3>
                      {jointLegend.map((joint) => (
                        <div key={joint.name} className="legend-row">
                          <span className="legend-swatch legend-swatch-joint" style={{ background: joint.color }} />
                          <span>{joint.name}</span>
                        </div>
                      ))}
                    </div>
                    <div className="kinematics-legend-section">
                      <h3>Links</h3>
                      {links.map((link) => (
                        <div key={link.name} className="legend-row">
                          <span className="legend-swatch legend-swatch-link" style={{ background: link.color }} />
                          <span>{link.name}</span>
                        </div>
                      ))}
                    </div>
                  </aside>
                ) : null}
              </>
            }
          />
          <aside className="ik-test-panel">
            <div className="ik-test-head">
              <h3>Square IK</h3>
              <span className={`pill ${ikTest.status === "error" ? "pill-alert" : "pill-muted"}`}>{ikTest.status}</span>
            </div>
            <label className="ik-test-input-group">
              <span className="metric-label">Square</span>
              <div className="ik-test-row">
                <input
                  className="camera-select ik-test-input"
                  value={ikSquare}
                  maxLength={2}
                  onChange={(event) => setIkSquare(event.target.value.toLowerCase())}
                />
                <button type="button" className="ik-test-solve-button" onClick={() => void onIkSquareTest(ikSquare)}>
                  Solve
                </button>
              </div>
            </label>
            <div className="ik-test-actions">
              <button
                type="button"
                className="kinematics-action-button secondary"
                disabled={ikTest.step_index >= ikTest.step_total || ikTest.step_total === 0}
                onClick={() => void onIkSquareStep()}
              >
                Next Joint
              </button>
              <span className="ik-test-step">
                Step {ikTest.step_index}/{ikTest.step_total}
              </span>
            </div>
            <p className="ik-test-message">{ikTest.message}</p>
            <div className="ik-test-grid">
              <div className="ik-test-block">
                <span className="metric-label">Pose</span>
                {ikTest.pose ? (
                  <div className="ik-test-values">
                    <span>X {ikTest.pose.x_mm}</span>
                    <span>Y {ikTest.pose.y_mm}</span>
                    <span>Z {ikTest.pose.z_mm}</span>
                  </div>
                ) : (
                  <span className="ik-test-empty">No solved pose</span>
                )}
              </div>
              <div className="ik-test-block">
                <span className="metric-label">Solved Joints</span>
                {ikTest.active_joint ? <span className="ik-test-active">Next: {ikTest.active_joint}</span> : null}
                {ikTest.joint_deg ? (
                  <div className="ik-test-values">
                    {Object.entries(ikTest.joint_deg).map(([name, value]) => (
                      <span key={name}>
                        {name} {value}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="ik-test-empty">No solved joints</span>
                )}
              </div>
            </div>
          </aside>
        </div>
        <div className="kinematics-controls">
          <div className="kinematics-control-head">
            <div className="kinematics-control-title">
              <h3>Pose Control</h3>
              <div className="control-target-toggle" role="group" aria-label="Robot control target">
                <button
                  type="button"
                  className={robot.control_target === "virtual" ? "toggle-chip active" : "toggle-chip"}
                  onClick={() => void onRobotControlTarget("virtual")}
                >
                  Virtual
                </button>
                <button
                  type="button"
                  className={robot.control_target === "hardware" ? "toggle-chip active" : "toggle-chip"}
                  onClick={() => void onRobotControlTarget("hardware")}
                  disabled={!robot.hardware_available}
                  title={robot.hardware_available ? "Control real robot arm" : robot.hardware_status}
                >
                  Real Robot
                </button>
              </div>
            </div>
            <div className="control-target-status">{robot.hardware_status}</div>
            <div className="kinematics-action-row">
              <button type="button" className="kinematics-action-button" onClick={() => void onRobotHome()}>
                Home
              </button>
              <button type="button" className="kinematics-action-button secondary" onClick={() => void onRobotSaveHome()}>
                Save Home
              </button>
              <button
                type="button"
                className={robot.gripper_state === "closed" ? "kinematics-action-button" : "kinematics-action-button secondary"}
                onClick={() => void onToggleGripper()}
              >
                Gripper {robot.gripper_state === "closed" ? "On" : "Off"}
              </button>
            </div>
          </div>
          <div className="joint-list embedded compact">
            {orderedJointEntries.map(([name, joint]) => (
              <article className="joint-card compact minimalist" key={name}>
                {(() => {
                  const targetAngle = localTargets[name] ?? joint.target_deg ?? config.robot.joints[name].home_deg;
                  const targetDeg = joint.target_deg ?? config.robot.joints[name].home_deg;
                  const actualDeg = joint.current_deg ?? targetDeg;
                  const minimumDeg = joint.minimum_deg ?? config.robot.joints[name].min_deg;
                  const maximumDeg = joint.maximum_deg ?? config.robot.joints[name].max_deg;
                  const controlMode = joint.control_mode ?? "manual";

                  return (
                    <>
                <div className="joint-card-head compact minimalist">
                  <h3>{joint.label}</h3>
                </div>
                <input
                  className="joint-slider"
                  type="range"
                  min={minimumDeg}
                  max={maximumDeg}
                  step={0.5}
                  value={targetAngle}
                  disabled={controlMode !== "manual"}
                  onChange={(event) => void handleSliderChange(name, Number(event.target.value))}
                />
                <div className="joint-values-block">
                  <div className="joint-values-row emphasis">
                    <span>Target angle</span>
                    <span>{Math.round(targetDeg)} deg</span>
                  </div>
                  <div className="joint-values-row emphasis">
                    <span>Actual angle</span>
                    <span>{Math.round(actualDeg)} deg</span>
                  </div>
                  <div className="joint-values-row">
                    <span>Target pulse</span>
                    <span>{Math.round(joint.target)}</span>
                  </div>
                  {controlMode !== "manual" ? (
                    <div className="joint-values-row">
                      <span>Control mode</span>
                      <span>{controlMode}</span>
                    </div>
                  ) : null}
                  <div className="joint-values-row">
                    <span>Actual pulse</span>
                    <span>{Math.round(joint.current)}</span>
                  </div>
                </div>
                <div className="joint-range-row">
                  <span>
                    pulse {joint.minimum} to {joint.maximum}
                  </span>
                  <span>
                    deg {minimumDeg} to {maximumDeg}
                  </span>
                </div>
                <div className="joint-rail">
                  <div
                    className="joint-target-bar"
                    style={{ width: `${widthPercent(targetDeg, minimumDeg, maximumDeg)}%` }}
                  />
                  <div
                    className="joint-current-bar"
                    style={{ width: `${widthPercent(actualDeg, minimumDeg, maximumDeg)}%` }}
                  />
                </div>
                    </>
                  );
                })()}
              </article>
            ))}
          </div>
        </div>
      </div>
    </Tile>
  );
}
