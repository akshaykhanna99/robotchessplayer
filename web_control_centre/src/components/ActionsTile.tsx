import { Tile } from "./Tile";

const ACTIONS = [
  "run_inference",
  "reset_corners",
  "toggle_execution",
  "toggle_gripper",
  "reset_pose",
  "estop",
] as const;

type ActionsTileProps = {
  onAction: (action: string) => void;
};

export function ActionsTile({ onAction }: ActionsTileProps) {
  return (
    <Tile title="Quick Actions" className="tile-actions" aside={<span className="pill pill-muted">API-linked</span>}>
      <div className="action-grid">
        {ACTIONS.map((action) => (
          <button
            key={action}
            className={action === "estop" ? "danger" : ""}
            onClick={() => onAction(action)}
          >
            {action.replace(/_/g, " ")}
          </button>
        ))}
      </div>
    </Tile>
  );
}
