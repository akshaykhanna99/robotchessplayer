import { useRef, type MouseEvent } from "react";
import type { GameState, VisionState } from "../types";
import { BoardPreview } from "./BoardPreview";
import { Tile } from "./Tile";

type VisionTileProps = {
  vision: VisionState;
  game: GameState;
  cameraSource: string;
  availableCameras: string[];
  workflowMode: "label" | "play" | null;
  onCameraSourceChange: (source: string) => void;
  onBoardProcessingAction: (action: string) => void;
  onVisionCornerSelect: (x: number, y: number) => void;
  onWorkflowModeChange: (mode: "label" | "play") => void | Promise<void>;
};

export function VisionTile({
  vision,
  game,
  cameraSource,
  availableCameras,
  workflowMode,
  onCameraSourceChange,
  onBoardProcessingAction,
  onVisionCornerSelect,
  onWorkflowModeChange,
}: VisionTileProps) {
  const cameraImageRef = useRef<HTMLImageElement | null>(null);

  function handleCameraClick(event: MouseEvent<HTMLDivElement>) {
    if (!vision.corner_selection_active) {
      return;
    }

    const image = cameraImageRef.current;
    if (!image) {
      return;
    }

    const bounds = image.getBoundingClientRect();
    const naturalWidth = image.naturalWidth;
    const naturalHeight = image.naturalHeight;
    if (!naturalWidth || !naturalHeight || !bounds.width || !bounds.height) {
      return;
    }

    const imageAspect = naturalWidth / naturalHeight;
    const boxAspect = bounds.width / bounds.height;

    let renderedWidth = bounds.width;
    let renderedHeight = bounds.height;
    let offsetX = 0;
    let offsetY = 0;

    if (imageAspect > boxAspect) {
      renderedHeight = bounds.width / imageAspect;
      offsetY = (bounds.height - renderedHeight) / 2;
    } else {
      renderedWidth = bounds.height * imageAspect;
      offsetX = (bounds.width - renderedWidth) / 2;
    }

    const localX = event.clientX - bounds.left - offsetX;
    const localY = event.clientY - bounds.top - offsetY;

    if (localX < 0 || localY < 0 || localX > renderedWidth || localY > renderedHeight) {
      return;
    }

    onVisionCornerSelect(localX / renderedWidth, localY / renderedHeight);
  }

  return (
    <Tile title="Game" className="tile-vision">
      <div className="vision-layout">
        <div className="vision-stage">
          <div
            className={`camera-frame ${vision.corner_selection_active ? "corner-mode" : ""}`}
            onClick={handleCameraClick}
          >
            {vision.camera_connected ? (
              <img
                ref={cameraImageRef}
                className="camera-feed"
                src={vision.board_initialized ? vision.board_stream_url : vision.stream_url}
                alt={vision.board_initialized ? "Warped board feed" : "Live camera feed"}
              />
            ) : (
              <div className="camera-empty">No live feed. Select a camera below.</div>
            )}
            {vision.corner_selection_active ? (
              <div className="corner-instruction-overlay">
                <strong className="corner-target">{vision.next_corner_label}</strong>
              </div>
            ) : null}
          </div>
          <BoardPreview
            fen={game.fen}
            observedBoard={game.observed_board}
            observedBoardInitialized={game.observed_board_initialized}
            sessionActive={game.session_active}
            detectedMove={game.detected_move}
            sideToMove={game.side_to_move}
            suggestedMove={game.suggested_move}
          />
        </div>

        <div className="preprocessing-controls">
          <span className="metric-label">Pre-processing</span>
          <div className="preprocessing-row">
            <label className="camera-select-group">
              <span className="metric-label">Camera</span>
              <select
                className="camera-select"
                value={cameraSource}
                onChange={(event) => onCameraSourceChange(event.target.value)}
              >
                {!availableCameras.includes(cameraSource) ? (
                  <option value={cameraSource}>{cameraSource}</option>
                ) : null}
                {availableCameras.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <div className="camera-status-group">
              <span className={`status-light ${vision.camera_connected ? "online" : "offline"}`} />
              <span>{vision.camera_connected ? "Camera Online" : "Camera Offline"}</span>
            </div>

            <button type="button" onClick={() => onBoardProcessingAction("select_corners")}>
              Select Corners
            </button>
            <button type="button" onClick={() => onBoardProcessingAction("reset_corners")}>
              Reset Corners
            </button>
          </div>

          {vision.board_initialized ? (
            <div className="workflow-mode-row">
              <button
                type="button"
                className={workflowMode === "label" ? "workflow-button active" : "workflow-button"}
                onClick={() => onWorkflowModeChange("label")}
              >
                Label
              </button>
              <button
                type="button"
                className={workflowMode === "play" ? "workflow-button active" : "workflow-button"}
                onClick={() => onWorkflowModeChange("play")}
              >
                Play
              </button>
              <button type="button" onClick={() => onBoardProcessingAction("reset_board")}>
                Reset Board
              </button>
              {workflowMode === "play" ? (
                <button type="button" onClick={() => onBoardProcessingAction("run_inference")}>
                  Run Inference
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </Tile>
  );
}
