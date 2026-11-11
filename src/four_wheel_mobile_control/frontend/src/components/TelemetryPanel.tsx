import React from 'react';
import { OdometryData, ArbiterStatus, SteeringMode } from '../types/ros';
import { Activity, Compass, Gauge, Radio, Video, Zap } from 'lucide-react';

interface TelemetryPanelProps {
  odom: OdometryData | null;
  arbiterStatus: ArbiterStatus | null;
  steeringMode: SteeringMode;
  lidarActive: boolean;
  cameraActive: boolean;
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({
  odom,
  arbiterStatus,
  steeringMode,
  lidarActive,
  cameraActive
}) => {
  const yawDeg = odom ? (odom.yaw * 180 / Math.PI).toFixed(1) : '0.0';
  const posX = odom ? odom.x.toFixed(2) : '0.00';
  const posY = odom ? odom.y.toFixed(2) : '0.00';
  const linVel = odom ? odom.linearVelocity.toFixed(2) : '0.00';
  const angVel = odom ? odom.angularVelocity.toFixed(2) : '0.00';

  return (
    <div className="w-full bg-gray-950 p-3 rounded-2xl border border-gray-800">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono font-bold text-gray-400 tracking-wider flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-cyan-400" /> ROBOT TELEMETRY & HEALTH
        </span>
        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/40">
          50 Hz ODOMETRY
        </span>
      </div>

      {/* Grid of Key Telemetry Values */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono">
        {/* Position */}
        <div className="bg-gray-900/80 p-2.5 rounded-xl border border-gray-800">
          <div className="text-[10px] text-gray-500 flex items-center justify-between">
            <span>POSE (X, Y)</span>
            <Compass className="w-3 h-3 text-cyan-400" />
          </div>
          <div className="text-sm font-bold text-white mt-1">
            {posX}, {posY} <span className="text-[10px] text-gray-500">m</span>
          </div>
        </div>

        {/* Heading */}
        <div className="bg-gray-900/80 p-2.5 rounded-xl border border-gray-800">
          <div className="text-[10px] text-gray-500 flex items-center justify-between">
            <span>HEADING (YAW)</span>
            <span className="text-[9px] text-cyan-400 font-bold">{yawDeg}&deg;</span>
          </div>
          <div className="text-sm font-bold text-white mt-1 flex items-center gap-1.5">
            <div
              style={{ transform: `rotate(${odom ? odom.yaw * 180 / Math.PI : 0}deg)` }}
              className="w-3.5 h-3.5 border-t-2 border-r-2 border-cyan-400 rounded-sm transform origin-center transition-transform"
            />
            <span>{yawDeg}&deg;</span>
          </div>
        </div>

        {/* Measured Velocities */}
        <div className="bg-gray-900/80 p-2.5 rounded-xl border border-gray-800">
          <div className="text-[10px] text-gray-500 flex items-center justify-between">
            <span>VELOCITY</span>
            <Gauge className="w-3 h-3 text-cyan-400" />
          </div>
          <div className="text-sm font-bold text-white mt-1">
            {linVel} <span className="text-[10px] text-gray-500">m/s</span> &bull; {angVel} <span className="text-[10px] text-gray-500">r/s</span>
          </div>
        </div>

        {/* Steering Mode */}
        <div className="bg-gray-900/80 p-2.5 rounded-xl border border-gray-800">
          <div className="text-[10px] text-gray-500 flex items-center justify-between">
            <span>STEER MODE</span>
            <Zap className="w-3 h-3 text-amber-400" />
          </div>
          <div className="text-xs font-bold text-cyan-300 mt-1 uppercase truncate">
            {steeringMode.replace('_', ' ')}
          </div>
        </div>
      </div>

      {/* Sensor Health Status Badges */}
      <div className="grid grid-cols-4 gap-2 mt-2 pt-2 border-t border-gray-900 font-mono text-[10px]">
        <div className="flex items-center gap-1.5 bg-gray-900/60 px-2 py-1.5 rounded-lg">
          <Radio className={`w-3.5 h-3.5 ${lidarActive ? 'text-emerald-400' : 'text-gray-600'}`} />
          <span className="text-gray-400">LiDAR:</span>
          <span className={lidarActive ? 'text-emerald-400 font-bold' : 'text-gray-600'}>
            {lidarActive ? '20m 15Hz' : 'OFF'}
          </span>
        </div>

        <div className="flex items-center gap-1.5 bg-gray-900/60 px-2 py-1.5 rounded-lg">
          <Compass className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-gray-400">IMU:</span>
          <span className="text-emerald-400 font-bold">50Hz</span>
        </div>

        <div className="flex items-center gap-1.5 bg-gray-900/60 px-2 py-1.5 rounded-lg">
          <Video className={`w-3.5 h-3.5 ${cameraActive ? 'text-emerald-400' : 'text-gray-600'}`} />
          <span className="text-gray-400">Cam:</span>
          <span className={cameraActive ? 'text-emerald-400 font-bold' : 'text-gray-600'}>
            {cameraActive ? 'RGB' : 'OFF'}
          </span>
        </div>

        <div className="flex items-center gap-1.5 bg-gray-900/60 px-2 py-1.5 rounded-lg">
          <Activity className={`w-3.5 h-3.5 ${arbiterStatus?.watchdog_tripped ? 'text-amber-400' : 'text-emerald-400'}`} />
          <span className="text-gray-400">Watchdog:</span>
          <span className={arbiterStatus?.watchdog_tripped ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>
            {arbiterStatus?.watchdog_tripped ? 'HOLD' : 'OK'}
          </span>
        </div>
      </div>
    </div>
  );
};

