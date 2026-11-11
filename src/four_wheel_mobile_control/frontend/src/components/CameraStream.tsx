import React, { useState } from 'react';
import { Video, VideoOff, Maximize2, RefreshCw } from 'lucide-react';
import { soundEffects } from '../utils/soundEffects';

interface CameraStreamProps {
  host: string;
  port: number;
  topic: string;
  compact?: boolean;
  onStatusChange?: (active: boolean) => void;
  onClickPreview?: () => void;
}

export const CameraStream: React.FC<CameraStreamProps> = ({
  host,
  port,
  topic,
  compact = false,
  onStatusChange,
  onClickPreview,
}) => {
  const [isEnabled, setIsEnabled] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const streamUrl = `http://${host}:${port}/stream?topic=${topic}&type=mjpeg&width=640&height=480&quality=80`;

  const handleReload = () => {
    soundEffects.playClick();
    setHasError(false);
    setReloadKey(prev => prev + 1);
  };

  const isLive = isEnabled && !hasError;

  return (
    <div
      className={`pixel-panel bg-[#080818] flex flex-col ${
        isFullscreen ? 'fixed inset-2 z-50' : ''
      }`}
    >
      {/* Header */}
      <div className="pixel-header px-2.5 py-1 flex items-center justify-between gap-1">
        <span className="font-pixel text-[8px] sm:text-[9px] text-white flex items-center gap-1.5 truncate">
          <Video className="w-3.5 h-3.5 shrink-0" />
          <span>RGB CAMERA</span>
        </span>
        <div className="flex items-center gap-1">
          <span
            className={`px-1.5 py-0.5 border font-pixel text-[7px] ${
              isLive
                ? 'bg-[#00FF00] text-black border-black'
                : 'bg-[#FF0000] text-white border-white'
            }`}
          >
            {isLive ? 'LIVE' : isEnabled ? 'OFF' : 'PAUSED'}
          </span>
          {!compact && (
            <>
              <button
                type="button"
                onClick={() => {
                  soundEffects.playClick();
                  setIsEnabled(e => !e);
                }}
                aria-label={isEnabled ? 'Pause camera stream' : 'Resume camera stream'}
                className="px-1.5 py-0.5 border border-white bg-[#11112B] text-white font-mono text-[9px] font-bold hover:bg-[#1E1E4A]"
              >
                {isEnabled ? 'II' : '▶'}
              </button>
              <button
                type="button"
                onClick={handleReload}
                aria-label="Reload camera stream"
                className="p-0.5 border border-white bg-[#11112B] text-white hover:bg-[#1E1E4A]"
              >
                <RefreshCw className="w-3 h-3" />
              </button>
              <button
                type="button"
                onClick={() => {
                  soundEffects.playClick();
                  setIsFullscreen(f => !f);
                }}
                aria-label="Toggle camera fullscreen"
                className="p-0.5 border border-white bg-[#11112B] text-white hover:bg-[#1E1E4A]"
              >
                <Maximize2 className="w-3 h-3" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Video Stream Body */}
      <div
        onClick={compact ? onClickPreview : undefined}
        className={`relative w-full ${
          isFullscreen ? 'flex-1' : compact ? 'h-24' : 'aspect-video'
        } bg-black overflow-hidden flex items-center justify-center ${
          compact && onClickPreview ? 'cursor-pointer' : ''
        }`}
      >
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
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="flex flex-col items-center justify-center text-center p-2">
              <VideoOff className="w-5 h-5 text-slate-500 mb-1" />
              <div className="font-mono text-[10px] font-bold text-slate-300">
                CAMERA FEED UNAVAILABLE
              </div>
              {!compact && (
                <button
                  type="button"
                  onClick={handleReload}
                  className="mt-2 pixel-btn px-2.5 py-1 bg-[#0000FF] text-white font-pixel text-[8px]"
                >
                  RECONNECT
                </button>
              )}
            </div>
          )
        ) : (
          <div className="font-mono text-[10px] text-slate-400">STREAM PAUSED</div>
        )}

        {/* Pixel Corner Viewfinder Reticle */}
        <div className="pointer-events-none absolute inset-1.5">
          <div className="absolute top-0 left-0 w-2.5 h-2.5 border-t-2 border-l-2 border-white/80" />
          <div className="absolute top-0 right-0 w-2.5 h-2.5 border-t-2 border-r-2 border-white/80" />
          <div className="absolute bottom-0 left-0 w-2.5 h-2.5 border-b-2 border-l-2 border-white/80" />
          <div className="absolute bottom-0 right-0 w-2.5 h-2.5 border-b-2 border-r-2 border-white/80" />
        </div>
      </div>

      {!compact && (
        <div className="px-2.5 py-1 bg-[#0F0F23] border-t-2 border-white/50 font-mono text-[10px] font-bold text-slate-200 flex items-center justify-between">
          <span>640 x 480</span>
          <span>|</span>
          <span>15 FPS ({topic})</span>
        </div>
      )}
    </div>
  );
};
