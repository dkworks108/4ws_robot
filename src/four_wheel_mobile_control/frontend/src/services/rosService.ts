import ROSLIB from 'roslib';
import {
  ConnectionStatus,
  OperatingMode,
  SteeringMode,
  ArbiterStatus,
  OdometryData,
  LaserScanData,
  OccupancyGridData,
  ExplorationCoverage,
  ImuData,
  JointSteerAngles,
  ReadinessStatus,
  ClockStatus,
  SystemConfig,
  LogEntry,
} from '../types/ros';

class RosService {
  private ros: ROSLIB.Ros | null = null;
  private statusListeners: Array<(status: ConnectionStatus) => void> = [];
  private currentStatus: ConnectionStatus = 'disconnected';
  private reconnectTimer: any = null;
  private heartbeatTimer: any = null;
  private latencyTimer: any = null;

  // Topics
  private cmdVelPub: ROSLIB.Topic | null = null;
  private heartbeatPub: ROSLIB.Topic | null = null;
  private setModePub: ROSLIB.Topic | null = null;
  private estopPub: ROSLIB.Topic | null = null;
  private speedLimitPub: ROSLIB.Topic | null = null;
  private steeringModePub: ROSLIB.Topic | null = null;
  private goalPosePub: ROSLIB.Topic | null = null;

  // Active Data Callbacks
  private arbiterStatusCallbacks: Array<(data: ArbiterStatus) => void> = [];
  private odomCallbacks: Array<(data: OdometryData) => void> = [];
  private scanCallbacks: Array<(data: LaserScanData) => void> = [];
  private mapCallbacks: Array<(data: OccupancyGridData) => void> = [];
  private planCallbacks: Array<(poses: Array<{ x: number; y: number }>) => void> = [];
  private steeringModeCallbacks: Array<(mode: SteeringMode) => void> = [];
  private explorationCoverageCallbacks: Array<(cov: ExplorationCoverage) => void> = [];
  private explorationStatusCallbacks: Array<(status: string) => void> = [];
  private imuCallbacks: Array<(imu: ImuData) => void> = [];
  private jointSteerCallbacks: Array<(joints: JointSteerAngles) => void> = [];
  private readinessCallbacks: Array<(r: ReadinessStatus) => void> = [];
  private clockCallbacks: Array<(c: ClockStatus) => void> = [];
  private latencyCallbacks: Array<(ms: number | null) => void> = [];
  private logCallbacks: Array<(entry: LogEntry) => void> = [];

  private scanTimestamps: number[] = [];
  private imuTimestamps: number[] = [];
  private clockTimestamps: number[] = [];
  private logCounter = 0;

  public config: SystemConfig = {
    host: window.location.hostname || 'localhost',
    rosbridge_port: 9090,
    web_video_port: 8080,
    camera_topic: '/camera/image_raw',
    lidar_topic: '/scan',
  };

  constructor() {
    this.fetchServerConfig();
  }

  private emitLog(level: 'INFO' | 'WARN' | 'ERROR', message: string) {
    const now = new Date();
    const time = now.toTimeString().slice(0, 8);
    const entry: LogEntry = { id: ++this.logCounter, time, level, message };
    this.logCallbacks.forEach(cb => cb(entry));
  }

  public async fetchServerConfig() {
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        if (data.rosbridge_port) this.config.rosbridge_port = data.rosbridge_port;
        if (data.web_video_port) this.config.web_video_port = data.web_video_port;
        if (data.primary_ip && !['localhost', '127.0.0.1'].includes(window.location.hostname)) {
          this.config.host = window.location.hostname;
        }
      }
    } catch {
      // Fallback to defaults
    }
  }

  public getStatus(): ConnectionStatus {
    return this.currentStatus;
  }

  public connect(host?: string, port?: number) {
    if (host) this.config.host = host;
    if (port) this.config.rosbridge_port = port;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ros) {
      this.sendVelocity(0, 0, 0);
      this.stopHeartbeat();
      this.stopLatencyMonitor();
      const oldRos = this.ros;
      this.ros = null;
      try {
        oldRos.close();
      } catch {
        // ignore
      }
    }

    this.setStatus('connecting');
    const wsUrl = `ws://${this.config.host}:${this.config.rosbridge_port}`;
    this.emitLog('INFO', `Connecting to rosbridge at ${wsUrl}...`);

    try {
      const rosInstance = new ROSLIB.Ros({ url: wsUrl });
      this.ros = rosInstance;

      rosInstance.on('connection', () => {
        if (this.ros !== rosInstance) return;
        this.setStatus('connected');
        this.emitLog('INFO', `Connected to rosbridge (${wsUrl})`);
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        this.setupPublishersAndSubscribers();
        this.startHeartbeat();
        this.startLatencyMonitor();
      });

      rosInstance.on('error', () => {
        if (this.ros !== rosInstance) return;
        this.setStatus('error');
        this.emitLog('ERROR', `WebSocket error on ${wsUrl}`);
        this.latencyCallbacks.forEach(cb => cb(null));
        this.scheduleReconnect();
      });

      rosInstance.on('close', () => {
        if (this.ros !== rosInstance) return;
        this.setStatus('disconnected');
        this.emitLog('WARN', 'WebSocket disconnected from rosbridge');
        this.stopHeartbeat();
        this.stopLatencyMonitor();
        this.latencyCallbacks.forEach(cb => cb(null));
        this.scheduleReconnect();
      });
    } catch {
      this.setStatus('error');
      this.scheduleReconnect();
    }
  }

  public disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.sendVelocity(0, 0, 0);
    this.stopHeartbeat();
    this.stopLatencyMonitor();
    if (this.ros) {
      this.ros.close();
      this.ros = null;
    }
    this.setStatus('disconnected');
  }

  private setStatus(status: ConnectionStatus) {
    this.currentStatus = status;
    this.statusListeners.forEach(cb => cb(status));
  }

  public onStatusChange(callback: (status: ConnectionStatus) => void) {
    this.statusListeners.push(callback);
    callback(this.currentStatus);
    return () => {
      this.statusListeners = this.statusListeners.filter(cb => cb !== callback);
    };
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      if (this.currentStatus !== 'connected') {
        this.connect();
      }
    }, 3000);
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.heartbeatPub && this.currentStatus === 'connected') {
        this.heartbeatPub.publish({});
      }
    }, 200); // 5 Hz heartbeat
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private startLatencyMonitor() {
    this.stopLatencyMonitor();
    const probe = () => {
      if (!this.ros || this.currentStatus !== 'connected') return;
      const t0 = performance.now();
      const srv = new ROSLIB.Service({
        ros: this.ros,
        name: '/rosapi/get_time',
        serviceType: 'rosapi_msgs/srv/GetTime',
      });
      srv.callService(
        new ROSLIB.ServiceRequest({}),
        () => {
          const rtt = Math.max(1, Math.round(performance.now() - t0));
          this.latencyCallbacks.forEach(cb => cb(rtt));
        },
        () => {
          // Ignore if rosapi is unavailable
        }
      );
    };
    probe();
    this.latencyTimer = setInterval(probe, 2500);
  }

  private stopLatencyMonitor() {
    if (this.latencyTimer) {
      clearInterval(this.latencyTimer);
      this.latencyTimer = null;
    }
  }

  private computeHz(buffer: number[], now: number): number {
    buffer.push(now);
    const cutoff = now - 2000;
    while (buffer.length > 0 && buffer[0] < cutoff) {
      buffer.shift();
    }
    if (buffer.length < 2) return 0;
    const spanSec = (buffer[buffer.length - 1] - buffer[0]) / 1000;
    return spanSec > 0 ? Math.round((buffer.length - 1) / spanSec) : 0;
  }

  private setupPublishersAndSubscribers() {
    if (!this.ros) return;

    // 1. Publishers
    this.cmdVelPub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/cmd_vel',
      messageType: 'geometry_msgs/msg/Twist',
    });

    this.heartbeatPub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/heartbeat',
      messageType: 'std_msgs/msg/Empty',
    });

    this.setModePub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/set_mode',
      messageType: 'std_msgs/msg/String',
    });

    this.estopPub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/estop',
      messageType: 'std_msgs/msg/Bool',
    });

    this.speedLimitPub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/set_speed_limit',
      messageType: 'std_msgs/msg/Float32',
    });

    this.steeringModePub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/four_wheel/set_mode',
      messageType: 'std_msgs/msg/String',
    });

    // 2. Nav2 Goal Pose Publisher (ROS 2 standard /goal_pose)
    this.goalPosePub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/goal_pose',
      messageType: 'geometry_msgs/msg/PoseStamped',
    });

    // 3. Subscriptions
    const subArbiter = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/arbiter_status',
      messageType: 'std_msgs/msg/String',
      queue_length: 1,
    });
    subArbiter.subscribe((msg: any) => {
      try {
        const data = JSON.parse(msg.data);
        this.arbiterStatusCallbacks.forEach(cb => cb(data));
      } catch {
        // ignore malformed json
      }
    });

    const subOdom = new ROSLIB.Topic({
      ros: this.ros,
      name: '/odom',
      messageType: 'nav_msgs/msg/Odometry',
      throttle_rate: 150,
      queue_length: 1,
    });
    subOdom.subscribe((msg: any) => {
      const q = msg.pose.pose.orientation;
      const siny_cosp = 2 * (q.w * q.z + q.x * q.y);
      const cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z);
      const yaw = Math.atan2(siny_cosp, cosy_cosp);

      const odomData: OdometryData = {
        x: msg.pose.pose.position.x,
        y: msg.pose.pose.position.y,
        yaw,
        linearVelocity: msg.twist.twist.linear.x,
        linearVelocityY: msg.twist.twist.linear.y || 0,
        angularVelocity: msg.twist.twist.angular.z,
        lastUpdated: Date.now(),
      };
      this.odomCallbacks.forEach(cb => cb(odomData));
    });

    const subScan = new ROSLIB.Topic({
      ros: this.ros,
      name: '/scan',
      messageType: 'sensor_msgs/msg/LaserScan',
      throttle_rate: 200,
      queue_length: 1,
    });
    subScan.subscribe((msg: any) => {
      const now = Date.now();
      const scanData: LaserScanData = {
        angle_min: msg.angle_min,
        angle_max: msg.angle_max,
        angle_increment: msg.angle_increment,
        range_min: msg.range_min,
        range_max: msg.range_max,
        ranges: msg.ranges,
        rateHz: this.computeHz(this.scanTimestamps, now),
        lastUpdated: now,
      };
      this.scanCallbacks.forEach(cb => cb(scanData));
    });

    const subMap = new ROSLIB.Topic({
      ros: this.ros,
      name: '/map',
      messageType: 'nav_msgs/msg/OccupancyGrid',
      throttle_rate: 4000,
      queue_length: 1,
    });
    subMap.subscribe((msg: any) => {
      const mapData: OccupancyGridData = {
        width: msg.info.width,
        height: msg.info.height,
        resolution: msg.info.resolution,
        originX: msg.info.origin.position.x,
        originY: msg.info.origin.position.y,
        data: msg.data,
        lastUpdated: Date.now(),
      };
      this.mapCallbacks.forEach(cb => cb(mapData));
    });

    const subPlan = new ROSLIB.Topic({
      ros: this.ros,
      name: '/plan',
      messageType: 'nav_msgs/msg/Path',
    });
    subPlan.subscribe((msg: any) => {
      const poses = (msg.poses || []).map((p: any) => ({
        x: p.pose.position.x,
        y: p.pose.position.y,
      }));
      this.planCallbacks.forEach(cb => cb(poses));
    });

    const subSteerMode = new ROSLIB.Topic({
      ros: this.ros,
      name: '/four_wheel/current_mode',
      messageType: 'std_msgs/msg/String',
    });
    subSteerMode.subscribe((msg: any) => {
      const mode = msg.data.trim() as SteeringMode;
      this.steeringModeCallbacks.forEach(cb => cb(mode));
    });

    const subCoverage = new ROSLIB.Topic({
      ros: this.ros,
      name: '/exploration/coverage',
      messageType: 'std_msgs/msg/String',
    });
    subCoverage.subscribe((msg: any) => {
      try {
        const data = JSON.parse(msg.data);
        this.explorationCoverageCallbacks.forEach(cb => cb(data));
      } catch {
        // ignore
      }
    });

    const subExplStatus = new ROSLIB.Topic({
      ros: this.ros,
      name: '/exploration/status',
      messageType: 'std_msgs/msg/String',
    });
    subExplStatus.subscribe((msg: any) => {
      this.explorationStatusCallbacks.forEach(cb => cb(msg.data));
    });

    const subImu = new ROSLIB.Topic({
      ros: this.ros,
      name: '/imu/data',
      messageType: 'sensor_msgs/msg/Imu',
      throttle_rate: 200,
      queue_length: 1,
    });
    subImu.subscribe((msg: any) => {
      const now = Date.now();
      const q = msg.orientation;
      const sinr_cosp = 2 * (q.w * q.x + q.y * q.z);
      const cosr_cosp = 1 - 2 * (q.x * q.x + q.y * q.y);
      const roll = Math.atan2(sinr_cosp, cosr_cosp);
      const sinp = Math.max(-1, Math.min(1, 2 * (q.w * q.y - q.z * q.x)));
      const pitch = Math.asin(sinp);
      const siny_cosp = 2 * (q.w * q.z + q.x * q.y);
      const cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z);
      const yaw = Math.atan2(siny_cosp, cosy_cosp);

      const imuData: ImuData = {
        rollDeg: (roll * 180) / Math.PI,
        pitchDeg: (pitch * 180) / Math.PI,
        yawDeg: (yaw * 180) / Math.PI,
        ax: msg.linear_acceleration?.x || 0,
        ay: msg.linear_acceleration?.y || 0,
        az: msg.linear_acceleration?.z || 0,
        gx: msg.angular_velocity?.x || 0,
        gy: msg.angular_velocity?.y || 0,
        gz: msg.angular_velocity?.z || 0,
        rateHz: this.computeHz(this.imuTimestamps, now),
        lastUpdated: now,
      };
      this.imuCallbacks.forEach(cb => cb(imuData));
    });

    const subJoints = new ROSLIB.Topic({
      ros: this.ros,
      name: '/joint_states',
      messageType: 'sensor_msgs/msg/JointState',
      throttle_rate: 150,
      queue_length: 1,
    });
    subJoints.subscribe((msg: any) => {
      const names: string[] = msg.name || [];
      const positions: number[] = msg.position || [];
      const toDeg = (rad: number) => (rad * 180) / Math.PI;
      const idx = (n: string) => names.indexOf(n);
      const flIdx = idx('fl_steering_joint');
      const frIdx = idx('fr_steering_joint');
      const rlIdx = idx('rl_steering_joint');
      const rrIdx = idx('rr_steering_joint');
      if (flIdx >= 0 && frIdx >= 0 && rlIdx >= 0 && rrIdx >= 0) {
        const angles: JointSteerAngles = {
          flDeg: toDeg(positions[flIdx] || 0),
          frDeg: toDeg(positions[frIdx] || 0),
          rlDeg: toDeg(positions[rlIdx] || 0),
          rrDeg: toDeg(positions[rrIdx] || 0),
          lastUpdated: Date.now(),
        };
        this.jointSteerCallbacks.forEach(cb => cb(angles));
      }
    });

    const subReadiness = new ROSLIB.Topic({
      ros: this.ros,
      name: '/system/readiness_status',
      messageType: 'std_msgs/msg/String',
    });
    subReadiness.subscribe((msg: any) => {
      try {
        const parsed = JSON.parse(msg.data) as ReadinessStatus;
        this.readinessCallbacks.forEach(cb => cb(parsed));
      } catch {
        // ignore
      }
    });

    const subClock = new ROSLIB.Topic({
      ros: this.ros,
      name: '/clock',
      messageType: 'rosgraph_msgs/msg/Clock',
      throttle_rate: 500,
      queue_length: 1,
    });
    subClock.subscribe((msg: any) => {
      const now = Date.now();
      const sec = (msg.clock?.sec || 0) + (msg.clock?.nanosec || 0) * 1e-9;
      const status: ClockStatus = {
        simTimeSec: sec,
        active: true,
        rateHz: this.computeHz(this.clockTimestamps, now),
        lastUpdated: now,
      };
      this.clockCallbacks.forEach(cb => cb(status));
    });
  }

  // Control APIs
  public sendVelocity(vx: number, vy: number, wz: number) {
    if (this.cmdVelPub && this.currentStatus === 'connected') {
      const twist = {
        linear: { x: vx, y: vy, z: 0.0 },
        angular: { x: 0.0, y: 0.0, z: wz },
      };
      this.cmdVelPub.publish(twist);
    }
  }

  public setOperatingMode(mode: OperatingMode) {
    if (this.setModePub && this.currentStatus === 'connected') {
      this.setModePub.publish({ data: mode });
      this.emitLog('INFO', `Requested operating authority: ${mode}`);
    }
  }

  public setSteeringMode(mode: SteeringMode) {
    if (this.steeringModePub && this.currentStatus === 'connected') {
      this.steeringModePub.publish({ data: mode });
      this.emitLog('INFO', `Requested steering mode: ${mode}`);
    }
  }

  public setSpeedLimit(limit: number) {
    if (this.speedLimitPub && this.currentStatus === 'connected') {
      this.speedLimitPub.publish({ data: limit });
      this.emitLog('INFO', `Speed limit set to ${Math.round(limit * 100)}%`);
    }
  }

  public triggerEmergencyStop() {
    this.emitLog('ERROR', 'EMERGENCY STOP TRIGGERED BY OPERATOR');
    if (this.estopPub && this.currentStatus === 'connected') {
      this.estopPub.publish({ data: true });
    } else if (this.ros && this.currentStatus === 'connected') {
      const srv = new ROSLIB.Service({
        ros: this.ros,
        name: '/mobile/trigger_estop',
        serviceType: 'std_srvs/srv/Trigger',
      });
      srv.callService(new ROSLIB.ServiceRequest({}), () => {});
    }
  }

  public resetEmergencyStop() {
    this.emitLog('WARN', 'Emergency Stop reset requested');
    if (this.estopPub && this.currentStatus === 'connected') {
      this.estopPub.publish({ data: false });
    } else if (this.ros && this.currentStatus === 'connected') {
      const srv = new ROSLIB.Service({
        ros: this.ros,
        name: '/mobile/reset_estop',
        serviceType: 'std_srvs/srv/Trigger',
      });
      srv.callService(new ROSLIB.ServiceRequest({}), () => {});
    }
  }

  // Exploration Services
  public startExploration() {
    if (!this.ros) return;
    this.emitLog('INFO', 'Starting autonomous frontier exploration');
    const srv = new ROSLIB.Service({
      ros: this.ros,
      name: '/exploration/start',
      serviceType: 'std_srvs/srv/Trigger',
    });
    srv.callService(new ROSLIB.ServiceRequest({}), () => {});
    this.setOperatingMode('AUTONOMOUS_EXPLORE');
  }

  public pauseExploration() {
    if (!this.ros) return;
    this.emitLog('WARN', 'Pausing frontier exploration');
    const srv = new ROSLIB.Service({
      ros: this.ros,
      name: '/exploration/pause',
      serviceType: 'std_srvs/srv/Trigger',
    });
    srv.callService(new ROSLIB.ServiceRequest({}), () => {});
  }

  public resumeExploration() {
    if (!this.ros) return;
    this.emitLog('INFO', 'Resuming frontier exploration');
    const srv = new ROSLIB.Service({
      ros: this.ros,
      name: '/exploration/resume',
      serviceType: 'std_srvs/srv/Trigger',
    });
    srv.callService(new ROSLIB.ServiceRequest({}), () => {});
    this.setOperatingMode('AUTONOMOUS_EXPLORE');
  }

  public stopExploration() {
    if (!this.ros) return;
    this.emitLog('WARN', 'Stopping frontier exploration');
    const srv = new ROSLIB.Service({
      ros: this.ros,
      name: '/exploration/stop',
      serviceType: 'std_srvs/srv/Trigger',
    });
    srv.callService(new ROSLIB.ServiceRequest({}), () => {});
    this.setOperatingMode('MANUAL');
  }

  // Nav2 Goal Dispatcher
  public sendNavigationGoal(x: number, y: number, yaw: number = 0.0) {
    if (!this.goalPosePub) return;

    this.setOperatingMode('AUTONOMOUS_NAV');
    this.emitLog('INFO', `Dispatching Nav2 goal: (${x.toFixed(2)}, ${y.toFixed(2)})`);

    const halfYaw = yaw * 0.5;
    const goalPose = new ROSLIB.Message({
      header: {
        stamp: { sec: 0, nanosec: 0 },
        frame_id: 'map',
      },
      pose: {
        position: { x, y, z: 0.0 },
        orientation: {
          x: 0.0,
          y: 0.0,
          z: Math.sin(halfYaw),
          w: Math.cos(halfYaw),
        },
      },
    });

    this.goalPosePub.publish(goalPose);
  }

  public cancelNavigationGoal() {
    if (!this.ros || this.currentStatus !== 'connected') return;
    this.emitLog('WARN', 'Cancelling active Nav2 navigation goal');
    const cancelClient = new ROSLIB.Service({
      ros: this.ros,
      name: '/navigate_to_pose/_action/cancel_goal',
      serviceType: 'action_msgs/srv/CancelGoal',
    });
    const request = new ROSLIB.ServiceRequest({});
    cancelClient.callService(request, () => {
      this.emitLog('INFO', 'Nav2 goal cancel requested');
    });
  }

  // Subscription registers
  public onArbiterStatus(cb: (data: ArbiterStatus) => void) {
    this.arbiterStatusCallbacks.push(cb);
    return () => {
      this.arbiterStatusCallbacks = this.arbiterStatusCallbacks.filter(c => c !== cb);
    };
  }

  public onOdometry(cb: (data: OdometryData) => void) {
    this.odomCallbacks.push(cb);
    return () => {
      this.odomCallbacks = this.odomCallbacks.filter(c => c !== cb);
    };
  }

  public onLaserScan(cb: (data: LaserScanData) => void) {
    this.scanCallbacks.push(cb);
    return () => {
      this.scanCallbacks = this.scanCallbacks.filter(c => c !== cb);
    };
  }

  public onMap(cb: (data: OccupancyGridData) => void) {
    this.mapCallbacks.push(cb);
    return () => {
      this.mapCallbacks = this.mapCallbacks.filter(c => c !== cb);
    };
  }

  public onPlan(cb: (poses: Array<{ x: number; y: number }>) => void) {
    this.planCallbacks.push(cb);
    return () => {
      this.planCallbacks = this.planCallbacks.filter(c => c !== cb);
    };
  }

  public onSteeringMode(cb: (mode: SteeringMode) => void) {
    this.steeringModeCallbacks.push(cb);
    return () => {
      this.steeringModeCallbacks = this.steeringModeCallbacks.filter(c => c !== cb);
    };
  }

  public onExplorationCoverage(cb: (cov: ExplorationCoverage) => void) {
    this.explorationCoverageCallbacks.push(cb);
    return () => {
      this.explorationCoverageCallbacks = this.explorationCoverageCallbacks.filter(c => c !== cb);
    };
  }

  public onExplorationStatus(cb: (status: string) => void) {
    this.explorationStatusCallbacks.push(cb);
    return () => {
      this.explorationStatusCallbacks = this.explorationStatusCallbacks.filter(c => c !== cb);
    };
  }

  public onImu(cb: (imu: ImuData) => void) {
    this.imuCallbacks.push(cb);
    return () => {
      this.imuCallbacks = this.imuCallbacks.filter(c => c !== cb);
    };
  }

  public onJointSteer(cb: (joints: JointSteerAngles) => void) {
    this.jointSteerCallbacks.push(cb);
    return () => {
      this.jointSteerCallbacks = this.jointSteerCallbacks.filter(c => c !== cb);
    };
  }

  public onReadiness(cb: (r: ReadinessStatus) => void) {
    this.readinessCallbacks.push(cb);
    return () => {
      this.readinessCallbacks = this.readinessCallbacks.filter(c => c !== cb);
    };
  }

  public onClock(cb: (c: ClockStatus) => void) {
    this.clockCallbacks.push(cb);
    return () => {
      this.clockCallbacks = this.clockCallbacks.filter(c => c !== cb);
    };
  }

  public onLatency(cb: (ms: number | null) => void) {
    this.latencyCallbacks.push(cb);
    return () => {
      this.latencyCallbacks = this.latencyCallbacks.filter(c => c !== cb);
    };
  }

  public onLog(cb: (entry: LogEntry) => void) {
    this.logCallbacks.push(cb);
    return () => {
      this.logCallbacks = this.logCallbacks.filter(c => c !== cb);
    };
  }
}

export const rosService = new RosService();
