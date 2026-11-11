import React from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';
import { rosService } from '../services/rosService';

interface EmergencyStopButtonProps {
  estopActive: boolean;
}

export const EmergencyStopButton: React.FC<EmergencyStopButtonProps> = ({ estopActive }) => {
  const handleTriggerEstop = () => {
    rosService.triggerEmergencyStop();
  };

  const handleResetEstop = () => {
    rosService.resetEmergencyStop();
  };

  return (
    <div className="w-full flex flex-col items-center justify-center p-3 rounded-2xl bg-gray-950 border-2 border-amber-500/40 relative overflow-hidden shadow-2xl">
      {/* Caution hazard striped background header */}
      <div className="absolute top-0 inset-x-0 h-2 bg-gradient-to-r from-amber-500 via-yellow-400 to-amber-500" />

      <div className="w-full flex items-center justify-between mb-2">
        <span className="text-[11px] font-mono tracking-wider font-bold text-amber-400 flex items-center gap-1">
          <AlertOctagon className="w-3.5 h-3.5" /> SYSTEM SAFETY INTERLOCK
        </span>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${estopActive ? 'bg-rose-500 text-white animate-pulse' : 'bg-gray-800 text-gray-400'}`}>
          {estopActive ? 'LATCHED (STOPPED)' : 'ARMED & READY'}
        </span>
      </div>

      {!estopActive ? (
        <button
          onClick={handleTriggerEstop}
          className="w-full py-4 px-6 rounded-xl bg-gradient-to-b from-rose-500 to-red-700 hover:from-rose-600 hover:to-red-800 active:scale-95 text-white font-black tracking-widest text-base sm:text-lg flex items-center justify-center gap-2 shadow-[0_0_25px_rgba(244,63,94,0.4)] transition-all duration-150 border-2 border-red-400/50"
        >
          <AlertOctagon className="w-6 h-6 animate-pulse" />
          EMERGENCY STOP
        </button>
      ) : (
        <div className="w-full flex flex-col sm:flex-row items-center gap-2">
          <div className="flex-1 w-full py-2.5 px-3 rounded-xl bg-rose-950/80 border border-rose-500/60 text-rose-300 text-xs font-mono font-bold flex items-center justify-center gap-1.5 animate-pulse text-center">
            <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0" />
            MOTION INHIBITED (E-STOP ACTIVE)
          </div>
          <button
            onClick={handleResetEstop}
            className="w-full sm:w-auto py-2.5 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white text-xs font-bold font-mono tracking-wider flex items-center justify-center gap-1.5 shadow-lg transition-all"
          >
            <RotateCcw className="w-4 h-4" />
            RESET E-STOP
          </button>
        </div>
      )}

      <div className="mt-2 text-[10px] text-gray-400 font-mono text-center">
        Zeroes all velocity &bull; Cancels Nav2 goals &bull; Inhibits kinematics
      </div>
    </div>
  );
};

