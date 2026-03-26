import { useEffect, useRef, useState, type MouseEvent } from "react";
import type { TrainingState } from "../types";
import { Tile } from "./Tile";

type TrainingPanelProps = {
  training: TrainingState;
  active: boolean;
  onCaptureSnapshot: () => void;
  onSetDatasetPath: (datasetPath: string) => void;
  onSetLabelMode: (mode: "white" | "black" | "empty") => void;
  onSelectSnapshot: (index: number) => void;
  onAnnotateSquare: (x: number, y: number) => void;
  onResetLabels: () => void;
  onCompleteSnapshot: () => void;
};

const LABEL_MODES: Array<"white" | "black" | "empty"> = ["white", "black", "empty"];

export function TrainingPanel({
  training,
  active,
  onCaptureSnapshot,
  onSetDatasetPath,
  onSetLabelMode,
  onSelectSnapshot,
  onAnnotateSquare,
  onResetLabels,
  onCompleteSnapshot,
}: TrainingPanelProps) {
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [datasetPathInput, setDatasetPathInput] = useState(training.dataset_path);
  const hasSnapshots = training.snapshot_count > 0 && training.active_snapshot_index >= 0;

  useEffect(() => {
    setDatasetPathInput(training.dataset_path);
  }, [training.dataset_path]);

  function handleSnapshotClick(event: MouseEvent<HTMLDivElement>) {
    if (!active || !hasSnapshots) {
      return;
    }

    const image = imageRef.current;
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

    onAnnotateSquare(localX / renderedWidth, localY / renderedHeight);
  }

  return (
    <Tile title="Labelling" className={`tile-training ${active ? "active" : "inactive"}`}>
      <div className={`training-controls ${active ? "active" : "inactive"}`}>
        {active ? (
          <>
          <div className="training-action-row">
            <button type="button" onClick={onCaptureSnapshot}>
              Capture Snapshot
            </button>
            <button
              type="button"
              onClick={() => onSelectSnapshot(training.active_snapshot_index - 1)}
              disabled={training.active_snapshot_index <= 0}
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => onSelectSnapshot(training.active_snapshot_index + 1)}
              disabled={training.active_snapshot_index < 0 || training.active_snapshot_index >= training.snapshot_count - 1}
            >
              Next
            </button>
            <button type="button" onClick={onResetLabels} disabled={!hasSnapshots}>
              Reset Labels
            </button>
            <button type="button" onClick={onCompleteSnapshot} disabled={!hasSnapshots}>
              Save Snapshot
            </button>
          </div>

          <div className="training-meta-row">
            <span>
              Snapshot {hasSnapshots ? training.active_snapshot_index + 1 : 0} / {training.snapshot_count}
            </span>
            <span>Saved: {training.saved_snapshot_count}</span>
          </div>

          <div className="training-dataset-row">
            <label className="training-dataset-group">
              <span className="metric-label">Dataset Export Folder</span>
              <input
                className="training-dataset-input"
                type="text"
                value={datasetPathInput}
                onChange={(event) => setDatasetPathInput(event.target.value)}
                onBlur={() => {
                  const next = datasetPathInput.trim();
                  if (next && next !== training.dataset_path) {
                    onSetDatasetPath(next);
                  } else if (!next) {
                    setDatasetPathInput(training.dataset_path);
                  }
                }}
              />
            </label>
          </div>

          <div className="training-label-row">
            {LABEL_MODES.map((mode) => (
              <button
                key={mode}
                type="button"
                className={training.label_mode === mode ? "workflow-button active" : "workflow-button"}
                onClick={() => onSetLabelMode(mode)}
              >
                {mode}
              </button>
            ))}
          </div>

          {hasSnapshots ? (
            <div className="training-snapshot-frame" onClick={handleSnapshotClick}>
              <img
                ref={imageRef}
                className="training-snapshot-image"
                src={`${training.active_snapshot_url}?v=${training.revision}`}
                alt="Training snapshot with grid overlay"
              />
            </div>
          ) : (
            <div className="training-copy training-copy-muted">
              <p>Capture a board snapshot to start board-wide annotation.</p>
              <p>Then choose `white`, `black`, or `empty` and click all matching squares.</p>
            </div>
          )}
          </>
        ) : (
          <div className="training-copy training-copy-muted">
            <p>Select `Label` after corner selection to enable the labelling workflow.</p>
          </div>
        )}
      </div>
    </Tile>
  );
}
