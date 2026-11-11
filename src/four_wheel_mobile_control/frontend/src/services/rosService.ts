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
  SystemConfig
} from '../types/ros';

class RosService {
  private ros: ROSLIB.Ros | null = null;
  private statusListeners: Array<(status: ConnectionStatus) => void> = [];
  private currentStatus: ConnectionStatus = 'disconnected';
  private reconnectTimer: any = null;
  private heartbeatTimer: any = null;

  // Topics
  private cmdVelPub: ROSLIB.Topic | null = null;
  private heartbeatPub: ROSLIB.Topic | null = null;
  private setModePub: ROSLIB.Topic | null = null;
  private estopPub: ROSLIB.Topic | null = null;
  private speedLimitPub: ROSLIB.Topic | null = null;
  private steeringModePub: ROSLIB.Topic | null = null;

  // Nav2 Action Client
  private navActionClient: ROSLIB.ActionClient | null = null;
  private currentNavGoal: ROSLIB.Goal | null = null;

  // Active Data Callbacks
  private arbiterStatusCallbacks: Array<(data: ArbiterStatus) => void> = [];
  private odomCallbacks: Array<(data: OdometryData) => void> = [];
  private scanCallbacks: Array<(data: LaserScanData) => void> = [];
  private mapCallbacks: Array<(data: OccupancyGridData) => void> = [];
  private planCallbacks: Array<(poses: Array<{x: number, y: number}>) => void> = [];
  private steeringModeCallbacks: Array<(mode: SteeringMode) => void> = [];
  private explorationCoverageCallbacks: Array<(cov: ExplorationCoverage) => void> = [];
  private explorationStatusCallbacks: Array<(status: string) => void> = [];

  public config: SystemConfig = {
    host: window.location.hostname || 'localhost',
    rosbridge_port: 9090,
    web_video_port: 8080,
    camera_topic: '/camera/image_raw',
    lidar_topic: '/scan'
  };

  constructor() {
    this.fetchServerConfig();
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

  public connect(host?: string, port?: number) {
    if (host) this.config.host = host;
    if (port) this.config.rosbridge_port = port;

    if (this.ros) {
      try {
        this.ros.close();
      } catch {}
    }

    this.setStatus('connecting');
    const wsUrl = `ws://${this.config.host}:${this.config.rosbridge_port}`;

    try {
      this.ros = new ROSLIB.Ros({ url: wsUrl });

      this.ros.on('connection', () => {
        this.setStatus('connected');
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        this.setupPublishersAndSubscribers();
        this.startHeartbeat();
      });

      this.ros.on('error', () => {
        this.setStatus('error');
        this.scheduleReconnect();
      });

      this.ros.on('close', () => {
        this.setStatus('disconnected');
        this.stopHeartbeat();
        this.scheduleReconnect();
      });
    } catch {
      this.setStatus('error');
      this.scheduleReconnect();
    }
  }

  public disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.stopHeartbeat();
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

  private setupPublishersAndSubscribers() {
    if (!this.ros) return;

    // 1. Publishers
    this.cmdVelPub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/cmd_vel',
      messageType: 'geometry_msgs/msg/Twist'
    });

    this.heartbeatPub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/heartbeat',
      messageType: 'std_msgs/msg/Empty'
    });

    this.setModePub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/set_mode',
      messageType: 'std_msgs/msg/String'
    });

    this.estopPub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/estop',
      messageType: 'std_msgs/msg/Bool'
    });

    this.speedLimitPub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/set_speed_limit',
      messageType: 'std_msgs/msg/Float32'
    });

    this.steeringModePub = new ROSLIB.Topic({
      ros: this.ros,
      name: '/four_wheel/set_mode',
      messageType: 'std_msgs/msg/String'
    });

    // 2. Action Client for Nav2 NavigateToPose
    this.navActionClient = new ROSLIB.ActionClient({
      ros: this.ros,
      serverName: 'navigate_to_pose',
      actionName: 'nav2_msgs/action/NavigateToPose'
    });

    // 3. Subscriptions
    const subArbiter = new ROSLIB.Topic({
      ros: this.ros,
      name: '/mobile/arbiter_status',
      messageType: 'std_msgs/msg/String'
    });
    subArbiter.subscribe((msg: any) => {
      try {
        const data = JSON.parse(msg.data);
        this.arbiterStatusCallbacks.forEach(cb => cb(data));
      } catch {}
    });

    const subOdom = new ROSLIB.Topic({
      ros: this.ros,
      name: '/odom',
      messageType: 'nav_msgs/msg/Odometry'
    });
    subOdom.subscribe((msg: any) => {
      const q = msg.pose.pose.orientation;
      // Convert quaternion to yaw
      const siny_cosp = 2 * (q.w * q.z + q.x * q.y);
      const cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z);
      const yaw = Math.atan2(siny_cosp, cosy_cosp);

      const odomData: OdometryData = {
        x: msg.pose.pose.position.x,
        y: msg.pose.pose.position.y,
        yaw: yaw,
        linearVelocity: msg.twist.twist.linear.x,
        angularVelocity: msg.twist.twist.angular.z,
        lastUpdated: Date.now()
      };
      this.odomCallbacks.forEach(cb => cb(odomData));
    });

    const subScan = new ROSLIB.Topic({
      ros: this.ros,
      name: '/scan',
      messageType: 'sensor_msgs/msg/LaserScan'
    });
    subScan.subscribe((msg: any) => {
      const scanData: LaserScanData = {
        angle_min: msg.angle_min,
        angle_max: msg.angle_max,
        angle_increment: msg.angle_increment,
        range_min: msg.range_min,
        range_max: msg.range_max,
        ranges: msg.ranges,
        lastUpdated: Date.now()
      };
      this.scanCallbacks.forEach(cb => cb(scanData));
    });

    const subMap = new ROSLIB.Topic({
      ros: this.ros,
      name: '/map',
      messageType: 'nav_msgs/msg/OccupancyGrid'
    });
    subMap.subscribe((msg: any) => {
      const mapData: OccupancyGridData = {
        width: msg.info.width,
        height: msg.info.height,
        resolution: msg.info.resolution,
        originX: msg.info.origin.position.x,
        originY: msg.info.origin.position.y,
        data: msg.data,
        lastUpdated: Date.now()
      };
      this.mapCallbacks.forEach(cb => cb(mapData));
    });

    const subPlan = new ROSLIB.Topic({
      ros: this.ros,
      name: '/plan',
      messageType: 'nav_msgs/msg/Path'
    });
    subPlan.subscribe((msg: any) => {
      const poses = msg.poses.map((p: any) => ({
        x: p.pose.position.x,
        y: p.pose.position.y
      }));
      this.planCallbacks.forEach(cb => cb(poses));
    });

    const subSteerMode = new ROSLIB.Topic({
      ros: this.ros,
      name: '/four_wheel/current_mode',
      messageType: 'std_msgs/msg/String'
    });
    subSteerMode.subscribe((msg: any) => {
      const mode = msg.data.trim() as SteeringMode;
      this.steeringModeCallbacks.forEach(cb => cb(mode));
    });

    const subCoverage = new ROSLIB.Topic({
      ros: this.ros,
      name: '/exploration/coverage',
      messageType: 'std_msgs/msg/String'
    });
    subCoverage.subscribe((msg: any) => {
      try {
        const data = JSON.parse(msg.data);
        this.explorationCoverageCallbacks.forEach(cb => cb(data));
      } catch {}
    });

    const subExplStatus = new ROSLIB.Topic({
      ros: this.ros,
      name: '/exploration/status',
      messageType: 'std_msgs/msg/String'
    });
    subExplStatus.subscribe((msg: any) => {
      this.explorationStatusCallbacks.forEach(cb => cb(msg.data));
    });
  }

  // Control APIs
  public sendVelocity(vx: number, vy: number, wz: number) {
    if (this.cmdVelPub && this.currentStatus === 'connected') {
      const twist = {
        linear: { x: vx, y: vy, z: 0.0 },
        angular: { x: 0.0, y: 0.0, z: wz }
      };
      this.cmdVelPub.publish(twist);
    }
  }

  public setOperatingMode(mode: OperatingMode) {
    if (this.setModePub && this.currentStatus === 'connected') {
      this.setModePub.publish({ data: mode });
    }
  }

  public setSteeringMode(mode: SteeringMode) {
    if (this.steeringModePub && this.currentStatus === 'connected') {
      this.steeringModePub.publish({ data: mode });
    }
  }

  public setSpeedLimit(limit: number) {
    if (this.speedLimitPub && this.currentStatus === 'connected') {
      this.speedLimitPub.publish({ data: limit });
    }
  }

  public triggerEmergencyStop() {
    if (this.estopPub && this.currentStatus === 'connected') {
      this.estopPub.publish({ data: true });
    }
    // Also call service for redundancy
    if (this.ros) {
      const srv = new ROSLIB.Service({
        ros: this.ros,
        name: '/mobile/trigger_estop',
        serviceType: 'std_srvs/srv/Trigger'
      });
      srv.callService(new ROSLIB.ServiceRequest({}), () => {});
    }
  }

  public resetEmergencyStop() {
    if (this.estopPub && this.currentStatus === 'connected') {
      this.estopPub.publish({ data: false });
    }
    if (this.ros) {
      const srv = new ROSLIB.Service({
        ros: this.ros,
        name: '/mobile/reset_estop',
        serviceType: 'std_srvs/srv/Trigger'
      });
      srv.callService(new ROSLIB.ServiceRequest({}), () => {});
    }
  }

  // Exploration Services
  public startExploration() {
    if (!this.ros) return;
    const srv = new ROSLIB.Service({
      ros: this.ros,
      name: '/exploration/start',
      serviceType: 'std_srvs/srv/Trigger'
    });
    srv.callService(new ROSLIB.ServiceRequest({}), () => {});
    this.setOperatingMode('AUTONOMOUS_EXPLORE');
  }

  public pauseExploration() {
    if (!this.ros) return;
    const srv = new ROSLIB.Service({
      ros: this.ros,
      name: '/exploration/pause',
      serviceType: 'std_srvs/srv/Trigger'
    });
    srv.callService(new ROSLIB.ServiceRequest({}), () => {});
  }

  public resumeExploration() {
    if (!this.ros) return;
    const srv = new ROSLIB.Service({
      ros: this.ros,
      name: '/exploration/resume',
      serviceType: 'std_srvs/srv/Trigger'
    });
    srv.callService(new ROSLIB.ServiceRequest({}), () => {});
    this.setOperatingMode('AUTONOMOUS_EXPLORE');
  }

  public stopExploration() {
    if (!this.ros) return;
    const srv = new ROSLIB.Service({
      ros: this.ros,
      name: '/exploration/stop',
      serviceType: 'std_srvs/srv/Trigger'
    });
    srv.callService(new ROSLIB.ServiceRequest({}), () => {});
    this.setOperatingMode('MANUAL');
  }

  // Nav2 Action Dispatcher
  public sendNavigationGoal(x: number, y: number, yaw: number = 0.0) {
    if (!this.navActionClient) return;

    this.setOperatingMode('AUTONOMOUS_NAV');

    const halfYaw = yaw * 0.5;
    const goalMessage = {
      pose: {
        header: {
          stamp: { sec: 0, nanosec: 0 },
          frame_id: 'map'
        },
        pose: {
          position: { x: x, y: y, z: 0.0 },
          orientation: {
            x: 0.0,
            y: 0.0,
            z: Math.sin(halfYaw),
            w: Math.cos(halfYaw)
          }
        }
      }
    };

    const goal = new ROSLIB.Goal({
      actionClient: this.navActionClient,
      goalMessage: goalMessage
    });

    this.currentNavGoal = goal;
    goal.send();
  }

  public cancelNavigationGoal() {
    if (this.currentNavGoal) {
      this.currentNavGoal.cancel();
      this.currentNavGoal = null;
    }
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

  public onPlan(cb: (poses: Array<{x: number, y: number}>) => void) {
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
}

export const rosService = new RosService();
