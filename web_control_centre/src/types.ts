export type SystemState = {
  mode: string;
  setup_name: string;
  robot_name: string;
  serial_port: string;
  camera_source: string;
  available_cameras: string[];
  last_action: string;
};

export type VisionState = {
  camera_connected: boolean;
  corners_selected: number;
  grid_locked: boolean;
  corner_selection_active: boolean;
  board_initialized: boolean;
  next_corner_label: string;
  next_corner_hint: string;
  stream_url: string;
  board_stream_url: string;
};

export type GameState = {
  side_to_move: string;
  detected_move: string;
  suggested_move: string;
  fen: string;
  observed_board: string[][];
  observed_board_initialized: boolean;
  session_active: boolean;
};

export type RobotState = {
  executing: boolean;
  gripper_state: string;
  control_target: string;
  hardware_available: boolean;
  hardware_status: string;
};

export type TrainingState = {
  snapshot_count: number;
  active_snapshot_index: number;
  label_mode: "white" | "black" | "empty";
  revision: number;
  saved_snapshot_count: number;
  active_snapshot_url: string;
  dataset_path: string;
  job_status: string;
  job_message: string;
  job_output_model: string;
};

export type SettingsState = {
  active_classifier_path: string;
  available_classifiers: string[];
};

export type IkTestState = {
  square: string;
  status: string;
  message: string;
  active_joint: string | null;
  step_index: number;
  step_total: number;
  pose: {
    x_mm: number;
    y_mm: number;
    z_mm: number;
  } | null;
  joint_deg: Record<string, number> | null;
};

export type BoardState = {
  origin_x_mm: number;
  origin_y_mm: number;
  square_size_mm: number;
};

export type JointState = {
  label: string;
  minimum: number;
  maximum: number;
  current: number;
  target: number;
  velocity: number;
  minimum_deg?: number;
  maximum_deg?: number;
  target_deg?: number;
  current_deg?: number;
  control_mode?: string;
};

export type LogEntry = {
  level: string;
  message: string;
};

export type CommandCentreState = {
  system: SystemState;
  vision: VisionState;
  game: GameState;
  robot: RobotState;
  training: TrainingState;
  settings: SettingsState;
  ik_test: IkTestState;
  board: BoardState;
  joints: Record<string, JointState>;
  logs: LogEntry[];
};
