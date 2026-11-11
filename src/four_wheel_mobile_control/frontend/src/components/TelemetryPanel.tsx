import React from 'react';
import { ArbiterStatus, OdometryData, ReadinessStatus } from '../types/ros';
import { BarChart3, Activity, Timer, CheckSquare, AlertTriangle } from 'lucide-react';

interface TelemetryPanelProps {
  odom: OdometryData | null;
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ odom }) => {
  const headingDeg = odom ? (((odom.yaw * 180) / Math.PI + 360) % 360).toFixed(1) : '--';

  const cells = [
    { label: 'X', val: odom ? `${odom.x.toFixed(2)} m` : '--' },
    { label: 'Y', val: odom ? `${odom.y.toFixed(2)} m` : '--' },
    { label: 'HEADING', val: `${headingDeg}°` },
    { label: 'Vx', val: odom ? `${odom.linearVelocity.toFixed(2)} m/s` : '--' },
    { label: 'Vy', val: odom ? `${odom.linearVelocityY.toFixed(2)} m/s` : '--' },
    { label: 'ωZ', val: odom ? `${odom.angularVelocity.toFixed(2)} rad/s` : '--' },
  ];

  return (
    <div className="pixel-panel bg-[#080818] flex flex-col">
      <div className="pixel-header px-2.5 py-1 flex items-center gap-1.5">
        <BarChart3 className="w-3.5 h-3.5 text-white shrink-0" />
        <span className="font-pixel text-[8px] sm:text-[9px] text-white truncate">
          ROBOT TELEMETRY (ODOMETRY)
        </span>
      </div>

      <div className="p-2 grid grid-cols-3 sm:grid-cols-6 gap-1.5">
        {cells.map(c => (
          <div key={c.label} className="bg-[#0F0F23] border border-white/50 px-1.5 py-1 text-center">
            <div className="font-mono text-[9px] text-slate-300">{c.label}</div>
            <div className="font-mono text-[11px] font-extrabold text-[#FFFF00] truncate">{c.val}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

interface SystemHealthPanelProps {
  readiness: ReadinessStatus | null;
  lidarActive: boolean;
  imuActive: boolean;
  mapActive: boolean;
}

export const SystemHealthPanel: React.FC<SystemHealthPanelProps> = ({
  readiness,
  lidarActive,
  imuActive,
  mapActive,
}) => {
  const comp = readiness?.components;

  const items = [
    {
      label: 'CONTROLLERS (9/9)',
      ok: comp?.Controllers ? comp.Controllers.healthy : false,
    },
    {
      label: 'LIDAR (/scan)',
      ok: comp?.LiDAR ? comp.LiDAR.healthy : lidarActive,
    },
    {
      label: 'IMU (/imu/data)',
      ok: comp?.IMU ? comp.IMU.healthy : imuActive,
    },
    {
      label: 'SLAM (/map)',
      ok: comp?.SLAM ? comp.SLAM.healthy : mapActive,
    },
    {
      label: 'NAV2 (ACTIVE)',
      ok: comp?.Nav2 ? comp.Nav2.healthy : false,
    },
    {
      label: 'EXPLORER (READY)',
      ok: comp?.Exploration ? comp.Exploration.healthy : false,
    },
  ];

  return (
    <div className="pixel-panel bg-[#080818] flex flex-col">
      <div className="pixel-header px-2.5 py-1 flex items-center justify-between gap-1">
        <span className="font-pixel text-[8px] sm:text-[9px] text-white flex items-center gap-1.5 truncate">
          <Activity className="w-3.5 h-3.5 shrink-0" />
          <span>SYSTEM HEALTH</span>
        </span>
        <span
          className={`px-1.5 py-0.5 border font-pixel text-[7px] ${
            readiness?.system_state === 'READY'
              ? 'bg-[#00FF00] text-black border-black'
              : readiness?.system_state === 'DEGRADED'
              ? 'bg-[#FFFF00] text-black border-black'
              : 'bg-slate-700 text-slate-200 border-white/50'
          }`}
        >
          {readiness?.system_state || 'SYNC'}
        </span>
      </div>

      <div className="p-2 grid grid-cols-2 gap-x-3 gap-y-1 font-mono text-[10px] font-bold">
        {items.map(it => (
          <div key={it.label} className="flex items-center gap-1.5 min-w-0">
            {it.ok ? (
              <CheckSquare className="w-3.5 h-3.5 text-[#00FF00] shrink-0" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5 text-[#FFFF00] shrink-0" />
            )}
            <span className={`truncate ${it.ok ? 'text-white' : 'text-slate-400'}`}>{it.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

interface WatchdogPanelProps {
  arbiterStatus: ArbiterStatus | null;
}

export const WatchdogPanel: React.FC<WatchdogPanelProps> = ({ arbiterStatus }) => {
  const tripped = arbiterStatus?.watchdog_tripped ?? false;

  return (
    <div className="pixel-panel bg-[#080818] flex flex-col">
      <div className="pixel-header px-2.5 py-1 flex items-center gap-1.5">
        <Timer className="w-3.5 h-3.5 text-white shrink-0" />
        <span className="font-pixel text-[8px] sm:text-[9px] text-white">WATCHDOG</span>
      </div>

      <div className="p-2.5 flex items-center justify-between gap-2 flex-1">
        <div className="font-pixel text-sm sm:text-base text-[#FFFF00]">400 ms</div>
        <div className="flex items-center gap-1.5">
          <span
            className={`w-3 h-3 inline-block border border-black ${
              tripped ? 'bg-[#FFFF00]' : 'bg-[#00FF00]'
            }`}
          />
          <span
            className={`font-pixel text-[10px] ${
              tripped ? 'text-[#FFFF00]' : 'text-[#00FF00]'
            }`}
          >
            {tripped ? 'TRIP' : 'OK'}
          </span>
        </div>
      </div>
    </div>
  );
};
