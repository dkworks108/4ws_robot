import React from 'react';
import { JointSteerAngles, SteeringMode } from '../types/ros';
import { getSteeringModeMeta } from './SteeringModeSelector';
import { Camera } from 'lucide-react';

interface RobotViewTopProps {
  steeringMode: SteeringMode;
  jointSteer: JointSteerAngles | null;
  compact?: boolean;
}

export const RobotViewTop: React.FC<RobotViewTopProps> = ({
  steeringMode,
  jointSteer,
  compact = false,
}) => {
  const meta = getSteeringModeMeta(steeringMode);
  const modeDisplay = meta.shortLabel.replace(/^[A-E]\.\s*/, '');

  const fl = jointSteer ? jointSteer.flDeg : 0;
  const fr = jointSteer ? jointSteer.frDeg : 0;
  const rl = jointSteer ? jointSteer.rlDeg : 0;
  const rr = jointSteer ? jointSteer.rrDeg : 0;

  const fmtDeg = (d: number) => `${d >= 0 ? '+' : ''}${d.toFixed(1)}°`;

  // ROS +angle is CCW (left), SVG +rotate is CW -> negate for screen orientation
  const wheels = [
    { x: 30, y: 38, deg: -fl, label: 'FL' },
    { x: 90, y: 38, deg: -fr, label: 'FR' },
    { x: 30, y: 92, deg: -rl, label: 'RL' },
    { x: 90, y: 92, deg: -rr, label: 'RR' },
  ];

  return (
    <div className="pixel-panel bg-[#080818] flex flex-col h-full">
      <div className="pixel-header px-2.5 py-1.5 flex items-center justify-between gap-1">
        <span className="font-pixel text-[8px] sm:text-[9px] text-white flex items-center gap-1.5 truncate">
          <Camera className="w-3.5 h-3.5 shrink-0" />
          <span>{compact ? 'ROBOT VIEW' : 'ROBOT VIEW (TOP)'}</span>
        </span>
      </div>

      <div className="p-2 flex-1 flex flex-col items-center justify-between gap-2">
        {!compact && (
          <div className="w-full text-center">
            <span className="inline-block px-2.5 py-0.5 bg-[#FFFF00] text-black border-2 border-black font-pixel text-[8px]">
              MODE: {modeDisplay}
            </span>
          </div>
        )}

        {/* Top-Down Pixel Robot Canvas */}
        <div className="w-full flex-1 min-h-[120px] pixel-grid-bg border-2 border-white/50 flex items-center justify-center p-1">
          <svg
            viewBox="0 0 120 124"
            className={compact ? 'w-24 h-24' : 'w-36 h-36'}
            shapeRendering="crispEdges"
            aria-label={`Top-down robot visualization in ${modeDisplay} mode`}
          >
            {/* Cyan Forward Heading Arrow */}
            <line x1="60" y1="32" x2="60" y2="12" stroke="#22D3EE" strokeWidth="4" />
            <polygon points="60,4 50,16 70,16" fill="#22D3EE" />

            {/* Suspension / Axle Struts */}
            <rect x="30" y="36" width="60" height="5" fill="#475569" />
            <rect x="30" y="90" width="60" height="5" fill="#475569" />

            {/* Pixel Robot Chassis */}
            <rect x="40" y="28" width="40" height="72" fill="#94A3B8" stroke="#FFFFFF" strokeWidth="2" />
            <rect x="44" y="33" width="32" height="62" fill="#CBD5E1" />
            {/* Front Sensor Bar */}
            <rect x="46" y="28" width="28" height="5" fill="#0F0F23" />
            <rect x="52" y="29" width="16" height="3" fill="#38BDF8" />
            {/* Center LiDAR Turret */}
            <rect x="52" y="54" width="16" height="16" fill="#0F0F23" stroke="#FFFFFF" strokeWidth="1.5" />
            <rect x="57" y="59" width="6" height="6" fill="#00FF00" />

            {/* 4 Independently Steered Pixel Wheels */}
            {wheels.map(w => (
              <g key={w.label} transform={`translate(${w.x}, ${w.y}) rotate(${w.deg})`}>
                <rect x="-7" y="-14" width="14" height="28" fill="#1E293B" stroke="#FFFFFF" strokeWidth="2" />
                <rect x="-4" y="-11" width="8" height="22" fill="#00FF00" />
                {/* Pixel tire tread ticks */}
                <rect x="-7" y="-8" width="14" height="2" fill="#000000" />
                <rect x="-7" y="-1" width="14" height="2" fill="#000000" />
                <rect x="-7" y="6" width="14" height="2" fill="#000000" />
              </g>
            ))}
          </svg>
        </div>

        {compact ? (
          <div className="w-full text-center bg-[#0F0F23] border border-white/60 py-1 px-1">
            <div className="font-mono text-[8px] text-slate-300">MODE:</div>
            <div className="font-pixel text-[8px] text-[#FFFF00] truncate">{modeDisplay}</div>
          </div>
        ) : (
          <div className="w-full bg-[#0F0F23] border-2 border-white/60 px-2.5 py-1.5">
            <div className="font-pixel text-[8px] text-[#FFFF00] mb-1">STEER ANGLES:</div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 font-mono text-[10px] font-bold">
              <div>
                FL: <span className="text-[#00FF00]">{fmtDeg(fl)}</span>
              </div>
              <div>
                FR: <span className="text-[#00FF00]">{fmtDeg(fr)}</span>
              </div>
              <div>
                RL: <span className="text-[#00FF00]">{fmtDeg(rl)}</span>
              </div>
              <div>
                RR: <span className="text-[#00FF00]">{fmtDeg(rr)}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

