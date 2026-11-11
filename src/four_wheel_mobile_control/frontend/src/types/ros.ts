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
  active_authority?: string;
  estop_active: boolean;
  speed_limit: number;
  speed_limit_pct: number;
  watchdog_tripped: boolean;
  heartbeat_alive?: boolean;
  valid_modes: string[];
  timestamp: number;
}

export interface OdometryData {
  x: number;
  y: number;
  yaw: number;
  linearVelocity: number;
  linearVelocityY: number;
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
  rateHz: number;
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
  goals_failed?: number;
  total_distance_m?: number;
}

export interface ImuData {
  rollDeg: number;
  pitchDeg: number;
  yawDeg: number;
  ax: number;
  ay: number;
  az: number;
  gx: number;
  gy: number;
  gz: number;
  rateHz: number;
  lastUpdated: number;
}

export interface JointSteerAngles {
  flDeg: number;
  frDeg: number;
  rlDeg: number;
  rrDeg: number;
  lastUpdated: number;
}

export interface ReadinessComponent {
  required: boolean;
  ready: boolean;
  healthy: boolean;
  detail: string;
}

export interface ReadinessStatus {
  system_state: 'STARTING' | 'READY' | 'DEGRADED' | 'FAILED' | 'STOPPING';
  timestamp_wall: number;
  timestamp_ros: number;
  uptime_sec: number;
  components: Record<string, ReadinessComponent>;
}

export interface ClockStatus {
  simTimeSec: number;
  active: boolean;
  rateHz: number;
  lastUpdated: number;
}

export interface SystemConfig {
  host: string;
  rosbridge_port: number;
  web_video_port: number;
  camera_topic: string;
  lidar_topic: string;
}

export type Handedness = 'right' | 'left';

export type KeyboardControlState =
  | 'ENABLED'
  | 'DISABLED'
  | 'MANUAL AUTHORITY REQUIRED'
  | 'DISCONNECTED'
  | 'WINDOW UNFOCUSED';

export interface ActiveKeysState {
  w: boolean;
  a: boolean;
  s: boolean;
  d: boolean;
  q: boolean;
  e: boolean;
  space: boolean;
}

export interface LogEntry {
  id: number;
  time: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
}
