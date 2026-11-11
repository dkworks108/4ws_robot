import React from 'react';
import { ActiveKeysState, KeyboardControlState } from '../types/ros';
import { manualInputPipeline } from '../services/manualInputPipeline';
import { Keyboard } from 'lucide-react';
import { soundEffects } from '../utils/soundEffects';

interface KeyboardControlPanelProps {
  activeKeys: ActiveKeysState;
  keyboardStatus: KeyboardControlState;
  keyboardEnabled: boolean;
  sensitivity: number;
}

export const KeyboardControlPanel: React.FC<KeyboardControlPanelProps> = ({
  activeKeys,
  keyboardStatus,
  keyboardEnabled,
  sensitivity,
}) => {
  const statusColors: Record<KeyboardControlState, string> = {
    ENABLED: 'bg-[#00FF00] text-black border-black',
    DISABLED: 'bg-slate-700 text-slate-200 border-white/50',
    'MANUAL AUTHORITY REQUIRED': 'bg-[#FFFF00] text-black border-black',
    DISCONNECTED: 'bg-[#FF0000] text-white border-white',
    'WINDOW UNFOCUSED': 'bg-amber-400 text-black border-black',
  };

  const renderKey = (label: string, pressed: boolean, title: string) => (
    <div
      title={title}
      className={`w-7 h-7 border-2 flex items-center justify-center font-pixel text-[9px] select-none ${
        pressed
          ? 'bg-[#FFFF00] text-black border-black translate-x-[1px] translate-y-[1px]'
          : 'bg-[#11112B] text-white border-white/80 shadow-pixel-sm'
      }`}
    >
      {label}
    </div>
  );

  return (
    <div className="bg-[#0F0F23] border-2 border-white/70 p-2 space-y-2">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-1.5">
          <Keyboard className="w-3.5 h-3.5 text-[#FFFF00]" />
          <span className="font-pixel text-[8px] text-white">KEYBOARD ({Math.round(sensitivity * 100)}%)</span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className={`px-1.5 py-0.5 border font-mono text-[9px] font-extrabold ${statusColors[keyboardStatus]}`}>
            {keyboardStatus}
          </span>
          <button
            type="button"
            onClick={() => {
              soundEffects.playClick();
              manualInputPipeline.setKeyboardEnabled(!keyboardEnabled);
            }}
            aria-pressed={keyboardEnabled}
            className={`pixel-btn px-2 py-0.5 font-mono text-[9px] font-extrabold ${
              keyboardEnabled ? 'bg-[#0000FF] text-white' : 'bg-slate-800 text-slate-300'
            }`}
          >
            {keyboardEnabled ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      {/* Keycaps + Quick Legend */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1">
            {renderKey('Q', activeKeys.q, 'Q: Rotate CCW')}
            {renderKey('W', activeKeys.w, 'W: Forward')}
            {renderKey('E', activeKeys.e, 'E: Rotate CW')}
          </div>
          <div className="flex items-center gap-1">
            {renderKey('A', activeKeys.a, 'A: Left')}
            {renderKey('S', activeKeys.s, 'S: Reverse')}
            {renderKey('D', activeKeys.d, 'D: Right')}
          </div>
        </div>

        <div className="flex-1 flex flex-col gap-1 items-end">
          <div
            className={`px-2.5 py-1 border-2 font-pixel text-[8px] ${
              activeKeys.space
                ? 'bg-[#FF0000] text-white border-white'
                : 'bg-[#11112B] text-slate-200 border-white/70'
            }`}
          >
            SPACE: STOP
          </div>
          <span className="font-mono text-[9px] text-slate-300 text-right">
            WASD Move &bull; Q/E Yaw
          </span>
        </div>
      </div>
    </div>
  );
};

