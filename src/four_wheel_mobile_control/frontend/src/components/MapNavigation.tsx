import React, { useRef, useEffect, useState, useCallback } from 'react';
import { OccupancyGridData, OdometryData, ExplorationCoverage, OperatingMode } from '../types/ros';
import { rosService } from '../services/rosService';
import { Map, Navigation, Compass, Play, Pause, Square, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

interface MapNavigationProps {
  mapData: OccupancyGridData | null;
  odom: OdometryData | null;
  plan: Array<{ x: number; y: number }>;
  coverage: ExplorationCoverage | null;
  operatingMode: OperatingMode;
  explorationStatus: string;
}

export const MapNavigation: React.FC<MapNavigationProps> = ({
  mapData,
  odom,
  plan,
  coverage,
  operatingMode,
  explorationStatus
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Pan and Zoom view state
  const [zoom, setZoom] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [startPan, setStartPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Selected Target Goal
  const [selectedGoal, setSelectedGoal] = useState<{ x: number; y: number } | null>(null);

  // Render Map & Overlays
  const renderMap = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.fillStyle = '#0f172a'; // Neutral background
    ctx.fillRect(0, 0, width, height);

    if (!mapData || !mapData.data || mapData.data.length === 0) {
      ctx.fillStyle = '#64748b';
      ctx.font = '12px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('AWAITING SLAM TOOLBOX OCCUPANCY GRID (/map)...', width / 2, height / 2);
      return;
    }

    ctx.save();
    // Center & Apply Pan + Zoom
    ctx.translate(width / 2 + pan.x, height / 2 + pan.y);
    ctx.scale(zoom, zoom);

    // Calculate map pixel scaling
    // Origin is bottom-left in ROS map
    const mapW = mapData.width;
    const mapH = mapData.height;
    const res = mapData.resolution;
    const originX = mapData.originX;
    const originY = mapData.originY;

    // Offscreen buffer for raster occupancy grid
    const imgData = ctx.createImageData(mapW, mapH);
    const buf = imgData.data;

    // ROS map data: index 0 is lower-left
    for (let y = 0; y < mapH; y++) {
      for (let x = 0; x < mapW; x++) {
        const val = mapData.data[y * mapW + x];
        // Invert Y for canvas coordinate system (canvas Y increases downwards)
        const canvasY = mapH - 1 - y;
        const idx = (canvasY * mapW + x) * 4;

        if (val === -1) {
          // Unknown space -> dark slate
          buf[idx] = 30;
          buf[idx + 1] = 41;
          buf[idx + 2] = 59;
          buf[idx + 3] = 255;
        } else if (val === 0) {
          // Free space -> light clean off-white
          buf[idx] = 241;
          buf[idx + 1] = 245;
          buf[idx + 2] = 249;
          buf[idx + 3] = 255;
        } else if (val > 50) {
          // Obstacle / Wall -> solid dark charcoal
          buf[idx] = 15;
          buf[idx + 1] = 23;
          buf[idx + 2] = 42;
          buf[idx + 3] = 255;
        } else {
          // Probability gradient
          buf[idx] = 148;
          buf[idx + 1] = 163;
          buf[idx + 2] = 184;
          buf[idx + 3] = 255;
        }
      }
    }

    // Render offscreen canvas
    const offCanvas = document.createElement('canvas');
    offCanvas.width = mapW;
    offCanvas.height = mapH;
    const offCtx = offCanvas.getContext('2d');
    if (offCtx) {
      offCtx.putImageData(imgData, 0, 0);
      // Center map on canvas
      const drawX = -mapW / 2;
      const drawY = -mapH / 2;
      ctx.drawImage(offCanvas, drawX, drawY);

      // Helper function to map World (meters) to Canvas Coordinates
      const worldToCanvas = (wx: number, wy: number) => {
        const px = (wx - originX) / res + drawX;
        const py = (mapH - (wy - originY) / res) + drawY;
        return { px, py };
      };

      // 1. Draw Nav2 Planned Path
      if (plan && plan.length > 1) {
        ctx.strokeStyle = '#10b981'; // Emerald path
        ctx.lineWidth = 2.5;
        ctx.setLineDash([4, 2]);
        ctx.beginPath();
        for (let i = 0; i < plan.length; i++) {
          const pt = worldToCanvas(plan[i].x, plan[i].y);
          if (i === 0) ctx.moveTo(pt.px, pt.py);
          else ctx.lineTo(pt.px, pt.py);
        }
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // 2. Draw Selected / Active Navigation Goal
      if (selectedGoal) {
        const goalPt = worldToCanvas(selectedGoal.x, selectedGoal.y);
        ctx.fillStyle = '#fbbf24'; // Amber star/target
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(goalPt.px, goalPt.py, 6, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();

        ctx.font = 'bold 10px monospace';
        ctx.fillStyle = '#fbbf24';
        ctx.fillText(`GOAL (${selectedGoal.x.toFixed(1)}, ${selectedGoal.y.toFixed(1)})`, goalPt.px + 8, goalPt.py + 3);
      }

      // 3. Draw Robot Pose & Heading
      if (odom) {
        const robotPt = worldToCanvas(odom.x, odom.y);

        // Circular footprint
        ctx.fillStyle = '#00d4ff';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(robotPt.px, robotPt.py, 7, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();

        // Heading arrow (yaw)
        // Canvas Y increases downwards, so yaw in canvas is -odom.yaw
        const arrowLength = 14;
        const yaw = odom.yaw;
        const endX = robotPt.px + arrowLength * Math.cos(-yaw);
        const endY = robotPt.py + arrowLength * Math.sin(-yaw);

        ctx.strokeStyle = '#f43f5e'; // Bright red pointer
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(robotPt.px, robotPt.py);
        ctx.lineTo(endX, endY);
        ctx.stroke();
      }
    }

    ctx.restore();
  }, [mapData, odom, plan, selectedGoal, zoom, pan]);

  useEffect(() => {
    renderMap();
  }, [renderMap]);

  // Touch & Pointer Handlers for Pan and Goal Selection
  const handlePointerDown = (e: React.PointerEvent) => {
    setIsPanning(true);
    setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isPanning) return;
    setPan({
      x: e.clientX - startPan.x,
      y: e.clientY - startPan.y
    });
  };

  const handlePointerUp = () => {
    setIsPanning(false);
  };

  // Click on canvas to pick destination in autonomous nav mode
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!mapData || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const width = canvasRef.current.width;
    const height = canvasRef.current.height;

    // Reverse transformations
    const mapW = mapData.width;
    const mapH = mapData.height;
    const res = mapData.resolution;
    const originX = mapData.originX;
    const originY = mapData.originY;
    const drawX = -mapW / 2;
    const drawY = -mapH / 2;

    const canvasTransX = (clickX - (width / 2 + pan.x)) / zoom;
    const canvasTransY = (clickY - (height / 2 + pan.y)) / zoom;

    const mapPixelX = canvasTransX - drawX;
    const mapPixelY = mapH - (canvasTransY - drawY);

    const worldX = originX + mapPixelX * res;
    const worldY = originY + mapPixelY * res;

    setSelectedGoal({ x: parseFloat(worldX.toFixed(2)), y: parseFloat(worldY.toFixed(2)) });
  };

  const handleSendGoal = () => {
    if (!selectedGoal) return;
    rosService.sendNavigationGoal(selectedGoal.x, selectedGoal.y);
  };

  const handleCancelGoal = () => {
    rosService.cancelNavigationGoal();
    setSelectedGoal(null);
  };

  return (
    <div className="w-full bg-gray-950 p-3 rounded-2xl border border-gray-800 flex flex-col">
      {/* Header */}
      <div className="w-full flex items-center justify-between mb-2">
        <span className="text-xs font-mono font-bold text-gray-400 tracking-wider flex items-center gap-1.5">
          <Map className="w-3.5 h-3.5 text-cyan-400" /> SLAM TOOLBOX OCCUPANCY GRID
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setZoom(z => Math.min(3.5, z * 1.25))}
            className="p-1 rounded bg-gray-900 border border-gray-800 text-gray-300 hover:text-white"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoom(z => Math.max(0.4, z / 1.25))}
            className="p-1 rounded bg-gray-900 border border-gray-800 text-gray-300 hover:text-white"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => { setZoom(1.0); setPan({ x: 0, y: 0 }); }}
            className="p-1 rounded bg-gray-900 border border-gray-800 text-gray-300 hover:text-white"
            title="Reset Map View"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Map Interactive Canvas */}
      <div className="relative w-full aspect-square max-h-[380px] rounded-xl overflow-hidden border border-gray-800 bg-[#0f172a] touch-none">
        <canvas
          ref={canvasRef}
          width={400}
          height={400}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onClick={handleCanvasClick}
          className="w-full h-full object-contain cursor-crosshair"
        />

        {/* Tip overlay */}
        <div className="absolute bottom-2 left-2 bg-black/60 backdrop-blur-sm px-2 py-0.5 rounded text-[9px] font-mono text-gray-400 border border-white/10">
          Drag to Pan &bull; Tap Map to Set Nav2 Goal
        </div>
      </div>

      {/* Nav2 Action Controls */}
      <div className="w-full flex items-center justify-between gap-2 mt-2 pt-2 border-t border-gray-900">
        <div className="text-[11px] font-mono text-gray-400">
          {selectedGoal ? (
            <span>TARGET: <strong className="text-amber-400">({selectedGoal.x}, {selectedGoal.y})</strong></span>
          ) : (
            <span>TAP MAP TO SET GOAL</span>
          )}
        </div>
        <div className="flex gap-1.5">
          {selectedGoal && (
            <button
              onClick={handleSendGoal}
              className="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-mono font-bold flex items-center gap-1 active:scale-95 transition"
            >
              <Navigation className="w-3.5 h-3.5" /> NAVIGATE
            </button>
          )}
          {(operatingMode === 'AUTONOMOUS_NAV' || selectedGoal) && (
            <button
              onClick={handleCancelGoal}
              className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-rose-400 rounded-lg text-xs font-mono font-bold active:scale-95 transition"
            >
              CANCEL
            </button>
          )}
        </div>
      </div>

      {/* Frontier Autonomous Exploration Control Bar */}
      <div className="w-full mt-2 pt-2 border-t border-gray-900 bg-gray-900/60 p-2.5 rounded-xl border border-gray-800/80">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-mono font-bold text-gray-300 flex items-center gap-1.5">
            <Compass className="w-4 h-4 text-cyan-400" /> AUTONOMOUS EXPLORATION
          </span>
          <span className="text-[10px] font-mono text-cyan-400 font-bold">
            STATUS: {explorationStatus || 'IDLE'}
          </span>
        </div>

        {/* Coverage Progress Bar */}
        <div className="w-full bg-gray-950 rounded-full h-2 mb-2 overflow-hidden border border-gray-800">
          <div
            style={{ width: `${coverage ? coverage.explored_pct : 0}%` }}
            className="bg-gradient-to-r from-cyan-500 to-emerald-400 h-full transition-all duration-300"
          />
        </div>
        <div className="flex justify-between text-[10px] font-mono text-gray-400 mb-2">
          <span>COVERAGE: <strong className="text-white">{coverage ? coverage.explored_pct : 0}%</strong></span>
          <span>AREA: <strong className="text-white">{coverage ? coverage.known_area_m2 : 0} m&sup2;</strong></span>
          <span>GOALS: <strong className="text-white">{coverage ? coverage.goals_completed : 0}</strong></span>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-4 gap-1.5 font-mono text-xs">
          <button
            onClick={() => rosService.startExploration()}
            className="py-1.5 px-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg flex items-center justify-center gap-1 active:scale-95 transition"
          >
            <Play className="w-3.5 h-3.5" /> START
          </button>
          <button
            onClick={() => rosService.pauseExploration()}
            className="py-1.5 px-2 bg-amber-600 hover:bg-amber-500 text-white font-bold rounded-lg flex items-center justify-center gap-1 active:scale-95 transition"
          >
            <Pause className="w-3.5 h-3.5" /> PAUSE
          </button>
          <button
            onClick={() => rosService.resumeExploration()}
            className="py-1.5 px-2 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-lg flex items-center justify-center gap-1 active:scale-95 transition"
          >
            <Play className="w-3.5 h-3.5" /> RESUME
          </button>
          <button
            onClick={() => rosService.stopExploration()}
            className="py-1.5 px-2 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-lg flex items-center justify-center gap-1 active:scale-95 transition"
          >
            <Square className="w-3.5 h-3.5" /> STOP
          </button>
        </div>
      </div>
    </div>
  );
};

