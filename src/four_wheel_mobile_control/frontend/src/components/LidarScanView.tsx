import React, { useRef, useEffect } from 'react';
import { LaserScanData } from '../types/ros';
import { Radio } from 'lucide-react';

interface LidarScanViewProps {
  scan: LaserScanData | null;
}

export const LidarScanView: React.FC<LidarScanViewProps> = ({ scan }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;

    // Deep retro dark navy background
    ctx.fillStyle = '#050816';
    ctx.fillRect(0, 0, width, height);

    const maxRange = scan?.range_max ? Math.min(20.0, scan.range_max) : 12.0;
    const scale = (Math.min(width, height) / 2 - 10) / maxRange;

    // Range rings
    ctx.lineWidth = 1;
    const ringCount = 3;
    for (let i = 1; i <= ringCount; i++) {
      const r = (maxRange * i) / ringCount;
      ctx.strokeStyle = '#1E3A8A';
      ctx.setLineDash([2, 3]);
      ctx.beginPath();
      ctx.arc(centerX, centerY, r * scale, 0, 2 * Math.PI);
      ctx.stroke();
    }

    // Crosshairs
    ctx.strokeStyle = '#1E3A8A';
    ctx.beginPath();
    ctx.moveTo(centerX, 6);
    ctx.lineTo(centerX, height - 6);
    ctx.moveTo(6, centerY);
    ctx.lineTo(width - 6, centerY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Red pixel robot triangle in center
    ctx.fillStyle = '#FF0000';
    ctx.beginPath();
    ctx.moveTo(centerX, centerY - 7);
    ctx.lineTo(centerX - 5, centerY + 5);
    ctx.lineTo(centerX + 5, centerY + 5);
    ctx.closePath();
    ctx.fill();

    if (!scan || !scan.ranges || scan.ranges.length === 0) {
      ctx.fillStyle = '#94A3B8';
      ctx.font = 'bold 10px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('AWAITING /scan', centerX, centerY + 28);
      return;
    }

    const ranges = scan.ranges;
    const angleMin = scan.angle_min;
    const angleInc = scan.angle_increment;

    // Crisp square pixel laser points
    ctx.fillStyle = '#22D3EE';
    for (let i = 0; i < ranges.length; i++) {
      const r = ranges[i];
      if (!Number.isFinite(r) || r < scan.range_min || r > scan.range_max || r > maxRange) continue;

      const angle = angleMin + i * angleInc;
      const xRos = r * Math.cos(angle);
      const yRos = r * Math.sin(angle);
      const px = Math.round(centerX - yRos * scale);
      const py = Math.round(centerY - xRos * scale);
      ctx.fillRect(px - 1, py - 1, 2, 2);
    }
  }, [scan]);

  const activePoints = scan ? scan.ranges.filter(r => Number.isFinite(r) && r > scan.range_min).length : 0;
  const maxR = scan ? Math.round(scan.range_max) : 20;
  const rateHz = scan?.rateHz ? scan.rateHz : scan ? 15 : 0;
  const isLive = scan !== null && Date.now() - scan.lastUpdated < 3000;

  return (
    <div className="pixel-panel bg-[#080818] flex flex-col">
      <div className="pixel-header px-2.5 py-1 flex items-center justify-between gap-1">
        <span className="font-pixel text-[8px] sm:text-[9px] text-white flex items-center gap-1.5 truncate">
          <Radio className="w-3.5 h-3.5 shrink-0" />
          <span>LIDAR (360&deg;)</span>
        </span>
        <span
          className={`px-1.5 py-0.5 border font-pixel text-[7px] ${
            isLive ? 'bg-[#00FF00] text-black border-black' : 'bg-slate-700 text-slate-300 border-white/50'
          }`}
        >
          {isLive ? 'LIVE' : 'WAIT'}
        </span>
      </div>

      <div className="p-2 flex items-center gap-2.5">
        <div className="border-2 border-white/60 bg-[#050816] shrink-0">
          <canvas ref={canvasRef} width={140} height={140} className="w-[128px] h-[128px] block" />
        </div>

        <div className="flex-1 font-mono text-[10px] space-y-2 min-w-0">
          <div>
            <div className="text-slate-300 text-[9px]">RANGE:</div>
            <div className="text-[#FFFF00] font-extrabold text-xs">{maxR} m</div>
          </div>
          <div>
            <div className="text-slate-300 text-[9px]">POINTS:</div>
            <div className="text-white font-extrabold text-xs">{activePoints || (scan ? scan.ranges.length : '--')}</div>
          </div>
          <div>
            <div className="text-slate-300 text-[9px]">RATE:</div>
            <div className="text-[#00FF00] font-extrabold text-xs">{rateHz > 0 ? `${rateHz} Hz` : '--'}</div>
          </div>
        </div>
      </div>
    </div>
  );
};
