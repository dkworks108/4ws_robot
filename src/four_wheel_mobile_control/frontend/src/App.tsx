import React, { useState, useEffect } from 'react';
import { rosService } from './services/rosService';
import {
  ConnectionStatus,
  OperatingMode,
  SteeringMode,
  ArbiterStatus,
  OdometryData,
  LaserScanData,
  OccupancyGridData,
  ExplorationCoverage
} from './types/ros';

import { Header } from './components/Header';
import { EmergencyStopButton } from './components/EmergencyStopButton';
import { OperatingModeSelector } from './components/OperatingModeSelector';
import { SteeringModeSelector } from './components/SteeringModeSelector';
import { JoystickControl } from './components/JoystickControl';
import { TelemetryPanel } from './components/TelemetryPanel';
import { CameraStream } from './components/CameraStream';
import { LidarScanView } from './components/LidarScanView';
import { MapNavigation } from './components/MapNavigation';
import { ConnectionSettingsModal } from './components/ConnectionSettingsModal';

import { Gamepad2, Radio, Map as MapIcon } from 'lucide-react';

export const App: React.FC = () => {
  // Theme
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  // Connection
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [detectedIps, setDetectedIps] = useState<string[]>([]);

  // Mobile Tabs: 'pilot' | 'sensors' | 'mission'
  const [activeTab, setActiveTab] = useState<'pilot' | 'sensors' | 'mission'>('pilot');

  // Real-time ROS State
  const [arbiterStatus, setArbiterStatus] = useState<ArbiterStatus | null>(null);
  const [odom, setOdom] = useState<OdometryData | null>(null);
  const [scan, setScan] = useState<LaserScanData | null>(null);
  const [mapData, setMapData] = useState<OccupancyGridData | null>(null);
  const [plan, setPlan] = useState<Array<{ x: number; y: number }>>([]);
  const [steeringMode, setSteeringMode] = useState<SteeringMode>('four_wheel_steer');
  const [coverage, setCoverage] = useState<ExplorationCoverage | null>(null);
  const [explorationStatus, setExplorationStatus] = useState<string>('IDLE');
  const [speedLimit, setSpeedLimit] = useState<number>(1.0);
  const [cameraActive, setCameraActive] = useState<boolean>(false);

  // Initialize ROS connection on mount
  useEffect(() => {
    // Auto-detect config from server
    fetch('/api/config')
      .then(res => res.json())
      .then(cfg => {
        if (cfg.detected_ips) setDetectedIps(cfg.detected_ips);
      })
      .catch(() => {});

    // Listen to connection status
    const unsubStatus = rosService.onStatusChange(st => setStatus(st));

    // Listen to Arbiter Status
    const unsubArbiter = rosService.onArbiterStatus(data => {
      setArbiterStatus(data);
      if (data.speed_limit) setSpeedLimit(data.speed_limit);
    });

    // Listen to Odometry
    const unsubOdom = rosService.onOdometry(data => setOdom(data));

    // Listen to Laser Scan
    const unsubScan = rosService.onLaserScan(data => setScan(data));

    // Listen to SLAM Occupancy Map
    const unsubMap = rosService.onMap(data => setMapData(data));

    // Listen to Nav2 Planned Path
    const unsubPlan = rosService.onPlan(data => setPlan(data));

    // Listen to Steering Mode
    const unsubSteer = rosService.onSteeringMode(data => setSteeringMode(data));

    // Listen to Exploration
    const unsubCoverage = rosService.onExplorationCoverage(data => setCoverage(data));
    const unsubExplStatus = rosService.onExplorationStatus(data => setExplorationStatus(data));

    // Initiate connect
    rosService.connect();

    return () => {
      unsubStatus();
      unsubArbiter();
      unsubOdom();
      unsubScan();
      unsubMap();
      unsubPlan();
      unsubSteer();
      unsubCoverage();
      unsubExplStatus();
      rosService.disconnect();
    };
  }, []);

  const currentOperatingMode: OperatingMode = arbiterStatus ? arbiterStatus.operating_mode : 'MANUAL';
  const isEstopActive: boolean = arbiterStatus ? arbiterStatus.estop_active : false;

  const handleSpeedLimitChange = (val: number) => {
    setSpeedLimit(val);
    rosService.setSpeedLimit(val);
  };

  return (
    <div className={`min-h-screen ${theme === 'dark' ? 'bg-gray-950 text-gray-100' : 'bg-slate-100 text-gray-900'} flex flex-col font-sans transition-colors duration-200`}>
      {/* Top Application Bar */}
      <Header
        status={status}
        theme={theme}
        onToggleTheme={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
        onOpenSettings={() => setIsSettingsOpen(true)}
        estopActive={isEstopActive}
        activeMode={currentOperatingMode}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-2.5 sm:p-4 space-y-3 pb-20 sm:pb-6">
        {/* Prominent Safety Interlock across all screens */}
        <EmergencyStopButton estopActive={isEstopActive} />

        {/* Operating Authority Mode Selector */}
        <OperatingModeSelector
          currentMode={currentOperatingMode}
          estopActive={isEstopActive}
        />

        {/* Mobile Navigation Tab Bar (visible on small mobile screens) */}
        <div className="flex sm:hidden w-full bg-gray-900 p-1 rounded-xl border border-gray-800 font-mono text-xs">
          <button
            onClick={() => setActiveTab('pilot')}
            className={`flex-1 py-2 rounded-lg flex items-center justify-center gap-1.5 transition ${
              activeTab === 'pilot' ? 'bg-cyan-600 text-white font-bold' : 'text-gray-400'
            }`}
          >
            <Gamepad2 className="w-4 h-4" /> PILOT
          </button>
          <button
            onClick={() => setActiveTab('sensors')}
            className={`flex-1 py-2 rounded-lg flex items-center justify-center gap-1.5 transition ${
              activeTab === 'sensors' ? 'bg-cyan-600 text-white font-bold' : 'text-gray-400'
            }`}
          >
            <Radio className="w-4 h-4" /> SENSORS
          </button>
          <button
            onClick={() => setActiveTab('mission')}
            className={`flex-1 py-2 rounded-lg flex items-center justify-center gap-1.5 transition ${
              activeTab === 'mission' ? 'bg-cyan-600 text-white font-bold' : 'text-gray-400'
            }`}
          >
            <MapIcon className="w-4 h-4" /> MAP
          </button>
        </div>

        {/* Responsive Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
          {/* LEFT COLUMN: Pilot Controls (Mobile Tab: 'pilot') */}
          <div className={`lg:col-span-6 space-y-3 ${activeTab === 'pilot' ? 'block' : 'hidden sm:block'}`}>
            <SteeringModeSelector
              currentMode={steeringMode}
              linearVel={odom ? odom.linearVelocity : 0}
            />

            <JoystickControl
              disabled={isEstopActive || currentOperatingMode !== 'MANUAL'}
              speedLimit={speedLimit}
              onSpeedLimitChange={handleSpeedLimitChange}
            />

            <TelemetryPanel
              odom={odom}
              arbiterStatus={arbiterStatus}
              steeringMode={steeringMode}
              lidarActive={scan !== null}
              cameraActive={cameraActive}
            />
          </div>

          {/* RIGHT COLUMN: Sensors & Map Navigation (Mobile Tabs: 'sensors' / 'mission') */}
          <div className="lg:col-span-6 space-y-3">
            {/* Sensors View (Camera & 2D LiDAR) */}
            <div className={`space-y-3 ${activeTab === 'sensors' ? 'block' : 'hidden sm:block'}`}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <CameraStream
                  host={rosService.config.host}
                  port={rosService.config.web_video_port}
                  topic={rosService.config.camera_topic}
                  onStatusChange={setCameraActive}
                />
                <LidarScanView scan={scan} />
              </div>
            </div>

            {/* Map & Mission Navigation */}
            <div className={`${activeTab === 'mission' ? 'block' : 'hidden sm:block'}`}>
              <MapNavigation
                mapData={mapData}
                odom={odom}
                plan={plan}
                coverage={coverage}
                operatingMode={currentOperatingMode}
                explorationStatus={explorationStatus}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Connection Settings Modal */}
      <ConnectionSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        detectedIps={detectedIps}
      />
    </div>
  );
};

