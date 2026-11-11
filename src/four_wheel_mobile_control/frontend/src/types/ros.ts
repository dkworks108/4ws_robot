export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export type OperatingMode = 'MANUAL' | 'AUTONOMOUS_NAV' | 'AUTONOMOUS_EXPLORE' | 'ESTOP';

export type SteeringMode = 
  | 'front_steer'       // Mode A: Front-Wheel Ackermann
  | 'four_wheel_steer'  // Mode B: 4WS Counter-Phase
  | 'crab'              // Mode C: Crab Steering
  | 'generalized'       // Mode D: Generalized Swerve
  | 'in_place_spin';    // Mode E: Rotation-In-Place

export interface ArbiterStatus {
  operating_mode: OperatingMode;
  estop_active: boolean;
  speed_limit: number;
  speed_limit_pct: number;
  watchdog_tripped: boolean;
  valid_modes: string[];
  timestamp: number;
}

export interface OdometryData {
  x: number;
  y: number;
  yaw: number;
  linearVelocity: number;
  angularVelocity: number;
  lastUpdated: number;
}

export interface LaserScanData {
  angle_min: number;
  angle_max: number;
  angle_increment: number;
  range_min: number;
  range_max: number;
  ranges: number[];
  lastUpdated: number;
}

export interface OccupancyGridData {
  width: number;
  height: number;
  resolution: number;
  originX: number;
  originY: number;
  data: number[];
  lastUpdated: number;
}

export interface ExplorationCoverage {
  explored_pct: number;
  known_area_m2: number;
  total_area_m2: number;
  state: string;
  goals_completed: number;
}

export interface SystemConfig {
  host: string;
  rosbridge_port: number;
  web_video_port: number;
  camera_topic: string;
  lidar_topic: string;
}

