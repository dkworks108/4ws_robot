import React, { useState } from 'react';
import { X, Server, Check, Keyboard, Hand, Volume2 } from 'lucide-react';
import { rosService } from '../services/rosService';
import { Handedness } from '../types/ros';
import { manualInputPipeline } from '../services/manualInputPipeline';
import { soundEffects } from '../utils/soundEffects';

interface ConnectionSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  detectedIps?: string[];
  handedness: Handedness;
  onChangeHandedness: (h: Handedness) => void;
  sfxMuted: boolean;
  onToggleSfx: () => void;
}

export const ConnectionSettingsModal: React.FC<ConnectionSettingsModalProps> = ({
  isOpen,
  onClose,
  detectedIps = [],
  handedness,
  onChangeHandedness,
  sfxMuted,
  onToggleSfx,
}) => {
  const [host, setHost] = useState(rosService.config.host);
  const [rosPort, setRosPort] = useState(rosService.config.rosbridge_port.toString());
  const [videoPort, setVideoPort] = useState(rosService.config.web_video_port.toString());
  const [kbEnabled, setKbEnabled] = useState(manualInputPipeline.isKeyboardEnabled());
  const [kbSens, setKbSens] = useState(Math.round(manualInputPipeline.getKeyboardSensitivity() * 100));

  if (!isOpen) return null;

  const handleSave = () => {
    soundEffects.playClick();
    const p = parseInt(rosPort, 10) || 9090;
    const vp = parseInt(videoPort, 10) || 8080;

    manualInputPipeline.setKeyboardEnabled(kbEnabled);
    manualInputPipeline.setKeyboardSensitivity(kbSens / 100);

    const netChanged =
      host !== rosService.config.host ||
      p !== rosService.config.rosbridge_port ||
      vp !== rosService.config.web_video_port;

    rosService.config.host = host;
    rosService.config.rosbridge_port = p;
    rosService.config.web_video_port = vp;

    if (netChanged) {
      rosService.connect(host, p);
    }
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 bg-black/85"
      role="dialog"
      aria-modal="true"
      aria-label="System Settings"
    >
      <div className="w-full max-w-md pixel-panel bg-[#080818] text-white max-h-[90vh] overflow-y-auto">
        <div className="pixel-header px-3 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-[#FFFF00]" />
            <h2 className="font-pixel text-[10px] text-white">SYSTEM SETTINGS</h2>
          </div>
          <button
            type="button"
            onClick={() => {
              soundEffects.playClick();
              onClose();
            }}
            aria-label="Close Settings"
            className="pixel-btn p-1 bg-[#11112B] text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-3.5 space-y-4 font-mono text-xs">
          {/* Network Settings */}
          <div className="space-y-2 border-2 border-white/40 p-2.5 bg-[#0F0F23]">
            <div className="font-pixel text-[8px] text-[#FFFF00]">ROS 2 NETWORK BRIDGE</div>
            <div>
              <label className="block text-[10px] text-slate-300 mb-1" htmlFor="host-ip-input">
                ROBOT / HOST IP ADDRESS
              </label>
              <input
                id="host-ip-input"
                type="text"
                value={host}
                onChange={e => setHost(e.target.value)}
                className="w-full bg-[#080818] border-2 border-white/70 px-2.5 py-1.5 text-white font-mono"
              />
            </div>

            {detectedIps.length > 0 && (
              <div>
                <span className="block text-[9px] text-slate-400 mb-1">DETECTED INTERFACES:</span>
                <div className="flex flex-wrap gap-1.5">
                  {detectedIps.map(ip => (
                    <button
                      key={ip}
                      type="button"
                      onClick={() => {
                        soundEffects.playClick();
                        setHost(ip);
                      }}
                      className={`px-2 py-0.5 border font-mono text-[10px] ${
                        host === ip
                          ? 'bg-[#00FF00] text-black border-black font-bold'
                          : 'bg-[#11112B] text-slate-200 border-white/60'
                      }`}
                    >
                      {ip}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[10px] text-slate-300 mb-1" htmlFor="ws-port-input">
                  ROSBRIDGE PORT
                </label>
                <input
                  id="ws-port-input"
                  type="text"
                  value={rosPort}
                  onChange={e => setRosPort(e.target.value)}
                  className="w-full bg-[#080818] border-2 border-white/70 px-2.5 py-1 text-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-300 mb-1" htmlFor="vid-port-input">
                  VIDEO PORT
                </label>
                <input
                  id="vid-port-input"
                  type="text"
                  value={videoPort}
                  onChange={e => setVideoPort(e.target.value)}
                  className="w-full bg-[#080818] border-2 border-white/70 px-2.5 py-1 text-white font-mono"
                />
              </div>
            </div>
          </div>

          {/* Desktop Keyboard Control Settings */}
          <div className="space-y-2 border-2 border-white/40 p-2.5 bg-[#0F0F23]">
            <div className="flex items-center justify-between">
              <span className="font-pixel text-[8px] text-[#FFFF00] flex items-center gap-1.5">
                <Keyboard className="w-3.5 h-3.5" /> DESKTOP KEYBOARD CONTROL
              </span>
              <button
                type="button"
                onClick={() => {
                  soundEffects.playClick();
                  setKbEnabled(v => !v);
                }}
                aria-pressed={kbEnabled}
                className={`pixel-btn px-2.5 py-0.5 font-pixel text-[8px] ${
                  kbEnabled ? 'bg-[#00FF00] text-black border-black' : 'bg-slate-700 text-white'
                }`}
              >
                {kbEnabled ? 'ENABLED' : 'DISABLED'}
              </button>
            </div>

            <div>
              <div className="flex items-center justify-between text-[10px] mb-1">
                <span className="text-slate-300">KEYBOARD SENSITIVITY:</span>
                <span className="text-[#00FF00] font-extrabold">{kbSens}%</span>
              </div>
              <input
                type="range"
                min={25}
                max={100}
                step={5}
                value={kbSens}
                onChange={e => setKbSens(parseInt(e.target.value, 10))}
                aria-label="Keyboard sensitivity percentage"
                className="w-full accent-[#FFFF00]"
              />
            </div>
          </div>

          {/* Mobile One-Handed Layout & Audio */}
          <div className="space-y-2.5 border-2 border-white/40 p-2.5 bg-[#0F0F23]">
            <div className="font-pixel text-[8px] text-[#FFFF00] flex items-center gap-1.5">
              <Hand className="w-3.5 h-3.5" /> MOBILE HANDEDNESS &amp; AUDIO
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  soundEffects.playClick();
                  onChangeHandedness('left');
                }}
                aria-pressed={handedness === 'left'}
                className={`pixel-btn py-1.5 font-pixel text-[8px] ${
                  handedness === 'left'
                    ? 'bg-[#FFFF00] text-black border-black'
                    : 'bg-[#11112B] text-white'
                }`}
              >
                LEFT-HANDED
              </button>
              <button
                type="button"
                onClick={() => {
                  soundEffects.playClick();
                  onChangeHandedness('right');
                }}
                aria-pressed={handedness === 'right'}
                className={`pixel-btn py-1.5 font-pixel text-[8px] ${
                  handedness === 'right'
                    ? 'bg-[#FFFF00] text-black border-black'
                    : 'bg-[#11112B] text-white'
                }`}
              >
                RIGHT-HANDED
              </button>
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-[10px] text-slate-300 flex items-center gap-1.5">
                <Volume2 className="w-3.5 h-3.5 text-[#00FF00]" />
                8-BIT SOUND EFFECTS
              </span>
              <button
                type="button"
                onClick={onToggleSfx}
                aria-pressed={!sfxMuted}
                className={`pixel-btn px-2.5 py-0.5 font-pixel text-[8px] ${
                  !sfxMuted ? 'bg-[#00FF00] text-black border-black' : 'bg-[#FF0000] text-white'
                }`}
              >
                {!sfxMuted ? 'SFX ON' : 'MUTED'}
              </button>
            </div>
          </div>
        </div>

        <div className="p-3 border-t-2 border-white/50 flex items-center justify-end gap-2 bg-[#080818]">
          <button
            type="button"
            onClick={() => {
              soundEffects.playClick();
              onClose();
            }}
            className="pixel-btn px-3 py-1.5 bg-[#11112B] text-white font-pixel text-[8px]"
          >
            CANCEL
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="pixel-btn px-3 py-1.5 bg-[#00FF00] text-black border-black font-pixel text-[8px] flex items-center gap-1"
          >
            <Check className="w-3.5 h-3.5" /> APPLY
          </button>
        </div>
      </div>
    </div>
  );
};
