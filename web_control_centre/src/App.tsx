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
  startPlayMode,
  startModelTraining,
  setTrainingDatasetPath,
  setTrainingLabelMode,
  submitVisionCorner,
} from "./api";
import { GeneralSettingsTile } from "./components/GeneralSettingsTile";
import { JointControlTile } from "./components/JointControlTile";
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

  if (!state) {
    return (
      <div className="app-shell">
        <header className="hero">
          <h1>Robot Chess Player</h1>
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
        <h1>Robot Chess Player</h1>
      </header>

      <main className="dashboard-grid">
        <div className="main-column">
          <VisionTile
            vision={state.vision}
            game={state.game}
            cameraSource={state.system.camera_source}
            availableCameras={state.system.available_cameras}
            workflowMode={workflowMode}
            onCameraSourceChange={handleCameraSourceChange}
            onBoardProcessingAction={handleBoardProcessingAction}
            onVisionCornerSelect={handleVisionCornerSelect}
            onWorkflowModeChange={handleWorkflowModeChange}
          />
          <KinematicsTile />
        </div>
        <div className="side-column">
          <GeneralSettingsTile settings={state.settings} onSetActiveClassifier={handleSetActiveClassifier} />
          <LogsTile logs={state.logs} />
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
          <JointControlTile joints={state.joints} onJointChange={handleJointChange} />
        </div>
      </main>
    </div>
  );
}
