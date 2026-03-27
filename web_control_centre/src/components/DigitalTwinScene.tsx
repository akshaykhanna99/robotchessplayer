import { useEffect, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import type { DigitalTwinConfig, PieceTypeConfig } from "../digitalTwinTypes";

const FILES = "abcdefgh";
const RANKS = "12345678";

const STARTING_PIECES: Array<{ square: string; type: keyof DigitalTwinConfig["pieces"]["types"]; side: "white" | "black" }> = [
  ...FILES.split("").map((file) => ({ square: `${file}2`, type: "pawn" as const, side: "white" as const })),
  ...FILES.split("").map((file) => ({ square: `${file}7`, type: "pawn" as const, side: "black" as const })),
  { square: "a1", type: "rook", side: "white" },
  { square: "h1", type: "rook", side: "white" },
  { square: "a8", type: "rook", side: "black" },
  { square: "h8", type: "rook", side: "black" },
  { square: "b1", type: "knight", side: "white" },
  { square: "g1", type: "knight", side: "white" },
  { square: "b8", type: "knight", side: "black" },
  { square: "g8", type: "knight", side: "black" },
  { square: "c1", type: "bishop", side: "white" },
  { square: "f1", type: "bishop", side: "white" },
  { square: "c8", type: "bishop", side: "black" },
  { square: "f8", type: "bishop", side: "black" },
  { square: "d1", type: "queen", side: "white" },
  { square: "d8", type: "queen", side: "black" },
  { square: "e1", type: "king", side: "white" },
  { square: "e8", type: "king", side: "black" },
];

type DigitalTwinSceneProps = {
  config: DigitalTwinConfig;
};

type ViewPreset = "iso" | "top" | "front" | "right";

const VIEW_PRESETS: Record<ViewPreset, [number, number, number]> = {
  iso: [-180, -220, 220],
  top: [80, 80, 420],
  front: [90, -260, 120],
  right: [420, 90, 120],
};

function axisRotation(axis: string, degrees: number): [number, number, number] {
  const radians = (degrees * Math.PI) / 180;
  if (axis === "x") {
    return [radians, 0, 0];
  }
  if (axis === "y") {
    return [0, radians, 0];
  }
  return [0, 0, radians];
}

function SceneCamera({ viewPreset, controls }: { viewPreset: ViewPreset; controls: OrbitControlsImpl | null }) {
  const { camera } = useThree();

  useEffect(() => {
    camera.up.set(0, 0, 1);
    const [x, y, z] = VIEW_PRESETS[viewPreset];
    camera.position.set(x, y, z);
    const targetX = 80;
    const targetY = 80;
    const targetZ = 0;
    if (viewPreset === "top") {
      camera.up.set(0, 1, 0);
    }
    camera.lookAt(targetX, targetY, targetZ);
    controls?.target.set(targetX, targetY, targetZ);
    controls?.update();
  }, [camera, controls, viewPreset]);

  return null;
}

function OriginMarker({ z }: { z: number }) {
  const axisLength = 40;
  const axisRadius = 0.9;

  return (
    <group position={[0, 0, z]}>
      <mesh castShadow position={[0, 0, 0]}>
        <sphereGeometry args={[3, 20, 20]} />
        <meshStandardMaterial color="#f7f4ed" emissive="#ffffff" emissiveIntensity={0.45} />
      </mesh>
      <mesh position={[axisLength / 2, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
        <cylinderGeometry args={[axisRadius, axisRadius, axisLength, 16]} />
        <meshStandardMaterial color="#bf4040" />
      </mesh>
      <mesh position={[0, axisLength / 2, 0]}>
        <cylinderGeometry args={[axisRadius, axisRadius, axisLength, 16]} />
        <meshStandardMaterial color="#3c9b5d" />
      </mesh>
      <mesh position={[0, 0, axisLength / 2]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[axisRadius, axisRadius, axisLength, 16]} />
        <meshStandardMaterial color="#346fc7" />
      </mesh>
      <Html position={[10, -8, 8]} center distanceFactor={14}>
        <div className="origin-label">Origin</div>
      </Html>
    </group>
  );
}

function Board({ config }: DigitalTwinSceneProps) {
  const { board } = config;
  const playableSize = board.square_size_mm * 8;
  const playableOffsetX = board.origin_x_mm + (board.board_size_x_mm - playableSize) / 2;
  const playableOffsetY = board.origin_y_mm + (board.board_size_y_mm - playableSize) / 2;
  const boardCenterX = board.origin_x_mm + board.board_size_x_mm / 2;
  const boardCenterY = board.origin_y_mm + board.board_size_y_mm / 2;
  const boardCenterZ = board.origin_z_mm - board.thickness_mm / 2;

  return (
    <group>
      <mesh position={[boardCenterX, boardCenterY, boardCenterZ]} receiveShadow>
        <boxGeometry args={[board.board_size_x_mm, board.board_size_y_mm, board.thickness_mm]} />
        <meshStandardMaterial color={board.border_color} />
      </mesh>
      {RANKS.split("").flatMap((_, rankIdx) =>
        FILES.split("").map((_, fileIdx) => {
          const isLight = (fileIdx + rankIdx) % 2 !== 0;
          const x = playableOffsetX + (fileIdx + 0.5) * board.square_size_mm;
          const y = playableOffsetY + (rankIdx + 0.5) * board.square_size_mm;
          return (
            <mesh key={`${fileIdx}-${rankIdx}`} position={[x, y, board.origin_z_mm + 0.15]} receiveShadow>
              <boxGeometry args={[board.square_size_mm, board.square_size_mm, 0.3]} />
              <meshStandardMaterial color={isLight ? board.light_square_color : board.dark_square_color} />
            </mesh>
          );
        }),
      )}
    </group>
  );
}

function Pieces({ config }: DigitalTwinSceneProps) {
  const { board, pieces } = config;
  const playableSize = board.square_size_mm * 8;
  const playableOffsetX = board.origin_x_mm + (board.board_size_x_mm - playableSize) / 2;
  const playableOffsetY = board.origin_y_mm + (board.board_size_y_mm - playableSize) / 2;

  return (
    <>
      {STARTING_PIECES.map((piece) => {
        const pieceType = pieces.types[piece.type] as PieceTypeConfig | undefined;
        if (!pieceType) {
          return null;
        }

        const fileIdx = FILES.indexOf(piece.square[0]);
        const rankIdx = RANKS.indexOf(piece.square[1]);
        const x = playableOffsetX + (fileIdx + 0.5) * board.square_size_mm;
        const y = playableOffsetY + (rankIdx + 0.5) * board.square_size_mm;
        const color = piece.side === "white" ? pieceType.color : "#2c2f34";

        return (
          <group key={`${piece.side}-${piece.square}`} position={[x, y, board.origin_z_mm]}>
            <mesh castShadow receiveShadow position={[0, 0, pieceType.height_mm / 2]} rotation={[Math.PI / 2, 0, 0]}>
              <cylinderGeometry args={[pieceType.diameter_mm / 2, pieceType.diameter_mm / 2, pieceType.height_mm, 28]} />
              <meshStandardMaterial color={color} />
            </mesh>
          </group>
        );
      })}
    </>
  );
}

function RobotBase({ config }: DigitalTwinSceneProps) {
  const { robot } = config;
  const { base_frame, base_geometry } = robot;
  const shoulderLink = robot.links.find((link) => link.name === "shoulder");
  const elbowLink = robot.links.find((link) => link.name === "elbow");
  const wristLink = robot.links.find((link) => link.name === "wrist");
  const baseJoint = robot.joints.base;
  const shoulderJoint = robot.joints.shoulder;
  const elbowJoint = robot.joints.elbow;
  const wristJoint = robot.joints.wrist;
  const baseRotation = axisRotation(baseJoint.axis, baseJoint.home_deg + base_frame.yaw_deg);
  const shoulderRotation = axisRotation(shoulderJoint.axis, shoulderJoint.home_deg);
  const elbowRotation = axisRotation(elbowJoint.axis, elbowJoint.home_deg);
  const wristRotation = axisRotation(wristJoint.axis, wristJoint.home_deg);

  return (
    <group position={[base_frame.x_mm, base_frame.y_mm, base_frame.z_mm]} rotation={baseRotation}>
      <mesh castShadow receiveShadow position={[0, 0, -base_geometry.height_mm / 2]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[base_geometry.radius_mm, base_geometry.radius_mm, base_geometry.height_mm, 48]} />
        <meshStandardMaterial color={base_geometry.color} />
      </mesh>
      <mesh castShadow>
        <sphereGeometry args={[3.2, 20, 20]} />
        <meshStandardMaterial color="#ffd166" emissive="#7c5a00" emissiveIntensity={0.35} />
      </mesh>
      {shoulderLink ? (
        <group rotation={shoulderRotation}>
          <mesh castShadow receiveShadow position={[0, 0, shoulderLink.length_mm / 2]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[shoulderLink.radius_mm, shoulderLink.radius_mm, shoulderLink.length_mm, 32]} />
            <meshStandardMaterial color={shoulderLink.color} />
          </mesh>
          <mesh castShadow position={[0, 0, shoulderLink.length_mm]}>
            <sphereGeometry args={[shoulderLink.radius_mm * 1.1, 20, 20]} />
            <meshStandardMaterial color="#d7dfe6" />
          </mesh>
          {elbowLink ? (
            <group position={[0, 0, shoulderLink.length_mm]} rotation={elbowRotation}>
              <mesh
                castShadow
                receiveShadow
                position={[0, 0, elbowLink.length_mm / 2]}
                rotation={[Math.PI / 2, 0, 0]}
              >
                <cylinderGeometry args={[elbowLink.radius_mm, elbowLink.radius_mm, elbowLink.length_mm, 32]} />
                <meshStandardMaterial color={elbowLink.color} />
              </mesh>
              <mesh castShadow position={[0, 0, elbowLink.length_mm]}>
                <sphereGeometry args={[elbowLink.radius_mm * 1.1, 20, 20]} />
                <meshStandardMaterial color="#d7dfe6" />
              </mesh>
              {wristLink ? (
                <group position={[0, 0, elbowLink.length_mm]}>
                  <mesh
                    castShadow
                    receiveShadow
                    position={[-wristLink.length_mm / 2, 0, 0]}
                    rotation={[0, 0, Math.PI / 2]}
                  >
                    <cylinderGeometry args={[wristLink.radius_mm, wristLink.radius_mm, wristLink.length_mm, 32]} />
                    <meshStandardMaterial color={wristLink.color} />
                  </mesh>
                  <mesh castShadow position={[-wristLink.length_mm, 0, 0]}>
                    <sphereGeometry args={[wristLink.radius_mm * 1.15, 20, 20]} />
                    <meshStandardMaterial color="#d7dfe6" />
                  </mesh>
                  <group position={[-wristLink.length_mm, 0, 0]} rotation={wristRotation} />
                </group>
              ) : null}
            </group>
          ) : null}
        </group>
      ) : null}
    </group>
  );
}

function SceneContent({
  config,
  viewPreset,
  controls,
  onControlsChange,
}: DigitalTwinSceneProps & {
  viewPreset: ViewPreset;
  controls: OrbitControlsImpl | null;
  onControlsChange: (controls: OrbitControlsImpl | null) => void;
}) {
  return (
    <>
      <SceneCamera viewPreset={viewPreset} controls={controls} />
      <color attach="background" args={[config.rendering.background]} />
      <ambientLight intensity={0.95} />
      <directionalLight position={[-180, -160, 260]} intensity={1.2} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048} />
      <directionalLight position={[220, 140, 120]} intensity={0.28} />
      <Board config={config} />
      <Pieces config={config} />
      <RobotBase config={config} />
      <OriginMarker z={config.board.origin_z_mm} />
      <OrbitControls makeDefault ref={onControlsChange} />
    </>
  );
}

export function DigitalTwinScene({ config }: DigitalTwinSceneProps) {
  const [viewPreset, setViewPreset] = useState<ViewPreset>("iso");
  const [controls, setControls] = useState<OrbitControlsImpl | null>(null);

  return (
    <div className="digital-twin-stage">
      <div className="digital-twin-viewbar">
        <button type="button" className={`view-chip ${viewPreset === "iso" ? "active" : ""}`} onClick={() => setViewPreset("iso")}>
          Iso
        </button>
        <button type="button" className={`view-chip ${viewPreset === "top" ? "active" : ""}`} onClick={() => setViewPreset("top")}>
          Top
        </button>
        <button
          type="button"
          className={`view-chip ${viewPreset === "front" ? "active" : ""}`}
          onClick={() => setViewPreset("front")}
        >
          Front
        </button>
        <button
          type="button"
          className={`view-chip ${viewPreset === "right" ? "active" : ""}`}
          onClick={() => setViewPreset("right")}
        >
          Right
        </button>
      </div>
      <Canvas shadows camera={{ fov: 34, near: 1, far: 4000 }}>
        <SceneContent config={config} viewPreset={viewPreset} controls={controls} onControlsChange={setControls} />
      </Canvas>
    </div>
  );
}
