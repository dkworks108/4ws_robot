import React from 'react';
import { ImuData } from '../types/ros';
import { PixelImuTriad } from './PixelIcons';
import { Cpu } from 'lucide-react';

interface ImuViewProps {
  imu: ImuData | null;
}

export const ImuView: React.FC<ImuViewProps> = ({ imu }) => {
  const isLive = imu !== null && Date.now() - imu.lastUpdated < 3000;

  return (
    <div className="pixel-panel bg-[#080818] flex flex-col">
      <div className="pixel-header px-2.5 py-1 flex items-center justify-between gap-1">
        <span className="font-pixel text-[8px] sm:text-[9px] text-white flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 shrink-0" />
          <span>IMU</span>
        </span>
        <span
          className={`px-1.5 py-0.5 border font-pixel text-[7px] ${
            isLive ? 'bg-[#00FF00] text-black border-black' : 'bg-slate-700 text-slate-300 border-white/50'
          }`}
        >
          {isLive ? 'LIVE' : 'WAIT'}
        </span>
      </div>

      <div className="p-2.5 flex items-center justify-between gap-2">
        <div className="font-mono text-[11px] font-bold space-y-1.5 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-slate-300 w-14">ROLL :</span>
            <span className="text-white">{imu ? `${imu.rollDeg.toFixed(1)}°` : '--'}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-300 w-14">PITCH:</span>
            <span className="text-white">{imu ? `${imu.pitchDeg.toFixed(1)}°` : '--'}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-300 w-14">YAW  :</span>
            <span className="text-[#FFFF00]">{imu ? `${imu.yawDeg.toFixed(1)}°` : '--'}</span>
          </div>
          {imu && (
            <div className="text-[9px] text-[#00FF00]">
              Az: {imu.az.toFixed(2)} m/s&sup2; ({imu.rateHz || 50} Hz)
            </div>
          )}
        </div>

        <div className="shrink-0 bg-[#0F0F23] border-2 border-white/50 p-1.5">
          <PixelImuTriad className="w-14 h-14" />
        </div>
      </div>
    </div>
  );
};

