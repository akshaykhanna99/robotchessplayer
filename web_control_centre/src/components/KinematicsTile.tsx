import { useEffect, useMemo, useState } from "react";
import twinConfig from "../../../config/digital_twin_setup_v1.json";
import type { JointState } from "../types";
import type { DigitalTwinConfig } from "../digitalTwinTypes";
import { DigitalTwinScene } from "./DigitalTwinScene";
import { Tile } from "./Tile";

type KinematicsTileProps = {
  joints: Record<string, JointState>;
  onJointChange: (joint: string, value: number) => Promise<void> | void;
};

const HOME_STORAGE_KEY = "robot-chess-player:digital-twin-home-pose";

function widthPercent(value: number, min: number, max: number) {
  if (max <= min) {
    return 0;
  }
  return ((value - min) / (max - min)) * 100;
}

function mapPulseToDegrees(value: number, pulseMin: number, pulseMax: number, degMin: number, degMax: number) {
  if (pulseMax <= pulseMin) {
    return degMin;
  }
  const ratio = (value - pulseMin) / (pulseMax - pulseMin);
  return degMin + ratio * (degMax - degMin);
}

export function KinematicsTile({ joints, onJointChange }: KinematicsTileProps) {
  const config = twinConfig as DigitalTwinConfig;
  const [showLegend, setShowLegend] = useState(true);
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
  const defaultHomePose = useMemo(
    () =>
      Object.fromEntries(
        orderedJointEntries.map(([name, joint]) => [name, joint.target]),
      ) as Record<string, number>,
    [orderedJointEntries],
  );
  const [homePose, setHomePose] = useState<Record<string, number>>(defaultHomePose);
  const [localTargets, setLocalTargets] = useState<Record<string, number>>(defaultHomePose);

  useEffect(() => {
    const savedHomePose = window.localStorage.getItem(HOME_STORAGE_KEY);
    if (savedHomePose) {
      try {
        const parsed = JSON.parse(savedHomePose) as Record<string, number>;
        setHomePose({ ...defaultHomePose, ...parsed });
      } catch {
        setHomePose(defaultHomePose);
      }
    } else {
      setHomePose(defaultHomePose);
    }
    setLocalTargets((prev) => ({ ...defaultHomePose, ...prev }));
  }, [defaultHomePose]);

  useEffect(() => {
    setLocalTargets((prev) => {
      const next = { ...prev };
      for (const [name, joint] of orderedJointEntries) {
        next[name] = joint.target;
      }
      return next;
    });
  }, [orderedJointEntries]);

  async function handleSliderChange(jointName: string, value: number) {
    setLocalTargets((prev) => ({ ...prev, [jointName]: value }));
    await onJointChange(jointName, value);
  }

  async function handleResetHome() {
    for (const [jointName, value] of Object.entries(homePose)) {
      setLocalTargets((prev) => ({ ...prev, [jointName]: value }));
      await onJointChange(jointName, value);
    }
  }

  function handleSaveHome() {
    const nextHomePose = { ...localTargets };
    setHomePose(nextHomePose);
    window.localStorage.setItem(HOME_STORAGE_KEY, JSON.stringify(nextHomePose));
  }

  return (
    <Tile title="Robot Kinematics" className="tile-kinematics">
      <div className="kinematics-layout">
        <div className="kinematics-stage">
          <DigitalTwinScene
            config={config}
            jointAngles={localTargets}
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
        </div>
        <div className="kinematics-controls">
          <div className="kinematics-control-head">
            <h3>Pose Control</h3>
            <div className="kinematics-action-row">
              <button type="button" className="kinematics-action-button" onClick={handleResetHome}>
                Home
              </button>
              <button type="button" className="kinematics-action-button secondary" onClick={handleSaveHome}>
                Save Home
              </button>
            </div>
          </div>
          <div className="joint-list embedded compact">
            {orderedJointEntries.map(([name, joint]) => (
              <article className="joint-card compact minimalist" key={name}>
                {(() => {
                  const jointConfig = config.robot.joints[name];
                  const targetPulse = localTargets[name] ?? joint.target;
                  const actualPulse = joint.current;
                  const targetDeg = mapPulseToDegrees(
                    targetPulse,
                    joint.minimum,
                    joint.maximum,
                    jointConfig.min_deg,
                    jointConfig.max_deg,
                  );
                  const actualDeg = mapPulseToDegrees(
                    actualPulse,
                    joint.minimum,
                    joint.maximum,
                    jointConfig.min_deg,
                    jointConfig.max_deg,
                  );

                  return (
                    <>
                <div className="joint-card-head compact minimalist">
                  <h3>{joint.label}</h3>
                </div>
                <input
                  className="joint-slider"
                  type="range"
                  min={joint.minimum}
                  max={joint.maximum}
                  step={1}
                  value={targetPulse}
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
                    <span>{Math.round(targetPulse)}</span>
                  </div>
                  <div className="joint-values-row">
                    <span>Actual pulse</span>
                    <span>{Math.round(actualPulse)}</span>
                  </div>
                </div>
                <div className="joint-range-row">
                  <span>
                    pulse {joint.minimum} to {joint.maximum}
                  </span>
                  <span>
                    deg {jointConfig.min_deg} to {jointConfig.max_deg}
                  </span>
                </div>
                <div className="joint-rail">
                  <div
                    className="joint-target-bar"
                    style={{ width: `${widthPercent(targetPulse, joint.minimum, joint.maximum)}%` }}
                  />
                  <div
                    className="joint-current-bar"
                    style={{ width: `${widthPercent(joint.current, joint.minimum, joint.maximum)}%` }}
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
