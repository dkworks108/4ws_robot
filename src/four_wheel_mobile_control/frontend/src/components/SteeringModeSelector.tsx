import React from 'react';
import { SteeringMode } from '../types/ros';
import { rosService } from '../services/rosService';

interface SteeringModeSelectorProps {
  currentMode: SteeringMode;
  linearVel: number;
}

export const SteeringModeSelector: React.FC<SteeringModeSelectorProps> = ({
  currentMode,
  linearVel
}) => {
  const modes: Array<{
    id: SteeringMode;
    label: string;
    sub: string;
    tag: string;
    desc: string;
  }> = [
    {
      id: 'front_steer',
      label: 'Ackermann',
      sub: 'Mode A',
      tag: 'Front Only',
      desc: 'Rear wheels locked straight; front axle steers.'
    },
    {
      id: 'four_wheel_steer',
      label: '4WS Counter',
      sub: 'Mode B',
      tag: 'Tight Radius',
      desc: 'Front and rear steer in opposite directions for minimum turning radius.'
    },
    {
      id: 'crab',
      label: 'Crab Steer',
      sub: 'Mode C',
      tag: 'Diagonal',
      desc: 'All 4 wheels steer parallel for pure diagonal / lateral translation.'
    },
    {
      id: 'generalized',
      label: 'Swerve',
      sub: 'Mode D',
      tag: 'Holonomic',
      desc: 'Arbitrary instantaneous center of rotation (Vx, Vy, Wz).'
    },
    {
      id: 'in_place_spin',
      label: 'In-Place Spin',
      sub: 'Mode E',
      tag: 'Zero Radius',
      desc: 'All wheels aligned tangent to center circle for pure yaw rotation.'
    }
  ];

  const handleSelectMode = (mode: SteeringMode) => {
    rosService.setSteeringMode(mode);
  };

  const isMoving = Math.abs(linearVel) > 0.15;

  return (
    <div className="w-full bg-gray-950 p-3 rounded-2xl border border-gray-800">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono font-bold text-gray-400 tracking-wider">
          4WS KINEMATIC STEERING MODES
        </span>
        {isMoving && (
          <span className="text-[10px] font-mono text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-500/40">
            MOVING: Auto-Decelerating
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {modes.map(m => {
          const isActive = currentMode === m.id;
          return (
            <button
              key={m.id}
              onClick={() => handleSelectMode(m.id)}
              className={`p-2 rounded-xl border flex flex-col items-center justify-center text-center transition-all ${
                isActive
                  ? 'bg-gradient-to-b from-cyan-900/50 to-blue-900/50 border-cyan-400 text-white shadow-[0_0_12px_rgba(6,182,212,0.3)]'
                  : 'bg-gray-900 border-gray-800 text-gray-400 hover:bg-gray-800/80 hover:text-gray-200'
              } active:scale-95`}
            >
              <div className="flex items-center justify-between w-full mb-1">
                <span className={`text-[9px] font-mono font-bold ${isActive ? 'text-cyan-400' : 'text-gray-400'}`}>
                  {m.sub}
                </span>
                <span className="text-[8px] bg-gray-800 px-1 py-0.2 rounded text-gray-400 font-mono">
                  {m.tag}
                </span>
              </div>
              <span className="text-xs font-bold font-mono tracking-tight text-white mb-0.5">
                {m.label}
              </span>
              <span className="text-[8px] text-gray-400 line-clamp-1">{m.desc}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

