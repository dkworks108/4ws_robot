import React from 'react';
import { Gauge } from 'lucide-react';
import { soundEffects } from '../utils/soundEffects';

interface SpeedLimitControlProps {
  speedLimit: number;
  disabled?: boolean;
  onChange: (limit: number) => void;
  compact?: boolean;
}

export const SpeedLimitControl: React.FC<SpeedLimitControlProps> = ({
  speedLimit,
  disabled = false,
  onChange,
  compact = false,
}) => {
  const pct = Math.round(speedLimit * 100);
  const totalSegments = 10;
  const filledSegments = Math.round((pct / 100) * totalSegments);

  const handleSelect = (val: number) => {
    if (disabled) return;
    soundEffects.playClick();
    onChange(val);
  };

  return (
    <div className="pixel-panel bg-[#080818] flex flex-col">
      <div className="pixel-header px-2.5 py-1 flex items-center justify-between gap-1">
        <span className="font-pixel text-[8px] sm:text-[9px] text-white flex items-center gap-1.5">
          <Gauge className="w-3.5 h-3.5 shrink-0" />
          <span>{compact ? 'SPEED' : 'SPEED LIMIT'}</span>
        </span>
        <span className="font-pixel text-[9px] sm:text-[10px] text-[#FFFF00]">{pct}%</span>
      </div>

      <div className={compact ? 'p-1.5 space-y-1.5' : 'p-2.5 space-y-2'}>
        {/* Segmented Green Bar */}
        <div
          className="grid grid-cols-10 gap-1 p-1 bg-[#0F0F23] border-2 border-white/60"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={25}
          aria-valuemax={100}
          aria-label="Speed limit percentage"
        >
          {Array.from({ length: totalSegments }).map((_, i) => (
            <div
              key={i}
              className={`h-3 sm:h-3.5 border border-black ${
                i < filledSegments ? 'bg-[#00FF00]' : 'bg-slate-800'
              }`}
            />
          ))}
        </div>

        {/* Preset Buttons */}
        <div className="grid grid-cols-4 gap-1" role="group" aria-label="Speed limit presets">
          {[0.25, 0.5, 0.75, 1.0].map(val => {
            const active = Math.abs(speedLimit - val) < 0.02;
            return (
              <button
                key={val}
                type="button"
                disabled={disabled}
                onClick={() => handleSelect(val)}
                aria-pressed={active}
                className={`pixel-btn py-1 font-mono text-[10px] sm:text-xs font-extrabold ${
                  active
                    ? 'bg-[#FFFF00] text-black border-black'
                    : 'bg-[#11112B] text-white border-white hover:bg-[#1E1E4A]'
                } ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
              >
                {Math.round(val * 100)}%
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

