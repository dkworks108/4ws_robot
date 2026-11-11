import React from 'react';
import { ExplorationCoverage, OperatingMode } from '../types/ros';
import { rosService } from '../services/rosService';
import { manualInputPipeline } from '../services/manualInputPipeline';
import { Crosshair, Play, Pause, Square, Navigation, Layers } from 'lucide-react';
import { soundEffects } from '../utils/soundEffects';

interface NavExplorePanelProps {
  operatingMode: OperatingMode;
  estopActive: boolean;
  explorationStatus: string;
  coverage: ExplorationCoverage | null;
  selectedGoal: { x: number; y: number } | null;
  onClearGoal: () => void;
  onTogglePickGoal?: () => void;
}

export const NavExplorePanel: React.FC<NavExplorePanelProps> = ({
  operatingMode,
  estopActive,
  explorationStatus,
  coverage,
  selectedGoal,
  onClearGoal,
  onTogglePickGoal,
}) => {
  const navLabel =
    estopActive
      ? 'E-STOP LOCKED'
      : operatingMode === 'AUTONOMOUS_NAV'
      ? 'Navigating'
      : 'Idle';

  const isPaused = explorationStatus === 'PAUSED';

  const handleSendGoal = () => {
    if (estopActive) return;
    if (selectedGoal) {
      manualInputPipeline.forceStopAll();
      soundEffects.playGoalDispatch();
      rosService.sendNavigationGoal(selectedGoal.x, selectedGoal.y);
    } else if (onTogglePickGoal) {
      soundEffects.playClick();
      onTogglePickGoal();
    }
  };

  const handleCancelNav = () => {
    soundEffects.playClick();
    rosService.cancelNavigationGoal();
    onClearGoal();
  };

  return (
    <div className="pixel-panel bg-[#080818] flex flex-col justify-between h-full">
      <div className="pixel-header px-2.5 py-1 flex items-center justify-between gap-1">
        <span className="font-pixel text-[8px] sm:text-[9px] text-white flex items-center gap-1.5 truncate">
          <Navigation className="w-3.5 h-3.5 shrink-0" />
          <span>NAVIGATION &amp; EXPLORATION</span>
        </span>
      </div>

      <div className="p-2.5 space-y-2.5 flex-1 flex flex-col justify-between">
        {/* Nav2 Row */}
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="font-mono text-[11px] font-bold flex items-center gap-1.5 min-w-0">
            <Navigation className="w-3.5 h-3.5 text-[#38BDF8] shrink-0" />
            <span className="text-slate-300">NAV2:</span>
            <span className="text-white truncate">
              {selectedGoal ? `Goal (${selectedGoal.x}, ${selectedGoal.y})` : navLabel}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={estopActive}
              onClick={handleSendGoal}
              className={`pixel-btn px-2.5 py-1 font-pixel text-[8px] flex items-center gap-1 ${
                selectedGoal
                  ? 'bg-[#FFFF00] text-black border-black'
                  : 'bg-[#0000FF] text-white border-white hover:bg-[#1E40FF]'
              } ${estopActive ? 'opacity-40 cursor-not-allowed' : ''}`}
            >
              <Crosshair className="w-3 h-3" />
              <span>{selectedGoal ? 'SEND GOAL' : 'SET GOAL'}</span>
            </button>

            {(selectedGoal || operatingMode === 'AUTONOMOUS_NAV') && (
              <button
                type="button"
                onClick={handleCancelNav}
                className="pixel-btn px-2 py-1 bg-[#11112B] text-[#FF0000] border-white font-pixel text-[8px]"
              >
                CANCEL
              </button>
            )}
          </div>
        </div>

        {/* Exploration Status + Coverage */}
        <div className="space-y-1.5 bg-[#0F0F23] border-2 border-white/50 p-2">
          <div className="flex items-center justify-between gap-2 font-mono text-[10px] font-bold">
            <span className="flex items-center gap-1.5 text-slate-200">
              <Layers className="w-3.5 h-3.5 text-[#00FF00]" />
              EXPLORATION: <span className="text-[#FFFF00]">{explorationStatus || 'READY'}</span>
            </span>
            <span className="text-[#00FF00]">
              {coverage ? `${coverage.explored_pct}% (${coverage.goals_completed} goals)` : '0%'}
            </span>
          </div>

          <div className="w-full h-2.5 bg-[#080818] border border-white/60 overflow-hidden">
            <div
              className="h-full bg-[#00FF00] transition-all duration-300"
              style={{ width: `${Math.min(100, coverage?.explored_pct || 0)}%` }}
            />
          </div>
        </div>

        {/* Arcade Action Buttons: START / PAUSE-RESUME / STOP */}
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            disabled={estopActive}
            onClick={() => {
              manualInputPipeline.forceStopAll();
              soundEffects.playGoalDispatch();
              rosService.startExploration();
            }}
            className={`pixel-btn py-2 px-1 bg-[#00FF00] text-black border-black font-pixel text-[8px] flex items-center justify-center gap-1 ${
              estopActive ? 'opacity-40 cursor-not-allowed' : 'hover:bg-[#33FF33]'
            }`}
          >
            <Play className="w-3.5 h-3.5" />
            <span>START</span>
          </button>

          <button
            type="button"
            disabled={estopActive}
            onClick={() => {
              soundEffects.playClick();
              if (isPaused) {
                manualInputPipeline.forceStopAll();
                rosService.resumeExploration();
              } else {
                rosService.pauseExploration();
              }
            }}
            className={`pixel-btn py-2 px-1 bg-[#FFFF00] text-black border-black font-pixel text-[8px] flex items-center justify-center gap-1 ${
              estopActive ? 'opacity-40 cursor-not-allowed' : 'hover:bg-[#FFF04D]'
            }`}
          >
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            <span>{isPaused ? 'RESUME' : 'PAUSE'}</span>
          </button>

          <button
            type="button"
            onClick={() => {
              soundEffects.playKeyStop();
              rosService.stopExploration();
            }}
            className="pixel-btn py-2 px-1 bg-[#FF0000] text-white border-white font-pixel text-[8px] flex items-center justify-center gap-1 hover:bg-[#FF3333]"
          >
            <Square className="w-3.5 h-3.5" />
            <span>STOP</span>
          </button>
        </div>
      </div>
    </div>
  );
};

