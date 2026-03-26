import type { SettingsState } from "../types";
import { Tile } from "./Tile";

type GeneralSettingsTileProps = {
  settings: SettingsState;
  onSetActiveClassifier: (classifierPath: string) => void;
};

export function GeneralSettingsTile({ settings, onSetActiveClassifier }: GeneralSettingsTileProps) {
  return (
    <Tile title="General Settings" className="tile-general-settings">
      <div className="general-settings-grid">
        <label className="training-dataset-group">
          <span className="metric-label">Active Classifier</span>
          <select
            className="camera-select"
            value={settings.active_classifier_path}
            onChange={(event) => onSetActiveClassifier(event.target.value)}
          >
            {settings.available_classifiers.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="training-copy training-copy-muted">
        <p>Play mode uses the active classifier selected here.</p>
      </div>
    </Tile>
  );
}
