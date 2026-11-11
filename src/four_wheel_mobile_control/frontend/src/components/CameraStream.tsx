import React, { useState } from 'react';
import { Video, VideoOff, Maximize2, RefreshCw } from 'lucide-react';

interface CameraStreamProps {
  host: string;
  port: number;
  topic: string;
  onStatusChange?: (active: boolean) => void;
}

export const CameraStream: React.FC<CameraStreamProps> = ({
  host,
  port,
  topic,
  onStatusChange
}) => {
  const [isEnabled, setIsEnabled] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const streamUrl = `http://${host}:${port}/stream?topic=${topic}&type=mjpeg&width=640&height=480&quality=80`;

  const handleReload = () => {
    setHasError(false);
    setReloadKey(prev => prev + 1);
  };

  return (
    <div className={`w-full bg-gray-950 p-3 rounded-2xl border border-gray-800 ${isFullscreen ? 'fixed inset-2 z-50 flex flex-col justify-between' : ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono font-bold text-gray-400 tracking-wider flex items-center gap-1.5">
          <Video className="w-3.5 h-3.5 text-cyan-400" /> ONBOARD RGB CAMERA
        </span>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setIsEnabled(!isEnabled)}
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold flex items-center gap-1 transition ${
              isEnabled ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'bg-gray-800 text-gray-400'
            }`}
          >
            {isEnabled ? 'STREAMING' : 'PAUSED'}
          </button>
          <button
            onClick={handleReload}
            className="p-1 rounded bg-gray-800 text-gray-400 hover:text-white"
            title="Reload Video Stream"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1 rounded bg-gray-800 text-gray-400 hover:text-white"
            title="Toggle Fullscreen"
          >
            <Maximize2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Video Stream Container */}
      <div className="relative w-full aspect-video rounded-xl bg-black overflow-hidden flex items-center justify-center border border-gray-800/80">
        {isEnabled ? (
          !hasError ? (
            <img
              key={reloadKey}
              src={streamUrl}
              alt="Live RGB Camera Stream"
              onLoad={() => {
                setHasError(false);
                onStatusChange?.(true);
              }}
              onError={() => {
                setHasError(true);
                onStatusChange?.(false);
              }}
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="flex flex-col items-center justify-center text-center p-4">
              <VideoOff className="w-8 h-8 text-gray-600 mb-2" />
              <div className="text-xs font-mono font-bold text-gray-400">CAMERA FEED UNAVAILABLE</div>
              <div className="text-[10px] text-gray-500 mt-1">
                Checking topic: <code className="text-cyan-400">{topic}</code>
              </div>
              <button
                onClick={handleReload}
                className="mt-3 px-3 py-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-mono font-bold transition"
              >
                RECONNECT
              </button>
            </div>
          )
        ) : (
          <div className="flex flex-col items-center justify-center text-gray-600">
            <VideoOff className="w-8 h-8 mb-1" />
            <span className="text-xs font-mono">STREAM PAUSED TO SAVE BANDWIDTH</span>
          </div>
        )}

        {/* Video Overlay HUD */}
        {isEnabled && !hasError && (
          <div className="absolute top-2 left-2 flex items-center gap-1.5 px-2 py-0.5 rounded bg-black/60 backdrop-blur-sm border border-white/10 text-[9px] font-mono text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            LIVE MJPEG &bull; 640x480 &bull; 30 FPS
          </div>
        )}
      </div>
    </div>
  );
};

