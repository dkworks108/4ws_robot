import React from 'react';
import { ConnectionStatus } from '../types/ros';
import { Wifi, WifiOff, Settings, Sun, Moon, ShieldAlert, Cpu } from 'lucide-react';

interface HeaderProps {
  status: ConnectionStatus;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  onOpenSettings: () => void;
  estopActive: boolean;
  activeMode: string;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  theme,
  onToggleTheme,
  onOpenSettings,
  estopActive,
  activeMode
}) => {
  const getStatusBadge = () => {
    switch (status) {
      case 'connected':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            ONLINE
          </span>
        );
      case 'connecting':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            CONNECTING
          </span>
        );
      case 'error':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/40">
            <WifiOff className="w-3.5 h-3.5" />
            ERR
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-gray-500/20 text-gray-400 border border-gray-500/40">
            <WifiOff className="w-3.5 h-3.5" />
            OFFLINE
          </span>
        );
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-gray-900/80 dark:bg-gray-900/90 border-b border-gray-800 px-3 py-2.5 sm:px-6">
      <div className="flex items-center justify-between gap-2 max-w-7xl mx-auto">
        {/* Brand & Robot Identifier */}
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Cpu className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm sm:text-base font-bold tracking-tight text-white flex items-center gap-1.5">
                4WS ROBOT <span className="text-cyan-400 text-xs font-mono font-normal">v1.0</span>
              </h1>
              {getStatusBadge()}
            </div>
            <div className="text-[10px] text-gray-400 font-mono">
              MODE: <span className="text-cyan-400 font-bold">{activeMode}</span>
              {estopActive && <span className="ml-2 text-rose-400 font-bold flex-inline items-center">🚨 ESTOP</span>}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          {estopActive && (
            <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded bg-rose-600/30 border border-rose-500 text-rose-300 text-xs font-bold animate-pulse">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              EMERGENCY STOP
            </div>
          )}

          <button
            onClick={onToggleTheme}
            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white transition"
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-cyan-400" />}
          </button>

          <button
            onClick={onOpenSettings}
            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white transition"
            aria-label="Connection Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};

