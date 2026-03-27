import { useEffect, useState } from "react";
import {
  annotateTrainingSquare,
  captureTrainingSnapshot,
  completeTrainingSnapshot,
  fetchState,
  resetTrainingLabels,
  sendAction,
  setActiveTrainingSnapshot,
  setActiveClassifier,
  setCameraSource,
  setJointTarget,
  solveIkSquareTest,
  stepIkSquareTest,
  startPlayMode,
  startModelTraining,
  setTrainingDatasetPath,
  setTrainingLabelMode,
  submitVisionCorner,
} from "./api";
import { GeneralSettingsTile } from "./components/GeneralSettingsTile";
import { KinematicsTile } from "./components/KinematicsTile";
import { LogsTile } from "./components/LogsTile";
import { ModelTrainingTile } from "./components/ModelTrainingTile";
import { TrainingPanel } from "./components/TrainingPanel";
import { VisionTile } from "./components/VisionTile";
import type { CommandCentreState } from "./types";

const POLL_INTERVAL_MS = 500;

export default function App() {
  const [state, setState] = useState<CommandCentreState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [workflowMode, setWorkflowMode] = useState<"label" | "play" | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [logsOpen, setLogsOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const nextState = await fetchState();
        if (!cancelled) {
          setState(nextState);
          setError(null);
        }
      } catch (pollError) {
        if (!cancelled) {
          setError(pollError instanceof Error ? pollError.message : "Unknown error");
        }
      } finally {
        if (!cancelled) {
          window.setTimeout(poll, POLL_INTERVAL_MS);
        }
      }
    }

    poll();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!state?.vision.board_initialized) {
      setWorkflowMode(null);
    }
  }, [state?.vision.board_initialized]);

  async function handleJointChange(joint: string, value: number) {
    await setJointTarget(joint, value);
    setState(await fetchState());
  }

  async function handleCameraSourceChange(source: string) {
    await setCameraSource(source);
    setState(await fetchState());
  }

  async function handleBoardProcessingAction(action: string) {
    await sendAction(action);
    setState(await fetchState());
  }

  async function handleVisionCornerSelect(x: number, y: number) {
    await submitVisionCorner(x, y);
    setState(await fetchState());
  }

  async function handleCaptureTrainingSnapshot() {
    await captureTrainingSnapshot();
    setState(await fetchState());
  }

  async function handleSetTrainingLabelMode(mode: "white" | "black" | "empty") {
    await setTrainingLabelMode(mode);
    setState(await fetchState());
  }

  async function handleSetTrainingDatasetPath(datasetPath: string) {
    await setTrainingDatasetPath(datasetPath);
    setState(await fetchState());
  }

  async function handleSelectTrainingSnapshot(index: number) {
    await setActiveTrainingSnapshot(index);
    setState(await fetchState());
  }

  async function handleAnnotateTrainingSquare(x: number, y: number) {
    await annotateTrainingSquare(x, y);
    setState(await fetchState());
  }

  async function handleResetTrainingLabels() {
    await resetTrainingLabels();
    setState(await fetchState());
  }

  async function handleCompleteTrainingSnapshot() {
    await completeTrainingSnapshot();
    setState(await fetchState());
  }

  async function handleStartModelTraining(datasetPath: string, modelName: string) {
    await startModelTraining(datasetPath, modelName);
    setState(await fetchState());
  }

  async function handleSetActiveClassifier(classifierPath: string) {
    await setActiveClassifier(classifierPath);
    setState(await fetchState());
  }

  async function handleWorkflowModeChange(mode: "label" | "play") {
    if (mode === "play") {
      await startPlayMode();
      setState(await fetchState());
    }
    setWorkflowMode(mode);
  }

  async function handleIkSquareTest(square: string) {
    await solveIkSquareTest(square);
    setState(await fetchState());
  }

  async function handleIkSquareStep() {
    await stepIkSquareTest();
    setState(await fetchState());
  }

  if (!state) {
    return (
      <div className="app-shell">
        <header className="hero">
          <h1>Autonomous Chess Player</h1>
        </header>
        <section className="tile">
          <div className="empty-state">{error ?? "Loading command-centre state..."}</div>
        </section>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <h1>Autonomous Chess Player</h1>
        <nav className="top-pill-nav" aria-label="Primary sections">
          <button type="button" className="top-pill-link" onClick={() => setSettingsOpen((value) => !value)}>
            Settings
          </button>
          <button type="button" className="top-pill-link" onClick={() => setLogsOpen((value) => !value)}>
            Logs
          </button>
        </nav>
      </header>

      <div
        className={[
          "page-frame",
          settingsOpen ? "left-open" : "",
          logsOpen ? "right-open" : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <aside className={`side-panel side-panel-left ${settingsOpen ? "open" : ""}`} aria-hidden={!settingsOpen}>
          <div className="side-panel-head">
            <h2>Settings</h2>
            <button type="button" className="side-panel-close" onClick={() => setSettingsOpen(false)}>
              ×
            </button>
          </div>
          <div className="side-panel-body">
            <GeneralSettingsTile
              settings={state.settings}
              onSetActiveClassifier={handleSetActiveClassifier}
              embedded
            />
          </div>
        </aside>

        <main className="dashboard-grid">
          <VisionTile
            vision={state.vision}
            game={state.game}
            logs={state.logs}
            cameraSource={state.system.camera_source}
            availableCameras={state.system.available_cameras}
            workflowMode={workflowMode}
            onCameraSourceChange={handleCameraSourceChange}
            onBoardProcessingAction={handleBoardProcessingAction}
            onVisionCornerSelect={handleVisionCornerSelect}
            onWorkflowModeChange={handleWorkflowModeChange}
          />
          <KinematicsTile
            joints={state.joints}
            ikTest={state.ik_test}
            onJointChange={handleJointChange}
            onIkSquareTest={handleIkSquareTest}
            onIkSquareStep={handleIkSquareStep}
          />
          <TrainingPanel
            training={state.training}
            active={workflowMode === "label"}
            onCaptureSnapshot={handleCaptureTrainingSnapshot}
            onSetDatasetPath={handleSetTrainingDatasetPath}
            onSetLabelMode={handleSetTrainingLabelMode}
            onSelectSnapshot={handleSelectTrainingSnapshot}
            onAnnotateSquare={handleAnnotateTrainingSquare}
            onResetLabels={handleResetTrainingLabels}
            onCompleteSnapshot={handleCompleteTrainingSnapshot}
          />
          <ModelTrainingTile training={state.training} onStartTraining={handleStartModelTraining} />
        </main>

        <aside className={`side-panel side-panel-right ${logsOpen ? "open" : ""}`} aria-hidden={!logsOpen}>
          <div className="side-panel-head">
            <h2>Logs</h2>
            <button type="button" className="side-panel-close" onClick={() => setLogsOpen(false)}>
              ×
            </button>
          </div>
          <div className="side-panel-body">
            <LogsTile logs={state.logs} embedded />
          </div>
        </aside>
      </div>
    </div>
  );
}
