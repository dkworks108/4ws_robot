import React from 'react';
import { SteeringMode } from '../types/ros';
import { rosService } from '../services/rosService';
import { PixelSteeringDiagram } from './PixelIcons';
import { soundEffects } from '../utils/soundEffects';
import { ChevronLeft, ChevronRight, Compass } from 'lucide-react';

export interface SteeringModeMeta {
  id: SteeringMode;
  shortLabel: string;
  title: string;
  description: string;
}

export const STEERING_MODES: SteeringModeMeta[] = [
  {
    id: 'front_steer',
    shortLabel: 'A. ACKERMANN',
    title: 'A. ACKERMANN',
    description: 'Front steer, rear locked',
  },
  {
    id: 'four_wheel_steer',
    shortLabel: 'B. 4WS COUNTER',
    title: 'B. 4WS COUNTER',
    description: 'Front & rear opposite',
  },
  {
    id: 'crab',
    shortLabel: 'C. CRAB STEER',
    title: 'C. CRAB STEER',
    description: 'All wheels parallel',
  },
  {
    id: 'generalized',
    shortLabel: 'D. SWERVE',
    title: 'D. SWERVE',
    description: 'Arbitrary instantaneous',
  },
  {
    id: 'in_place_spin',
    shortLabel: 'E. IN-PLACE SPIN',
    title: 'E. IN-PLACE SPIN',
    description: 'All wheels tangent to center',
  },
];

export function getSteeringModeMeta(mode: SteeringMode): SteeringModeMeta {
  return STEERING_MODES.find(m => m.id === mode) || STEERING_MODES[1];
}

interface SteeringModeSelectorProps {
  currentMode: SteeringMode;
  variant?: 'desktop' | 'mobile';
}

export const SteeringModeSelector: React.FC<SteeringModeSelectorProps> = ({
  currentMode,
  variant = 'desktop',
}) => {
  const handleSelect = (mode: SteeringMode) => {
    soundEffects.playModeChange();
    rosService.setSteeringMode(mode);
  };

  if (variant === 'mobile') {
    const idx = Math.max(
      0,
      STEERING_MODES.findIndex(m => m.id === currentMode)
    );
    const current = STEERING_MODES[idx];

    const step = (delta: number) => {
      const next = STEERING_MODES[(idx + delta + STEERING_MODES.length) % STEERING_MODES.length];
      handleSelect(next.id);
    };

    return (
      <div className="pixel-panel bg-[#080818] flex flex-col">
        <div className="pixel-header px-2 py-1 flex items-center gap-1.5">
          <Compass className="w-3.5 h-3.5 text-white shrink-0" />
          <span className="font-pixel text-[8px] text-white truncate">STEER MODE (4WS)</span>
        </div>
        <div className="p-1.5 flex items-center justify-between gap-1 flex-1">
          <button
            type="button"
            onClick={() => step(-1)}
            aria-label="Previous steering mode"
            className="pixel-btn bg-[#11112B] text-white p-1.5 min-w-[30px] min-h-[36px] flex items-center justify-center"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <div className="flex flex-col items-center text-center min-w-0 px-1">
            <span className="font-mono text-[11px] font-extrabold text-[#FFFF00] truncate max-w-full">
              {current.shortLabel}
            </span>
            <span className="font-mono text-[9px] text-slate-300 truncate max-w-full">
              {current.description}
            </span>
          </div>
          <button
            type="button"
            onClick={() => step(1)}
            aria-label="Next steering mode"
            className="pixel-btn bg-[#11112B] text-white p-1.5 min-w-[30px] min-h-[36px] flex items-center justify-center"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="pixel-panel bg-[#080818]">
      <div className="pixel-header px-3 py-1.5 flex items-center justify-between">
        <span className="font-pixel text-[9px] text-white tracking-wider">STEERING MODE (4WS)</span>
      </div>
      <div className="p-2 space-y-1.5" role="radiogroup" aria-label="Four-Wheel Steering Modes">
        {STEERING_MODES.map(m => {
          const isActive = currentMode === m.id;
          return (
            <button
              key={m.id}
              type="button"
              role="radio"
              aria-checked={isActive}
              onClick={() => handleSelect(m.id)}
              className={`w-full text-left px-2.5 py-1.5 border-2 flex items-center gap-2.5 transition-colors ${
                isActive
                  ? 'bg-[#00FF00] text-black border-white shadow-pixel-sm'
                  : 'bg-[#0F0F23] text-white border-white/60 hover:border-[#FFFF00] hover:bg-[#171738]'
              }`}
            >
              {/* Radio indicator */}
              <span
                className={`w-3.5 h-3.5 border-2 flex items-center justify-center shrink-0 ${
                  isActive ? 'border-black bg-black' : 'border-white bg-transparent'
                }`}
              >
                {isActive && <span className="w-1.5 h-1.5 bg-[#00FF00]" />}
              </span>

              <PixelSteeringDiagram mode={m.id} active={isActive} />

              <div className="min-w-0 flex-1">
                <div className="font-mono text-[11px] font-extrabold leading-tight truncate">
                  {m.title}
                </div>
                <div
                  className={`font-mono text-[9px] leading-tight truncate ${
                    isActive ? 'text-black/80 font-bold' : 'text-slate-300'
                  }`}
                >
                  {m.description}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
