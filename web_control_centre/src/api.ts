import type { CommandCentreState } from "./types";

export async function fetchState(): Promise<CommandCentreState> {
  const response = await fetch("/api/state");
  if (!response.ok) {
    throw new Error("Failed to load command-centre state");
  }
  return response.json();
}

export async function sendAction(action: string): Promise<void> {
  const response = await fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  if (!response.ok) {
    throw new Error(`Failed to send action '${action}'`);
  }
}

export async function setJointTarget(joint: string, value: number): Promise<void> {
  const response = await fetch("/api/joint-target", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ joint, value }),
  });
  if (!response.ok) {
    throw new Error(`Failed to update joint '${joint}'`);
  }
}

export async function setJointAngleTarget(joint: string, value: number): Promise<void> {
  const response = await fetch("/api/joint-angle-target", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ joint, value }),
  });
  if (!response.ok) {
    throw new Error(`Failed to update joint angle '${joint}'`);
  }
}

export async function setCameraSource(source: string): Promise<void> {
  const response = await fetch("/api/camera/select", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source }),
  });
  if (!response.ok) {
    throw new Error(`Failed to select camera '${source}'`);
  }
}

export async function submitVisionCorner(x: number, y: number): Promise<void> {
  const response = await fetch("/api/vision/corner", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ x, y }),
  });
  if (!response.ok) {
    throw new Error("Failed to submit selected corner");
  }
}

export async function captureTrainingSnapshot(): Promise<void> {
  const response = await fetch("/api/training/capture", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error("Failed to capture training snapshot");
  }
}

export async function setTrainingLabelMode(mode: "white" | "black" | "empty"): Promise<void> {
  const response = await fetch("/api/training/label-mode", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
  if (!response.ok) {
    throw new Error(`Failed to set training label mode '${mode}'`);
  }
}

export async function setTrainingDatasetPath(datasetPath: string): Promise<void> {
  const response = await fetch("/api/training/dataset-path", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_path: datasetPath }),
  });
  if (!response.ok) {
    throw new Error(`Failed to set labelling dataset path '${datasetPath}'`);
  }
}

export async function startModelTraining(datasetPath: string, modelName: string): Promise<void> {
  const response = await fetch("/api/training/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_path: datasetPath, model_name: modelName }),
  });
  if (!response.ok) {
    throw new Error("Failed to start model training");
  }
}

export async function setActiveTrainingSnapshot(index: number): Promise<void> {
  const response = await fetch("/api/training/snapshot", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ index }),
  });
  if (!response.ok) {
    throw new Error(`Failed to switch to training snapshot ${index + 1}`);
  }
}

export async function annotateTrainingSquare(x: number, y: number): Promise<void> {
  const response = await fetch("/api/training/square", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ x, y }),
  });
  if (!response.ok) {
    throw new Error("Failed to annotate training square");
  }
}

export async function resetTrainingLabels(): Promise<void> {
  const response = await fetch("/api/training/reset-labels", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error("Failed to reset training labels");
  }
}

export async function completeTrainingSnapshot(): Promise<void> {
  const response = await fetch("/api/training/complete-snapshot", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error("Failed to save training snapshot");
  }
}

export async function startPlayMode(): Promise<void> {
  const response = await fetch("/api/play/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error("Failed to start play mode");
  }
}

export async function setActiveClassifier(classifierPath: string): Promise<void> {
  const response = await fetch("/api/settings/active-classifier", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ classifier_path: classifierPath }),
  });
  if (!response.ok) {
    throw new Error(`Failed to set active classifier '${classifierPath}'`);
  }
}

export async function solveIkSquareTest(square: string): Promise<void> {
  const response = await fetch("/api/kinematics/square-test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ square }),
  });
  if (!response.ok) {
    throw new Error(`Failed to solve IK for square '${square}'`);
  }
}

export async function stepIkSquareTest(): Promise<void> {
  const response = await fetch("/api/kinematics/square-test/next", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error("Failed to advance IK joint step");
  }
}

export async function setRobotControlTarget(target: "virtual" | "hardware"): Promise<void> {
  const response = await fetch("/api/robot/control-target", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target }),
  });
  if (!response.ok) {
    throw new Error(`Failed to set control target '${target}'`);
  }
}

export async function moveRobotToHome(): Promise<void> {
  const response = await fetch("/api/robot/home", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error("Failed to move robot to home pose");
  }
}

export async function saveRobotHome(): Promise<void> {
  const response = await fetch("/api/robot/home/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error("Failed to save robot home pose");
  }
}
