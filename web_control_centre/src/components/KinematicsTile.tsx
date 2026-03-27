import twinConfig from "../../../config/digital_twin_setup_v1.json";
import type { DigitalTwinConfig } from "../digitalTwinTypes";
import { DigitalTwinScene } from "./DigitalTwinScene";
import { Tile } from "./Tile";

export function KinematicsTile() {
  return (
    <Tile title="Robot Kinematics" className="tile-kinematics">
      <div className="kinematics-stage">
        <DigitalTwinScene config={twinConfig as DigitalTwinConfig} />
      </div>
    </Tile>
  );
}
