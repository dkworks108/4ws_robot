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

    // Clear canvas
    ctx.fillStyle = '#0a0d14';
    ctx.fillRect(0, 0, width, height);

    // Maximum radar view range in meters
    const maxRange = 12.0;
    const scale = (Math.min(width, height) / 2 - 15) / maxRange;

    // Draw range rings
    const rings = [2.0, 5.0, 8.0, 11.0];
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 4]);

    rings.forEach(r => {
      ctx.strokeStyle = '#1e293b';
      ctx.beginPath();
      ctx.arc(centerX, centerY, r * scale, 0, 2 * Math.PI);
      ctx.stroke();

      ctx.fillStyle = '#475569';
      ctx.font = '9px monospace';
      ctx.fillText(`${r}m`, centerX + r * scale - 12, centerY - 4);
    });

    // Crosshairs
    ctx.strokeStyle = '#1e293b';
    ctx.setLineDash([2, 4]);
    ctx.beginPath();
    ctx.moveTo(centerX, 10);
    ctx.lineTo(centerX, height - 10);
    ctx.moveTo(10, centerY);
    ctx.lineTo(width - 10, centerY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw Robot Body at Center
    ctx.fillStyle = '#0284c7';
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 1.5;
    const robotSize = 0.36 * scale;
    ctx.beginPath();
    ctx.rect(centerX - robotSize / 2, centerY - robotSize / 2, robotSize, robotSize);
    ctx.fill();
    ctx.stroke();

    // Direction Heading Pointer
    ctx.fillStyle = '#f43f5e';
    ctx.beginPath();
    ctx.moveTo(centerX, centerY - robotSize / 2 - 4);
    ctx.lineTo(centerX - 4, centerY - robotSize / 2 + 2);
    ctx.lineTo(centerX + 4, centerY - robotSize / 2 + 2);
    ctx.closePath();
    ctx.fill();

    if (!scan || !scan.ranges || scan.ranges.length === 0) {
      ctx.fillStyle = '#64748b';
      ctx.font = '11px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('AWAITING 2D LIDAR SCAN...', centerX, centerY + 45);
      return;
    }

    // Render Laser Scan obstacle points
    const ranges = scan.ranges;
    const angleMin = scan.angle_min;
    const angleInc = scan.angle_increment;

    for (let i = 0; i < ranges.length; i++) {
      const r = ranges[i];
      if (isNaN(r) || r < scan.range_min || r > scan.range_max || r > maxRange) continue;

      // Laser coordinate convention: angle 0 is forward (+X)
      // In canvas: +X is right, +Y is down.
      // Forward is top (-Y in canvas), Left is +Y in ROS (left in canvas)
      const angle = angleMin + i * angleInc;
      const x_ros = r * Math.cos(angle);
      const y_ros = r * Math.sin(angle);

      const canvasX = centerX - y_ros * scale;
      const canvasY = centerY - x_ros * scale;

      // Color based on proximity danger
      if (r < 1.0) {
        ctx.fillStyle = '#f43f5e'; // Red (Critical danger)
      } else if (r < 3.0) {
        ctx.fillStyle = '#f59e0b'; // Amber (Caution)
      } else {
        ctx.fillStyle = '#00d4ff'; // Cyan (Free clear obstacle)
      }

      ctx.beginPath();
      ctx.arc(canvasX, canvasY, 1.5, 0, 2 * Math.PI);
      ctx.fill();
    }
  }, [scan]);

  const nearestDistance = scan && scan.ranges && scan.ranges.length > 0
    ? Math.min(...scan.ranges.filter(r => !isNaN(r) && r > (scan.range_min || 0.1))).toFixed(2)
    : '--';

  return (
    <div className="w-full bg-gray-950 p-3 rounded-2xl border border-gray-800 flex flex-col items-center">
      <div className="w-full flex items-center justify-between mb-2">
        <span className="text-xs font-mono font-bold text-gray-400 tracking-wider flex items-center gap-1.5">
          <Radio className="w-3.5 h-3.5 text-cyan-400" /> 2D LIDAR RADAR (20m GPU)
        </span>
        <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/40">
          CLOSEST: <strong className="text-white">{nearestDistance} m</strong>
        </span>
      </div>

      <div className="relative w-full aspect-square max-w-[340px] rounded-xl overflow-hidden border border-gray-800">
        <canvas
          ref={canvasRef}
          width={340}
          height={340}
          className="w-full h-full object-contain"
        />
      </div>

      <div className="w-full flex justify-between text-[9px] font-mono text-gray-500 mt-2 px-1">
        <span>RED: &lt;1.0m (Collision Risk)</span>
        <span>AMBER: &lt;3.0m</span>
        <span>CYAN: &gt;3.0m</span>
      </div>
    </div>
  );
};

