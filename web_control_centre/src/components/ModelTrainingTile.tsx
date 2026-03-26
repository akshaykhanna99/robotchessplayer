import { useEffect, useState } from "react";
import type { TrainingState } from "../types";
import { Tile } from "./Tile";

type ModelTrainingTileProps = {
  training: TrainingState;
  onStartTraining: (datasetPath: string, modelName: string) => void;
};

export function ModelTrainingTile({ training, onStartTraining }: ModelTrainingTileProps) {
  const [datasetPathInput, setDatasetPathInput] = useState(training.dataset_path);
  const [modelNameInput, setModelNameInput] = useState("");

  useEffect(() => {
    setDatasetPathInput(training.dataset_path);
  }, [training.dataset_path]);

  return (
    <Tile title="Training" className="tile-model-training">
      <div className="model-training-controls">
        <label className="training-dataset-group">
          <span className="metric-label">Dataset Folder</span>
          <input
            className="training-dataset-input"
            type="text"
            value={datasetPathInput}
            onChange={(event) => setDatasetPathInput(event.target.value)}
          />
        </label>

        <label className="training-dataset-group">
          <span className="metric-label">Classifier Name</span>
          <input
            className="training-dataset-input"
            type="text"
            placeholder="classifier_YYYYMMDD_HHMMSS"
            value={modelNameInput}
            onChange={(event) => setModelNameInput(event.target.value)}
          />
        </label>

        <div className="training-action-row">
          <button
            type="button"
            onClick={() => onStartTraining(datasetPathInput.trim(), modelNameInput.trim())}
            disabled={training.job_status === "running"}
          >
            Train Model
          </button>
        </div>

        <div className="training-meta-row">
          <span>Status: {training.job_status}</span>
          {training.job_output_model ? <span>Output: {training.job_output_model}</span> : null}
        </div>

        <div className="training-copy">
          <p>{training.job_message}</p>
        </div>
      </div>
    </Tile>
  );
}
