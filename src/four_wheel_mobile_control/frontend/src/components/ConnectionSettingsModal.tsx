import React, { useState } from 'react';
import { X, Wifi, Server, Check } from 'lucide-react';
import { rosService } from '../services/rosService';

interface ConnectionSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  detectedIps?: string[];
}

export const ConnectionSettingsModal: React.FC<ConnectionSettingsModalProps> = ({
  isOpen,
  onClose,
  detectedIps = []
}) => {
  const [host, setHost] = useState(rosService.config.host);
  const [rosPort, setRosPort] = useState(rosService.config.rosbridge_port.toString());
  const [videoPort, setVideoPort] = useState(rosService.config.web_video_port.toString());

  if (!isOpen) return null;

  const handleSaveAndReconnect = () => {
    const p = parseInt(rosPort, 10) || 9090;
    const vp = parseInt(videoPort, 10) || 8080;
    rosService.config.host = host;
    rosService.config.rosbridge_port = p;
    rosService.config.web_video_port = vp;
    rosService.connect(host, p);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-md bg-gray-950 border border-gray-800 rounded-2xl p-5 shadow-2xl">
        <div className="flex items-center justify-between pb-3 border-b border-gray-800 mb-4">
          <div className="flex items-center gap-2">
            <Server className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-bold font-mono text-white">CONNECTION SETTINGS</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4 font-mono text-xs">
          {/* Host IP input */}
          <div>
            <label className="block text-gray-400 mb-1">ROBOT / HOST IP ADDRESS</label>
            <input
              type="text"
              value={host}
              onChange={e => setHost(e.target.value)}
              placeholder="e.g. 192.168.1.100"
              className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-white font-mono focus:outline-none focus:border-cyan-400"
            />
          </div>

          {/* Quick select detected IPs */}
          {detectedIps.length > 0 && (
            <div>
              <span className="block text-[10px] text-gray-500 mb-1">DETECTED SYSTEM INTERFACES:</span>
              <div className="flex flex-wrap gap-1.5">
                {detectedIps.map(ip => (
                  <button
                    key={ip}
                    type="button"
                    onClick={() => setHost(ip)}
                    className={`px-2 py-0.5 rounded text-[10px] border ${
                      host === ip
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500'
                        : 'bg-gray-900 text-gray-400 border-gray-800 hover:text-white'
                    }`}
                  >
                    {ip}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Port Settings */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-gray-400 mb-1">ROSBRIDGE WS PORT</label>
              <input
                type="text"
                value={rosPort}
                onChange={e => setRosPort(e.target.value)}
                className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-white font-mono focus:outline-none focus:border-cyan-400"
              />
            </div>
            <div>
              <label className="block text-gray-400 mb-1">WEB VIDEO PORT</label>
              <input
                type="text"
                value={videoPort}
                onChange={e => setVideoPort(e.target.value)}
                className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-white font-mono focus:outline-none focus:border-cyan-400"
              />
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-gray-900/60 border border-gray-800 text-[10px] text-gray-400">
            <span className="font-bold text-cyan-400 block mb-0.5">MOBILE ACCESS TIP:</span>
            Ensure your mobile device is connected to the same Wi-Fi network. Open <code className="text-white">http://{host}:3000</code> on your mobile browser.
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 mt-5 pt-3 border-t border-gray-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-gray-900 text-gray-400 hover:text-white font-mono text-xs"
          >
            CANCEL
          </button>
          <button
            onClick={handleSaveAndReconnect}
            className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold flex items-center gap-1.5 shadow-lg active:scale-95 transition"
          >
            <Check className="w-4 h-4" /> APPLY & RECONNECT
          </button>
        </div>
      </div>
    </div>
  );
};

