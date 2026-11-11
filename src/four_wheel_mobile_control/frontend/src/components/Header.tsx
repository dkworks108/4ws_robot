import React from 'react';
import { ConnectionStatus, ClockStatus, KeyboardControlState } from '../types/ros';
import { PixelRobotLogo, PixelSoundIcon } from './PixelIcons';
import { Menu, Settings, Sun, Moon, Box } from 'lucide-react';
import { soundEffects } from '../utils/soundEffects';

interface HeaderProps {
  status: ConnectionStatus;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  onOpenSettings: () => void;
  onToggleSidebar?: () => void;
  clockStatus: ClockStatus | null;
  latencyMs: number | null;
  fps: number;
  keyboardStatus: KeyboardControlState;
  sfxMuted: boolean;
  onToggleSfx: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  theme,
  onToggleTheme,
  onOpenSettings,
  onToggleSidebar,
  clockStatus,
  latencyMs,
  fps,
  keyboardStatus,
  sfxMuted,
  onToggleSfx,
}) => {
  const isConnected = status === 'connected';
  const simActive = clockStatus?.active ?? false;

  const connLabel =
    status === 'connected'
      ? 'CONNECTED'
      : status === 'connecting'
      ? 'CONNECTING'
      : status === 'error'
      ? 'ERR / RETRY'
      : 'OFFLINE';

  const connColor = isConnected
    ? 'border-[#00FF00] text-[#00FF00] bg-[#00FF00]/10'
    : status === 'connecting'
    ? 'border-[#FFFF00] text-[#FFFF00] bg-[#FFFF00]/10'
    : 'border-[#FF0000] text-[#FF0000] bg-[#FF0000]/15';

  const kbOn = keyboardStatus === 'ENABLED';

  return (
    <header
      className={`sticky top-0 z-40 border-b-2 ${
        theme === 'dark'
          ? 'bg-[#080818] border-white text-white'
          : 'bg-slate-200 border-black text-black'
      } px-2.5 sm:px-4 py-2`}
    >
      <div className="flex items-center justify-between gap-2">
        {/* Left: Menu + Pixel Robot Logo + Title */}
        <div className="flex items-center gap-2 min-w-0">
          {onToggleSidebar && (
            <button
              type="button"
              onClick={() => {
                soundEffects.playClick();
                onToggleSidebar();
              }}
              aria-label="Toggle Navigation Sidebar"
              className="hidden lg:flex items-center justify-center w-8 h-8 pixel-btn bg-[#11112B] text-white"
            >
              <Menu className="w-4 h-4" />
            </button>
          )}
          <PixelRobotLogo className="w-8 h-8 sm:w-9 sm:h-9 shrink-0" />
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="font-pixel text-[10px] sm:text-xs tracking-wide truncate">
                <span className="hidden sm:inline">4WS MOBILE ROBOT</span>
                <span className="sm:hidden">4WS ROBOT</span>
              </h1>
              <span className="font-pixel text-[9px] sm:text-[10px] text-[#FFFF00]">v1.0</span>
            </div>
            <p className="font-mono text-[9px] sm:text-[10px] opacity-80 truncate">
              FOUR-WHEEL STEERING &bull; ROS 2 HUMBLE
            </p>
          </div>
        </div>

        {/* Center/Right Telemetry Status Badges (Desktop) */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {/* Connection Status */}
          <div
            className={`px-2 py-1 border-2 ${connColor} font-pixel text-[8px] sm:text-[9px] flex items-center gap-1.5 shadow-pixel-sm`}
            role="status"
            aria-label={`ROS Connection: ${connLabel}`}
          >
            <span
              className={`w-2 h-2 inline-block ${
                isConnected
                  ? 'bg-[#00FF00]'
                  : status === 'connecting'
                  ? 'bg-[#FFFF00] animate-pulse'
                  : 'bg-[#FF0000]'
              }`}
            />
            <span>{connLabel}</span>
          </div>

          {/* Gazebo Sim Badge (Desktop/Tablet) */}
          <div
            className={`hidden md:flex items-center gap-1.5 px-2 py-1 border-2 font-mono text-[10px] font-bold shadow-pixel-sm ${
              simActive
                ? 'border-[#38BDF8] text-white bg-[#1028C8]/60'
                : 'border-slate-600 text-slate-400 bg-black/40'
            }`}
          >
            <Box className="w-3.5 h-3.5 text-[#38BDF8]" />
            <span>GAZEBO (SIM)</span>
          </div>

          {/* FPS & Latency (Desktop XL) */}
          <div className="hidden xl:flex items-center gap-2 px-2.5 py-1 border-2 border-white/70 bg-[#0F0F23] text-white font-mono text-[10px] font-bold shadow-pixel-sm">
            <span>FPS: {fps > 0 ? fps : '--'}</span>
            <span className="opacity-50">|</span>
            <span>LAT: {latencyMs !== null ? `${latencyMs} ms` : '--'}</span>
          </div>

          {/* Sound Effects Toggle */}
          <button
            type="button"
            onClick={onToggleSfx}
            aria-label={sfxMuted ? 'Unmute Sound Effects' : 'Mute Sound Effects'}
            title={sfxMuted ? 'Unmute Retro SFX' : 'Mute Retro SFX'}
            className={`p-1.5 pixel-btn ${
              theme === 'dark' ? 'bg-[#11112B] text-white' : 'bg-white text-black border-black'
            }`}
          >
            <PixelSoundIcon muted={sfxMuted} className="w-4 h-4" />
          </button>

          {/* Theme Toggle */}
          <button
            type="button"
            onClick={() => {
              soundEffects.playClick();
              onToggleTheme();
            }}
            aria-label={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Theme`}
            title="Toggle Theme"
            className={`hidden sm:flex p-1.5 pixel-btn ${
              theme === 'dark'
                ? 'bg-[#11112B] text-[#FFFF00]'
                : 'bg-white text-slate-900 border-black'
            }`}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* Settings Modal Trigger */}
          <button
            type="button"
            onClick={() => {
              soundEffects.playClick();
              onOpenSettings();
            }}
            aria-label="Open System & Keyboard Settings"
            title="Connection, Keyboard & Handedness Settings"
            className={`p-1.5 pixel-btn ${
              theme === 'dark' ? 'bg-[#11112B] text-white' : 'bg-white text-black border-black'
            }`}
          >
            <Settings className="w-4 h-4" />
          </button>

          {/* Keyboard Status Badge (Desktop) */}
          <button
            type="button"
            onClick={() => {
              soundEffects.playClick();
              onOpenSettings();
            }}
            aria-label={`Keyboard Control Status: ${keyboardStatus}`}
            title={`Keyboard Control: ${keyboardStatus}`}
            className={`hidden sm:flex px-2 py-1 border-2 font-pixel text-[9px] shadow-pixel-sm ${
              kbOn
                ? 'bg-[#0000FF] text-[#FFFF00] border-white'
                : 'bg-slate-800 text-slate-400 border-slate-500'
            }`}
          >
            KB
          </button>
        </div>
      </div>
    </header>
  );
};
