import React from 'react';
import { rosService } from '../services/rosService';
import { manualInputPipeline } from '../services/manualInputPipeline';
import { PixelShieldIcon, PixelWarningIcon } from './PixelIcons';
import { soundEffects } from '../utils/soundEffects';

interface EmergencyStopButtonProps {
  estopActive: boolean;
}

export const EmergencyStopButton: React.FC<EmergencyStopButtonProps> = ({ estopActive }) => {
  const handleToggleEstop = () => {
    if (estopActive) {
      soundEffects.playEstopReset();
      rosService.resetEmergencyStop();
    } else {
      manualInputPipeline.forceStopAll();
      soundEffects.playEstop();
      rosService.triggerEmergencyStop();
    }
  };

  return (
    <section
      aria-label="System Safety Interlock"
      className={`w-full border-2 border-white shadow-pixel px-2.5 sm:px-3 py-2 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 ${
        estopActive ? 'bg-[#6A0000] animate-pixel-blink' : 'bg-[#B80000]'
      }`}
    >
      {/* Left: Shield + Title + Armed/Latched Status + Hazard Stripes */}
      <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
        <PixelShieldIcon className="w-6 h-6 shrink-0" />
        <div className="flex flex-wrap items-center gap-2 min-w-0">
          <span className="font-pixel text-[9px] sm:text-[11px] text-white tracking-wide">
            SYSTEM SAFETY INTERLOCK
          </span>
          {estopActive ? (
            <span className="px-2 py-0.5 bg-[#FFFF00] text-black border-2 border-black font-pixel text-[8px] sm:text-[9px]">
              E-STOP ENGAGED
            </span>
          ) : (
            <span className="px-2 py-0.5 bg-[#00FF00] text-black border-2 border-black font-pixel text-[8px] sm:text-[9px]">
              ARMED &amp; READY
            </span>
          )}
        </div>
        <div
          className="hidden md:block flex-1 h-4 pixel-hazard-stripes max-w-[260px] ml-auto"
          aria-hidden="true"
        />
      </div>

      {/* Right: Prominent Emergency Stop / Reset Button */}
      <button
        type="button"
        onClick={handleToggleEstop}
        aria-pressed={estopActive}
        className={`pixel-btn px-4 py-2 sm:py-2.5 flex items-center justify-center gap-2 font-pixel text-[10px] sm:text-xs shrink-0 ${
          estopActive
            ? 'bg-[#00FF00] text-black border-black hover:bg-[#33FF33]'
            : 'bg-[#FF0000] text-white border-white hover:bg-[#FF2A2A]'
        }`}
      >
        <PixelWarningIcon className="w-4 h-4 sm:w-5 sm:h-5 shrink-0" />
        <span>{estopActive ? 'RESET E-STOP' : 'EMERGENCY STOP'}</span>
      </button>
    </section>
  );
};
