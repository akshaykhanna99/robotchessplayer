export type Vec3Mm = {
  x_mm: number;
  y_mm: number;
  z_mm: number;
};

export type BaseFrameConfig = Vec3Mm & {
  yaw_deg: number;
};

export type BoardConfig = {
  origin_x_mm: number;
  origin_y_mm: number;
  origin_z_mm: number;
  yaw_deg: number;
  square_size_mm: number;
  board_size_x_mm: number;
  board_size_y_mm: number;
  thickness_mm: number;
  light_square_color: string;
  dark_square_color: string;
  border_color: string;
};

export type LinkConfig = {
  name: string;
  length_mm: number;
  radius_mm: number;
  color: string;
};

export type JointConfig = {
  axis: string;
  min_deg: number;
  max_deg: number;
  home_deg: number;
};

export type RobotConfig = {
  base_frame: BaseFrameConfig;
  base_geometry: {
    shape: string;
    radius_mm: number;
    height_mm: number;
    color: string;
  };
  links: LinkConfig[];
  joints: Record<string, JointConfig>;
};

export type ToolConfig = {
  type: string;
  mount_offset_mm: Vec3Mm;
  pickup_point_offset_mm: Vec3Mm;
  geometry: {
    shape: string;
    size_x_mm: number;
    size_y_mm: number;
    size_z_mm: number;
    color: string;
  };
};

export type PieceTypeConfig = {
  diameter_mm: number;
  height_mm: number;
  color: string;
};

export type PiecesConfig = {
  default_clearance_above_piece_mm: number;
  default_grasp_height_from_base_mm: number;
  types: Record<string, PieceTypeConfig>;
};

export type SceneBoxConfig = {
  x_mm: number;
  y_mm: number;
  z_mm: number;
  size_x_mm: number;
  size_y_mm: number;
  size_z_mm: number;
  color: string;
};

export type ObstacleConfig = SceneBoxConfig & {
  name: string;
  shape: string;
};

export type DigitalTwinConfig = {
  setup_name: string;
  units: string;
  world_frame: {
    name: string;
    origin_definition: string;
  };
  board: BoardConfig;
  robot: RobotConfig;
  tool: ToolConfig;
  pieces: PiecesConfig;
  scene: {
    table: SceneBoxConfig;
    capture_tray: SceneBoxConfig;
    obstacles: ObstacleConfig[];
  };
  rendering: {
    show_axes: boolean;
    show_square_labels: boolean;
    show_collision_geometry: boolean;
    background: string;
  };
};
