import React from 'react';
import { OperatingMode } from '../types/ros';
import { rosService } from '../services/rosService';
import { manualInputPipeline } from '../services/manualInputPipeline';
import { PixelGamepadIcon, PixelNavIcon, PixelExploreIcon } from './PixelIcons';
import { soundEffects } from '../utils/soundEffects';

interface OperatingModeSelectorProps {
  currentMode: OperatingMode;
  estopActive: boolean;
  compact?: boolean;
}

export const OperatingModeSelector: React.FC<OperatingModeSelectorProps> = ({
  currentMode,
  estopActive,
  compact = false,
}) => {
  const modes: Array<{
    id: OperatingMode;
    label: string;
    icon: React.ReactNode;
  }> = [
    { id: 'MANUAL', label: 'MANUAL', icon: <PixelGamepadIcon className="w-4 h-4 sm:w-5 sm:h-5" /> },
    { id: 'AUTONOMOUS_NAV', label: 'NAV2', icon: <PixelNavIcon className="w-4 h-4 sm:w-5 sm:h-5" /> },
    { id: 'AUTONOMOUS_EXPLORE', label: 'EXPLORE', icon: <PixelExploreIcon className="w-4 h-4 sm:w-5 sm:h-5" /> },
  ];

  const handleSelectMode = (mode: OperatingMode) => {
    if (estopActive) return;
    if (mode !== 'MANUAL') {
      manualInputPipeline.forceStopAll();
    }
    soundEffects.playAuthorityChange();
    rosService.setOperatingMode(mode);
  };

  if (compact) {
    return (
      <div className="grid grid-cols-3 gap-2" role="group" aria-label="Control Authority">
        {modes.map(m => {
          const isActive = currentMode === m.id;
          return (
            <button
              key={m.id}
              type="button"
              onClick={() => handleSelectMode(m.id)}
              disabled={estopActive}
              aria-pressed={isActive}
              className={`pixel-btn py-2 px-2 flex flex-col items-center justify-center gap-1 font-pixel text-[9px] ${
                isActive
                  ? 'bg-[#FFFF00] text-black border-black'
                  : 'bg-[#080818] text-white border-white hover:bg-[#141436]'
              } ${estopActive ? 'opacity-40 cursor-not-allowed' : ''}`}
            >
              {m.icon}
              <span>{m.label}</span>
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="pixel-panel bg-[#080818]">
      <div className="pixel-header px-3 py-1.5 flex items-center justify-between">
        <span className="font-pixel text-[9px] text-white tracking-wider">CONTROL AUTHORITY</span>
      </div>
      <div className="p-2.5 grid grid-cols-3 gap-2" role="group" aria-label="Control Authority">
        {modes.map(m => {
          const isActive = currentMode === m.id;
          return (
            <button
              key={m.id}
              type="button"
              onClick={() => handleSelectMode(m.id)}
              disabled={estopActive}
              aria-pressed={isActive}
              className={`pixel-btn py-2.5 px-1.5 flex flex-col items-center justify-center gap-1.5 font-pixel text-[8px] ${
                isActive
                  ? 'bg-[#FFFF00] text-black border-black'
                  : 'bg-[#0F0F23] text-white border-white hover:bg-[#191944]'
              } ${estopActive ? 'opacity-40 cursor-not-allowed' : ''}`}
            >
              {m.icon}
              <span>{m.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
