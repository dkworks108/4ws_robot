import React, { useState, useEffect } from 'react';
import { rosService } from './services/rosService';
import { manualInputPipeline, ManualCommandSnapshot } from './services/manualInputPipeline';
import { soundEffects } from './utils/soundEffects';
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
  Handedness,
  LogEntry,
} from './types/ros';

import { Header } from './components/Header';
import { EmergencyStopButton } from './components/EmergencyStopButton';
import { OperatingModeSelector } from './components/OperatingModeSelector';
import { SteeringModeSelector } from './components/SteeringModeSelector';
import { SpeedLimitControl } from './components/SpeedLimitControl';
import { JoystickControl } from './components/JoystickControl';
import { KeyboardControlPanel } from './components/KeyboardControlPanel';
import { RobotViewTop } from './components/RobotViewTop';
import { CameraStream } from './components/CameraStream';
import { LidarScanView } from './components/LidarScanView';
import { ImuView } from './components/ImuView';
import { SlamMapPanel } from './components/SlamMapPanel';
import { NavExplorePanel } from './components/NavExplorePanel';
import { TelemetryPanel, SystemHealthPanel, WatchdogPanel } from './components/TelemetryPanel';
import { ConnectionSettingsModal } from './components/ConnectionSettingsModal';

import {
  Home,
  Map as MapIcon,
  Radio,
  BarChart3,
  FileText,
  Settings,
  Gamepad2,
  ChevronRight,
  Crosshair,
  Cpu,
} from 'lucide-react';

type DesktopSection = 'control' | 'map' | 'sensors' | 'telemetry' | 'logs';
type MobileTab = 'pilot' | 'map' | 'sensors' | 'telemetry';

const HANDEDNESS_KEY = '4ws_mobile_handedness';

export const App: React.FC = () => {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [detectedIps, setDetectedIps] = useState<string[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [desktopSection, setDesktopSection] = useState<DesktopSection>('control');
  const [mobileTab, setMobileTab] = useState<MobileTab>('pilot');

  const [handedness, setHandedness] = useState<Handedness>(() => {
    try {
      const saved = localStorage.getItem(HANDEDNESS_KEY);
      return saved === 'left' ? 'left' : 'right';
    } catch {
      return 'right';
    }
  });
  const [sfxMuted, setSfxMuted] = useState<boolean>(() => soundEffects.isMuted());

  // Real-time ROS 2 State
  const [arbiterStatus, setArbiterStatus] = useState<ArbiterStatus | null>(null);
  const [odom, setOdom] = useState<OdometryData | null>(null);
  const [scan, setScan] = useState<LaserScanData | null>(null);
  const [mapData, setMapData] = useState<OccupancyGridData | null>(null);
  const [plan, setPlan] = useState<Array<{ x: number; y: number }>>([]);
  const [steeringMode, setSteeringMode] = useState<SteeringMode>('four_wheel_steer');
  const [coverage, setCoverage] = useState<ExplorationCoverage | null>(null);
  const [explorationStatus, setExplorationStatus] = useState<string>('READY');
  const [speedLimit, setSpeedLimit] = useState<number>(1.0);
  const [imu, setImu] = useState<ImuData | null>(null);
  const [jointSteer, setJointSteer] = useState<JointSteerAngles | null>(null);
  const [readiness, setReadiness] = useState<ReadinessStatus | null>(null);
  const [clockStatus, setClockStatus] = useState<ClockStatus | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [cameraActive, setCameraActive] = useState<boolean>(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [selectedGoal, setSelectedGoal] = useState<{ x: number; y: number } | null>(null);
  const [goalPickArmed, setGoalPickArmed] = useState<boolean>(false);
  const [clockText, setClockText] = useState<string>(() => new Date().toTimeString().slice(0, 8));

  // Shared Manual Input Pipeline Snapshot (Keyboard + Joystick)
  const [manualSnap, setManualSnap] = useState<ManualCommandSnapshot>(() =>
    manualInputPipeline.getSnapshot()
  );

  const currentOperatingMode: OperatingMode = arbiterStatus ? arbiterStatus.operating_mode : 'MANUAL';
  const isEstopActive: boolean = arbiterStatus ? arbiterStatus.estop_active : false;

  // Keep shared manual pipeline synchronized with ROS authority/connection/E-stop
  useEffect(() => {
    manualInputPipeline.updateSystemState(status, currentOperatingMode, isEstopActive);
  }, [status, currentOperatingMode, isEstopActive]);

  // Global physical keyboard & browser safety listeners
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      manualInputPipeline.handleKeyDown(e);
    };
    const onKeyUp = (e: KeyboardEvent) => {
      manualInputPipeline.handleKeyUp(e);
    };
    const onBlur = () => {
      manualInputPipeline.setWindowFocus(false);
    };
    const onFocus = () => {
      manualInputPipeline.setWindowFocus(true);
    };
    const onVisibilityChange = () => {
      manualInputPipeline.setPageVisibility(!document.hidden);
    };

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    window.addEventListener('blur', onBlur);
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibilityChange);

    const unsubPipe = manualInputPipeline.subscribe(setManualSnap);
    const clockTimer = setInterval(() => {
      setClockText(new Date().toTimeString().slice(0, 8));
    }, 1000);

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      unsubPipe();
      clearInterval(clockTimer);
      manualInputPipeline.forceStopAll();
    };
  }, []);

  // Initialize ROS connection & subscriptions on mount
  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(cfg => {
        if (cfg.detected_ips) setDetectedIps(cfg.detected_ips);
      })
      .catch(() => {});

    let prevStatus: ConnectionStatus = 'disconnected';
    const unsubStatus = rosService.onStatusChange(st => {
      setStatus(st);
      if (st === 'connected' && prevStatus !== 'connected') {
        soundEffects.playConnect();
      } else if (st === 'disconnected' && prevStatus === 'connected') {
        soundEffects.playDisconnect();
      }
      prevStatus = st;
    });

    const unsubArbiter = rosService.onArbiterStatus(data => {
      setArbiterStatus(data);
      if (typeof data.speed_limit === 'number') setSpeedLimit(data.speed_limit);
    });
    const unsubOdom = rosService.onOdometry(setOdom);
    const unsubScan = rosService.onLaserScan(setScan);
    const unsubMap = rosService.onMap(setMapData);
    const unsubPlan = rosService.onPlan(setPlan);
    const unsubSteer = rosService.onSteeringMode(setSteeringMode);
    const unsubCov = rosService.onExplorationCoverage(setCoverage);
    const unsubExplStatus = rosService.onExplorationStatus(setExplorationStatus);
    const unsubImu = rosService.onImu(setImu);
    const unsubJoints = rosService.onJointSteer(setJointSteer);
    const unsubReadiness = rosService.onReadiness(setReadiness);
    const unsubClock = rosService.onClock(setClockStatus);
    const unsubLat = rosService.onLatency(setLatencyMs);
    const unsubLog = rosService.onLog(entry => {
      setLogs(prev => [entry, ...prev].slice(0, 80));
    });

    rosService.connect();

    return () => {
      unsubStatus();
      unsubArbiter();
      unsubOdom();
      unsubScan();
      unsubMap();
      unsubPlan();
      unsubSteer();
      unsubCov();
      unsubExplStatus();
      unsubImu();
      unsubJoints();
      unsubReadiness();
      unsubClock();
      unsubLat();
      unsubLog();
      rosService.disconnect();
    };
  }, []);

  const handleSpeedLimitChange = (val: number) => {
    setSpeedLimit(val);
    rosService.setSpeedLimit(val);
  };

  const handleChangeHandedness = (h: Handedness) => {
    setHandedness(h);
    try {
      localStorage.setItem(HANDEDNESS_KEY, h);
    } catch {
      // ignore
    }
  };

  const handleToggleSfx = () => {
    const nextMuted = soundEffects.toggleMute();
    setSfxMuted(nextMuted);
  };

  const manualDisabled = isEstopActive || currentOperatingMode !== 'MANUAL';
  const headingDeg = odom ? (((odom.yaw * 180) / Math.PI + 360) % 360).toFixed(1) : '--';
  const watchdogOk = !(arbiterStatus?.watchdog_tripped ?? false);
  const fpsDisplay = scan?.rateHz ? scan.rateHz : clockStatus?.rateHz ? clockStatus.rateHz : 0;

  const sidebarItems: Array<{ id: DesktopSection | 'settings'; label: string; icon: React.ReactNode }> = [
    { id: 'control', label: 'CONTROL', icon: <Home className="w-4 h-4" /> },
    { id: 'map', label: 'MAP & NAV', icon: <MapIcon className="w-4 h-4" /> },
    { id: 'sensors', label: 'SENSORS', icon: <Radio className="w-4 h-4" /> },
    { id: 'telemetry', label: 'TELEMETRY', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'logs', label: 'LOGS', icon: <FileText className="w-4 h-4" /> },
    { id: 'settings', label: 'SETTINGS', icon: <Settings className="w-4 h-4" /> },
  ];

  const handleSelectGoalFromMap = (goal: { x: number; y: number }) => {
    setSelectedGoal(goal);
    setGoalPickArmed(false);
  };

  const themeBg = theme === 'dark' ? 'bg-[#0F0F23] text-white' : 'bg-slate-200 text-slate-950';

  return (
    <div className={`min-h-screen flex flex-col overflow-x-hidden ${themeBg}`}>
      {/* Top Global Header */}
      <Header
        status={status}
        theme={theme}
        onToggleTheme={() => setTheme(t => (t === 'dark' ? 'light' : 'dark'))}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onToggleSidebar={() => setSidebarOpen(s => !s)}
        clockStatus={clockStatus}
        latencyMs={latencyMs}
        fps={fpsDisplay}
        keyboardStatus={manualSnap.keyboardStatus}
        sfxMuted={sfxMuted}
        onToggleSfx={handleToggleSfx}
      />

      {/* Body Wrapper */}
      <div className="flex-1 flex min-w-0">
        {/* DESKTOP LEFT SIDEBAR RAIL */}
        {sidebarOpen && (
          <aside
            aria-label="Desktop Section Navigation"
            className="hidden lg:flex flex-col w-[76px] shrink-0 bg-[#080818] border-r-2 border-white py-2 px-1.5 gap-2"
          >
            {sidebarItems.map(item => {
              const active = desktopSection === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    soundEffects.playClick();
                    if (item.id === 'settings') {
                      setIsSettingsOpen(true);
                    } else {
                      setDesktopSection(item.id);
                    }
                  }}
                  aria-current={active ? 'page' : undefined}
                  className={`py-2 px-1 border-2 flex flex-col items-center justify-center gap-1.5 font-pixel text-[7px] transition-colors ${
                    active
                      ? 'bg-[#FFFF00] text-black border-black shadow-pixel-sm'
                      : 'bg-[#0F0F23] text-white border-white/60 hover:border-[#FFFF00]'
                  }`}
                >
                  {item.icon}
                  <span className="text-center leading-tight">{item.label}</span>
                </button>
              );
            })}
          </aside>
        )}

        {/* MAIN CONTENT AREA */}
        <main className="flex-1 min-w-0 p-2 sm:p-2.5 pb-20 lg:pb-2.5 space-y-2.5 flex flex-col">
          {/* Persistent System Safety Interlock Banner (Desktop + All Mobile Tabs) */}
          <EmergencyStopButton estopActive={isEstopActive} />

          {/* ==================== DESKTOP CONSOLE (lg and up) ==================== */}
          <div className="hidden lg:flex flex-col gap-2.5 flex-1">
            {desktopSection === 'control' && (
              <>
                {/* Main 12-Col Grid matching Desktop Reference */}
                <div className="grid grid-cols-12 gap-2.5 items-stretch">
                  {/* LEFT COL (3 cols): Authority + 5 Steering Modes + Speed Limit */}
                  <div className="col-span-3 flex flex-col gap-2.5">
                    <OperatingModeSelector
                      currentMode={currentOperatingMode}
                      estopActive={isEstopActive}
                    />
                    <SteeringModeSelector currentMode={steeringMode} variant="desktop" />
                    <SpeedLimitControl
                      speedLimit={speedLimit}
                      disabled={isEstopActive}
                      onChange={handleSpeedLimitChange}
                    />
                  </div>

                  {/* CENTER + RIGHT-TOP AREA (9 cols) */}
                  <div className="col-span-9 flex flex-col gap-2.5">
                    {/* Upper Row: Manual Control + Robot View + Sensors */}
                    <div className="grid grid-cols-9 gap-2.5">
                      {/* CENTER-LEFT (3 cols): Manual Control Joystick + Keyboard */}
                      <div className="col-span-3 pixel-panel bg-[#080818] flex flex-col justify-between">
                        <div className="pixel-header px-2.5 py-1.5 flex items-center justify-between">
                          <span className="font-pixel text-[9px] text-white">MANUAL CONTROL</span>
                          <span className="font-mono text-[9px] font-bold text-[#FFFF00]">
                            {manualSnap.source.toUpperCase()}
                          </span>
                        </div>

                        <div className="p-2.5 flex-1 flex flex-col justify-between gap-2.5">
                          <JoystickControl
                            disabled={manualDisabled}
                            showVelocityRow
                            vxFeedback={odom ? odom.linearVelocity : manualSnap.vx}
                            vyFeedback={odom ? odom.linearVelocityY : manualSnap.vy}
                            wzFeedback={odom ? odom.angularVelocity : manualSnap.wz}
                          />

                          <KeyboardControlPanel
                            activeKeys={manualSnap.activeKeys}
                            keyboardStatus={manualSnap.keyboardStatus}
                            keyboardEnabled={manualInputPipeline.isKeyboardEnabled()}
                            sensitivity={manualInputPipeline.getKeyboardSensitivity()}
                          />
                        </div>
                      </div>

                      {/* CENTER-RIGHT (3 cols): Top-Down Robot View */}
                      <div className="col-span-3">
                        <RobotViewTop steeringMode={steeringMode} jointSteer={jointSteer} />
                      </div>

                      {/* RIGHT COL (3 cols): RGB Camera + LiDAR 360 + IMU */}
                      <div className="col-span-3 flex flex-col gap-2.5">
                        <CameraStream
                          host={rosService.config.host}
                          port={rosService.config.web_video_port}
                          topic={rosService.config.camera_topic}
                          onStatusChange={setCameraActive}
                        />
                        <LidarScanView scan={scan} />
                        <ImuView imu={imu} />
                      </div>
                    </div>

                    {/* Middle-Bottom Row: SLAM Map (5 cols) + Navigation & Exploration (4 cols) */}
                    <div className="grid grid-cols-9 gap-2.5">
                      <div className="col-span-5">
                        <SlamMapPanel
                          mapData={mapData}
                          odom={odom}
                          plan={plan}
                          coverage={coverage}
                          selectedGoal={selectedGoal}
                          onSelectGoal={handleSelectGoalFromMap}
                          goalPickArmed={goalPickArmed}
                          heightClass="h-[195px]"
                        />
                      </div>
                      <div className="col-span-4">
                        <NavExplorePanel
                          operatingMode={currentOperatingMode}
                          estopActive={isEstopActive}
                          explorationStatus={explorationStatus}
                          coverage={coverage}
                          selectedGoal={selectedGoal}
                          onClearGoal={() => setSelectedGoal(null)}
                          onTogglePickGoal={() => setGoalPickArmed(a => !a)}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bottom Row: Robot Telemetry + System Health + Watchdog */}
                <div className="grid grid-cols-12 gap-2.5">
                  <div className="col-span-5">
                    <TelemetryPanel odom={odom} />
                  </div>
                  <div className="col-span-4">
                    <SystemHealthPanel
                      readiness={readiness}
                      lidarActive={scan !== null}
                      imuActive={imu !== null}
                      mapActive={mapData !== null}
                    />
                  </div>
                  <div className="col-span-3">
                    <WatchdogPanel arbiterStatus={arbiterStatus} />
                  </div>
                </div>
              </>
            )}

            {desktopSection === 'map' && (
              <div className="grid grid-cols-12 gap-3 flex-1">
                <div className="col-span-8">
                  <SlamMapPanel
                    mapData={mapData}
                    odom={odom}
                    plan={plan}
                    coverage={coverage}
                    selectedGoal={selectedGoal}
                    onSelectGoal={handleSelectGoalFromMap}
                    goalPickArmed={goalPickArmed}
                    heightClass="h-[520px]"
                  />
                </div>
                <div className="col-span-4 flex flex-col gap-3">
                  <OperatingModeSelector
                    currentMode={currentOperatingMode}
                    estopActive={isEstopActive}
                  />
                  <NavExplorePanel
                    operatingMode={currentOperatingMode}
                    estopActive={isEstopActive}
                    explorationStatus={explorationStatus}
                    coverage={coverage}
                    selectedGoal={selectedGoal}
                    onClearGoal={() => setSelectedGoal(null)}
                    onTogglePickGoal={() => setGoalPickArmed(a => !a)}
                  />
                  <TelemetryPanel odom={odom} />
                </div>
              </div>
            )}

            {desktopSection === 'sensors' && (
              <div className="grid grid-cols-12 gap-3">
                <div className="col-span-5">
                  <CameraStream
                    host={rosService.config.host}
                    port={rosService.config.web_video_port}
                    topic={rosService.config.camera_topic}
                    onStatusChange={setCameraActive}
                  />
                </div>
                <div className="col-span-4">
                  <LidarScanView scan={scan} />
                </div>
                <div className="col-span-3">
                  <ImuView imu={imu} />
                </div>
              </div>
            )}

            {desktopSection === 'telemetry' && (
              <div className="grid grid-cols-12 gap-3">
                <div className="col-span-8 space-y-3">
                  <TelemetryPanel odom={odom} />
                  <SystemHealthPanel
                    readiness={readiness}
                    lidarActive={scan !== null}
                    imuActive={imu !== null}
                    mapActive={mapData !== null}
                  />
                  <WatchdogPanel arbiterStatus={arbiterStatus} />
                </div>
                <div className="col-span-4">
                  <RobotViewTop steeringMode={steeringMode} jointSteer={jointSteer} />
                </div>
              </div>
            )}

            {desktopSection === 'logs' && (
              <div className="pixel-panel bg-[#080818] flex flex-col flex-1 min-h-[380px]">
                <div className="pixel-header px-3 py-1.5 flex items-center justify-between">
                  <span className="font-pixel text-[9px] text-white">SYSTEM EVENT &amp; ROS LOGS</span>
                  <button
                    type="button"
                    onClick={() => {
                      soundEffects.playClick();
                      setLogs([]);
                    }}
                    className="pixel-btn px-2 py-0.5 bg-[#11112B] text-white font-mono text-[10px]"
                  >
                    CLEAR
                  </button>
                </div>
                <div className="p-3 font-mono text-xs space-y-1 overflow-y-auto max-h-[460px]">
                  {logs.length === 0 ? (
                    <div className="text-slate-400">No session events logged yet.</div>
                  ) : (
                    logs.map(l => (
                      <div key={l.id} className="flex items-start gap-2 border-b border-white/10 pb-1">
                        <span className="text-slate-400 shrink-0">[{l.time}]</span>
                        <span
                          className={`font-bold shrink-0 ${
                            l.level === 'ERROR'
                              ? 'text-[#FF0000]'
                              : l.level === 'WARN'
                              ? 'text-[#FFFF00]'
                              : 'text-[#00FF00]'
                          }`}
                        >
                          {l.level}
                        </span>
                        <span className="text-white break-all">{l.message}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* ==================== MOBILE ONE-HANDED INTERFACE (< lg) ==================== */}
          <div className="lg:hidden flex flex-col gap-2">
            {mobileTab === 'pilot' && (
              <>
                {/* 3. Manual / Nav2 / Explore Selector */}
                <OperatingModeSelector
                  currentMode={currentOperatingMode}
                  estopActive={isEstopActive}
                  compact
                />

                {/* 4 & 5. Compact Steer Mode + Speed Limiter Row */}
                <div className="grid grid-cols-2 gap-2">
                  <SteeringModeSelector currentMode={steeringMode} variant="mobile" />
                  <SpeedLimitControl
                    speedLimit={speedLimit}
                    disabled={isEstopActive}
                    onChange={handleSpeedLimitChange}
                    compact
                  />
                </div>

                {/* 6. Live Velocity Readings */}
                <div className="pixel-panel bg-[#080818] px-2 py-1.5 grid grid-cols-3 gap-1 text-center">
                  <div>
                    <div className="font-mono text-[9px] text-slate-300">Vx</div>
                    <div className="font-mono text-xs font-extrabold text-[#FFFF00]">
                      {(odom ? odom.linearVelocity : manualSnap.vx).toFixed(2)} m/s
                    </div>
                  </div>
                  <div className="border-x border-white/30">
                    <div className="font-mono text-[9px] text-slate-300">Vy</div>
                    <div className="font-mono text-xs font-extrabold text-[#FFFF00]">
                      {(odom ? odom.linearVelocityY : manualSnap.vy).toFixed(2)} m/s
                    </div>
                  </div>
                  <div>
                    <div className="font-mono text-[9px] text-slate-300">&omega;Z</div>
                    <div className="font-mono text-xs font-extrabold text-[#FFFF00]">
                      {(odom ? odom.angularVelocity : manualSnap.wz).toFixed(2)} rad/s
                    </div>
                  </div>
                </div>

                {/* 7, 8 & 9. Primary Thumb Zone: Handedness-Aware Joystick + Rotation + Compact Robot View */}
                <div className="grid grid-cols-12 gap-2 items-stretch">
                  {handedness === 'left' ? (
                    <>
                      <div className="col-span-8 flex items-center justify-center py-1">
                        <JoystickControl disabled={manualDisabled} compact handedness="left" />
                      </div>
                      <div className="col-span-4">
                        <RobotViewTop
                          steeringMode={steeringMode}
                          jointSteer={jointSteer}
                          compact
                        />
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="col-span-4">
                        <RobotViewTop
                          steeringMode={steeringMode}
                          jointSteer={jointSteer}
                          compact
                        />
                      </div>
                      <div className="col-span-8 flex items-center justify-center py-1">
                        <JoystickControl disabled={manualDisabled} compact handedness="right" />
                      </div>
                    </>
                  )}
                </div>

                {/* 10. Camera & Sensor Shortcuts */}
                <div className="grid grid-cols-12 gap-2 items-stretch">
                  <div className="col-span-6">
                    <CameraStream
                      host={rosService.config.host}
                      port={rosService.config.web_video_port}
                      topic={rosService.config.camera_topic}
                      compact
                      onStatusChange={setCameraActive}
                      onClickPreview={() => {
                        soundEffects.playClick();
                        setMobileTab('sensors');
                      }}
                    />
                  </div>
                  <div className="col-span-6 flex flex-col justify-between gap-1.5">
                    <button
                      type="button"
                      onClick={() => {
                        soundEffects.playClick();
                        setMobileTab('sensors');
                      }}
                      className="pixel-btn px-2 py-1.5 bg-[#080818] text-white flex items-center justify-between font-mono text-[10px] font-bold"
                    >
                      <span className="flex items-center gap-1.5 truncate">
                        <span className={`w-2 h-2 ${scan ? 'bg-[#00FF00]' : 'bg-slate-500'}`} />
                        <Radio className="w-3 h-3 text-[#38BDF8] shrink-0" />
                        <span>LiDAR (360&deg;)</span>
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 shrink-0" />
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        soundEffects.playClick();
                        setMobileTab('sensors');
                      }}
                      className="pixel-btn px-2 py-1.5 bg-[#080818] text-white flex items-center justify-between font-mono text-[10px] font-bold"
                    >
                      <span className="flex items-center gap-1.5 truncate">
                        <span className={`w-2 h-2 ${imu ? 'bg-[#00FF00]' : 'bg-slate-500'}`} />
                        <Cpu className="w-3 h-3 text-[#FFFF00] shrink-0" />
                        <span>IMU</span>
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 shrink-0" />
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        soundEffects.playClick();
                        setMobileTab('map');
                      }}
                      className="pixel-btn px-2 py-1.5 bg-[#080818] text-white flex items-center justify-between font-mono text-[10px] font-bold"
                    >
                      <span className="flex items-center gap-1.5 truncate">
                        <span className={`w-2 h-2 ${mapData ? 'bg-[#00FF00]' : 'bg-slate-500'}`} />
                        <MapIcon className="w-3 h-3 text-[#00FF00] shrink-0" />
                        <span>MAP (SLAM)</span>
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 shrink-0" />
                    </button>
                  </div>
                </div>

                {/* 11. Pose & Watchdog Strip */}
                <div className="pixel-panel bg-[#080818] px-2.5 py-1.5 grid grid-cols-3 gap-1.5 items-center font-mono text-[10px]">
                  <div>
                    <div className="text-[8px] text-slate-300 flex items-center gap-1">
                      <Crosshair className="w-2.5 h-2.5 text-[#38BDF8]" /> POSE (X, Y)
                    </div>
                    <div className="font-extrabold text-white truncate">
                      {odom ? `${odom.x.toFixed(2)}, ${odom.y.toFixed(2)}` : '--, --'}
                    </div>
                  </div>
                  <div className="text-center border-x border-white/30">
                    <div className="text-[8px] text-slate-300">HEADING</div>
                    <div className="font-extrabold text-[#FFFF00]">{headingDeg}&deg;</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[8px] text-slate-300">WATCHDOG</div>
                    <div className={`font-pixel text-[9px] ${watchdogOk ? 'text-[#00FF00]' : 'text-[#FFFF00]'}`}>
                      {watchdogOk ? '● OK' : '● TRIP'}
                    </div>
                  </div>
                </div>
              </>
            )}

            {mobileTab === 'map' && (
              <div className="space-y-2.5">
                <OperatingModeSelector
                  currentMode={currentOperatingMode}
                  estopActive={isEstopActive}
                  compact
                />
                <SlamMapPanel
                  mapData={mapData}
                  odom={odom}
                  plan={plan}
                  coverage={coverage}
                  selectedGoal={selectedGoal}
                  onSelectGoal={handleSelectGoalFromMap}
                  goalPickArmed={goalPickArmed}
                  heightClass="h-[260px]"
                />
                <NavExplorePanel
                  operatingMode={currentOperatingMode}
                  estopActive={isEstopActive}
                  explorationStatus={explorationStatus}
                  coverage={coverage}
                  selectedGoal={selectedGoal}
                  onClearGoal={() => setSelectedGoal(null)}
                  onTogglePickGoal={() => setGoalPickArmed(a => !a)}
                />
              </div>
            )}

            {mobileTab === 'sensors' && (
              <div className="space-y-2.5">
                <CameraStream
                  host={rosService.config.host}
                  port={rosService.config.web_video_port}
                  topic={rosService.config.camera_topic}
                  onStatusChange={setCameraActive}
                />
                <LidarScanView scan={scan} />
                <ImuView imu={imu} />
              </div>
            )}

            {mobileTab === 'telemetry' && (
              <div className="space-y-2.5">
                <TelemetryPanel odom={odom} />
                <SystemHealthPanel
                  readiness={readiness}
                  lidarActive={scan !== null}
                  imuActive={imu !== null}
                  mapActive={mapData !== null}
                />
                <WatchdogPanel arbiterStatus={arbiterStatus} />
                <RobotViewTop steeringMode={steeringMode} jointSteer={jointSteer} />
              </div>
            )}
          </div>
        </main>
      </div>

      {/* DESKTOP BOTTOM SYSTEM TICKER BAR */}
      <footer className="hidden lg:flex items-center justify-between px-3 py-1 bg-[#080818] border-t-2 border-white font-pixel text-[8px]">
        <div className="flex items-center gap-3 overflow-hidden">
          <span className="text-[#FFFF00] shrink-0">&#9654; SYSTEM:</span>
          <span className={status === 'connected' ? 'text-[#00FF00]' : 'text-[#FF0000]'}>
            {status === 'connected' ? 'ROBOT ONLINE' : 'DISCONNECTED'}
          </span>
          <span className="text-white">&gt;</span>
          <span className={readiness?.components?.Controllers?.healthy ? 'text-[#00FF00]' : 'text-slate-300'}>
            CONTROLLERS {readiness?.components?.Controllers?.healthy ? 'ACTIVE' : 'PENDING'}
          </span>
          <span className="text-white">&gt;</span>
          <span className={mapData ? 'text-[#00FF00]' : 'text-slate-300'}>
            SLAM {mapData ? 'READY' : 'WAIT'}
          </span>
          <span className="text-white">&gt;</span>
          <span className="text-[#00FF00]">
            NAV2 {currentOperatingMode === 'AUTONOMOUS_NAV' ? 'ACTIVE' : 'IDLE'}
          </span>
          <span className="text-white">&gt;</span>
          <span className="text-[#00FF00]">
            EXPLORATION {explorationStatus || 'READY'}
          </span>
          <span className="text-white">&gt;</span>
          <span className={cameraActive ? 'text-[#00FF00]' : 'text-slate-400'}>
            CAM {cameraActive ? 'LIVE' : 'WAIT'}
          </span>
        </div>
        <div className="font-mono text-xs font-bold text-white shrink-0">{clockText}</div>
      </footer>

      {/* MOBILE FIXED 4-TAB BOTTOM NAVIGATION BAR */}
      <nav
        aria-label="Mobile Bottom Navigation"
        className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#080818] border-t-2 border-white grid grid-cols-4 gap-1 p-1.5"
      >
        {(
          [
            { id: 'pilot', label: 'PILOT', icon: <Gamepad2 className="w-4 h-4" /> },
            { id: 'map', label: 'MAP', icon: <MapIcon className="w-4 h-4" /> },
            { id: 'sensors', label: 'SENSORS', icon: <Radio className="w-4 h-4" /> },
            { id: 'telemetry', label: 'TELEMETRY', icon: <BarChart3 className="w-4 h-4" /> },
          ] as Array<{ id: MobileTab; label: string; icon: React.ReactNode }>
        ).map(tab => {
          const active = mobileTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                soundEffects.playClick();
                setMobileTab(tab.id);
              }}
              aria-current={active ? 'page' : undefined}
              className={`pixel-btn py-1.5 px-1 flex flex-col items-center justify-center gap-1 font-pixel text-[8px] ${
                active
                  ? 'bg-[#FFFF00] text-black border-black'
                  : 'bg-[#0F0F23] text-white border-white/70'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Settings & Preferences Modal */}
      <ConnectionSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        detectedIps={detectedIps}
        handedness={handedness}
        onChangeHandedness={handleChangeHandedness}
        sfxMuted={sfxMuted}
        onToggleSfx={handleToggleSfx}
      />
    </div>
  );
};
