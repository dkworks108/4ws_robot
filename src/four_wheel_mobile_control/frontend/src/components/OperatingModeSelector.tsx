import React from 'react';
import { OperatingMode } from '../types/ros';
import { Gamepad2, Navigation, Compass, Lock } from 'lucide-react';
import { rosService } from '../services/rosService';

interface OperatingModeSelectorProps {
  currentMode: OperatingMode;
  estopActive: boolean;
}

export const OperatingModeSelector: React.FC<OperatingModeSelectorProps> = ({
  currentMode,
  estopActive
}) => {
  const modes: Array<{
    id: OperatingMode;
    label: string;
    sublabel: string;
    icon: React.ReactNode;
  }> = [
    {
      id: 'MANUAL',
      label: 'Manual',
      sublabel: 'Virtual Joystick',
      icon: <Gamepad2 className="w-4 h-4" />
    },
    {
      id: 'AUTONOMOUS_NAV',
      label: 'Nav2',
      sublabel: 'Point & Click Goal',
      icon: <Navigation className="w-4 h-4" />
    },
    {
      id: 'AUTONOMOUS_EXPLORE',
      label: 'Exploration',
      sublabel: 'Frontier Mapper',
      icon: <Compass className="w-4 h-4" />
    }
  ];

  const handleSelectMode = (mode: OperatingMode) => {
    if (estopActive) return;
    rosService.setOperatingMode(mode);
  };

  return (
    <div className="w-full bg-gray-950 p-3 rounded-2xl border border-gray-800">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono font-bold text-gray-400 tracking-wider">
          COMMAND ARBITER AUTHORITY
        </span>
        <span className="text-[11px] font-mono text-cyan-400 font-semibold">
          ACTIVE: {currentMode}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {modes.map(m => {
          const isActive = currentMode === m.id;
          const isDisabled = estopActive;

          return (
            <button
              key={m.id}
              onClick={() => handleSelectMode(m.id)}
              disabled={isDisabled}
              className={`p-2.5 rounded-xl border flex flex-col items-center justify-center text-center transition-all ${
                isActive
                  ? 'bg-cyan-500/20 border-cyan-400 text-white shadow-[0_0_15px_rgba(6,182,212,0.25)]'
                  : 'bg-gray-900 border-gray-800 text-gray-400 hover:bg-gray-800/80 hover:text-gray-200'
              } ${isDisabled ? 'opacity-40 cursor-not-allowed' : 'active:scale-95'}`}
            >
              <div className={`mb-1 ${isActive ? 'text-cyan-400' : 'text-gray-400'}`}>
                {isDisabled ? <Lock className="w-4 h-4 text-rose-400" /> : m.icon}
              </div>
              <span className="text-xs font-bold font-mono tracking-tight">{m.label}</span>
              <span className="text-[9px] text-gray-400 truncate max-w-full">{m.sublabel}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

