import React, { useRef, useEffect, useState, useCallback } from 'react';
import { OccupancyGridData, OdometryData, ExplorationCoverage } from '../types/ros';
import { Map, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import { soundEffects } from '../utils/soundEffects';

interface SlamMapPanelProps {
  mapData: OccupancyGridData | null;
  odom: OdometryData | null;
  plan: Array<{ x: number; y: number }>;
  coverage: ExplorationCoverage | null;
  selectedGoal: { x: number; y: number } | null;
  onSelectGoal: (goal: { x: number; y: number }) => void;
  goalPickArmed?: boolean;
  heightClass?: string;
}

export const SlamMapPanel: React.FC<SlamMapPanelProps> = ({
  mapData,
  odom,
  plan,
  coverage,
  selectedGoal,
  onSelectGoal,
  goalPickArmed = false,
  heightClass = 'h-[190px] sm:h-[220px]',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [zoom, setZoom] = useState<number>(0.65);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const dragStartRef = useRef<{ x: number; y: number; moved: boolean }>({
    x: 0,
    y: 0,
    moved: false,
  });

  const renderMap = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.fillStyle = '#06081A';
    ctx.fillRect(0, 0, width, height);

    if (!mapData || !mapData.data || mapData.data.length === 0) {
      ctx.fillStyle = '#94A3B8';
      ctx.font = 'bold 11px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('AWAITING SLAM OCCUPANCY GRID (/map)...', width / 2, height / 2);
      return;
    }

    ctx.save();
    ctx.translate(width / 2 + pan.x, height / 2 + pan.y);
    ctx.scale(zoom, zoom);

    const mapW = mapData.width;
    const mapH = mapData.height;
    const res = mapData.resolution;
    const originX = mapData.originX;
    const originY = mapData.originY;

    const imgData = ctx.createImageData(mapW, mapH);
    const buf = imgData.data;

    for (let y = 0; y < mapH; y++) {
      for (let x = 0; x < mapW; x++) {
        const val = mapData.data[y * mapW + x];
        const canvasY = mapH - 1 - y;
        const idx = (canvasY * mapW + x) * 4;

        if (val === -1) {
          buf[idx] = 10;
          buf[idx + 1] = 14;
          buf[idx + 2] = 34;
          buf[idx + 3] = 255;
        } else if (val === 0) {
          buf[idx] = 226;
          buf[idx + 1] = 232;
          buf[idx + 2] = 240;
          buf[idx + 3] = 255;
        } else if (val > 50) {
          buf[idx] = 0;
          buf[idx + 1] = 0;
          buf[idx + 2] = 0;
          buf[idx + 3] = 255;
        } else {
          buf[idx] = 100;
          buf[idx + 1] = 116;
          buf[idx + 2] = 139;
          buf[idx + 3] = 255;
        }
      }
    }

    const offCanvas = document.createElement('canvas');
    offCanvas.width = mapW;
    offCanvas.height = mapH;
    const offCtx = offCanvas.getContext('2d');
    if (offCtx) {
      offCtx.putImageData(imgData, 0, 0);
      const drawX = -mapW / 2;
      const drawY = -mapH / 2;
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(offCanvas, drawX, drawY);

      const worldToCanvas = (wx: number, wy: number) => ({
        px: (wx - originX) / res + drawX,
        py: mapH - (wy - originY) / res + drawY,
      });

      // Nav2 planned path
      if (plan && plan.length > 1) {
        ctx.strokeStyle = '#00FF00';
        ctx.lineWidth = 3 / zoom;
        ctx.beginPath();
        for (let i = 0; i < plan.length; i++) {
          const pt = worldToCanvas(plan[i].x, plan[i].y);
          if (i === 0) ctx.moveTo(pt.px, pt.py);
          else ctx.lineTo(pt.px, pt.py);
        }
        ctx.stroke();
      }

      // Selected Nav2 Goal
      if (selectedGoal) {
        const g = worldToCanvas(selectedGoal.x, selectedGoal.y);
        const sz = 7 / zoom;
        ctx.fillStyle = '#FFFF00';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 2 / zoom;
        ctx.fillRect(g.px - sz / 2, g.py - sz / 2, sz, sz);
        ctx.strokeRect(g.px - sz / 2, g.py - sz / 2, sz, sz);
      }

      // Robot Pose + Yaw arrow
      if (odom) {
        const rp = worldToCanvas(odom.x, odom.y);
        const rSz = 8 / zoom;
        ctx.fillStyle = '#0000FF';
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 2 / zoom;
        ctx.fillRect(rp.px - rSz / 2, rp.py - rSz / 2, rSz, rSz);
        ctx.strokeRect(rp.px - rSz / 2, rp.py - rSz / 2, rSz, rSz);

        const len = 14 / zoom;
        ctx.strokeStyle = '#FF0000';
        ctx.lineWidth = 2.5 / zoom;
        ctx.beginPath();
        ctx.moveTo(rp.px, rp.py);
        ctx.lineTo(rp.px + len * Math.cos(-odom.yaw), rp.py + len * Math.sin(-odom.yaw));
        ctx.stroke();
      }
    }

    ctx.restore();
  }, [mapData, odom, plan, selectedGoal, zoom, pan]);

  useEffect(() => {
    renderMap();
  }, [renderMap]);

  const handlePointerDown = (e: React.PointerEvent) => {
    setIsPanning(true);
    dragStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y, moved: false };
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isPanning) return;
    const nx = e.clientX - dragStartRef.current.x;
    const ny = e.clientY - dragStartRef.current.y;
    if (Math.hypot(nx - pan.x, ny - pan.y) > 4) {
      dragStartRef.current.moved = true;
    }
    setPan({ x: nx, y: ny });
  };

  const handlePointerUp = () => {
    setIsPanning(false);
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (dragStartRef.current.moved) return;
    if (!mapData || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const scaleX = canvasRef.current.width / rect.width;
    const scaleY = canvasRef.current.height / rect.height;
    const clickX = (e.clientX - rect.left) * scaleX;
    const clickY = (e.clientY - rect.top) * scaleY;

    const mapW = mapData.width;
    const mapH = mapData.height;
    const drawX = -mapW / 2;
    const drawY = -mapH / 2;

    const canvasTransX = (clickX - (canvasRef.current.width / 2 + pan.x)) / zoom;
    const canvasTransY = (clickY - (canvasRef.current.height / 2 + pan.y)) / zoom;
    const mapPixelX = canvasTransX - drawX;
    const mapPixelY = mapH - (canvasTransY - drawY);

    const worldX = mapData.originX + mapPixelX * mapData.resolution;
    const worldY = mapData.originY + mapPixelY * mapData.resolution;
    soundEffects.playClick();
    onSelectGoal({ x: parseFloat(worldX.toFixed(2)), y: parseFloat(worldY.toFixed(2)) });
  };

  const resStr = mapData ? mapData.resolution.toFixed(2) : '0.05';
  const sizeStr = mapData ? `${mapData.width} x ${mapData.height}` : '-- x --';
  const areaStr = coverage ? `${coverage.known_area_m2}` : '--';

  return (
    <div className="pixel-panel bg-[#080818] flex flex-col">
      <div className="pixel-header px-2.5 py-1 flex items-center justify-between gap-2">
        <span className="font-pixel text-[8px] sm:text-[9px] text-white flex items-center gap-1.5 truncate">
          <Map className="w-3.5 h-3.5 shrink-0" />
          <span>SLAM MAP (OCCUPANCY GRID)</span>
        </span>
        {goalPickArmed && (
          <span className="px-1.5 py-0.5 bg-[#FFFF00] text-black font-pixel text-[7px] border border-black">
            TAP MAP FOR GOAL
          </span>
        )}
      </div>

      <div className={`relative w-full ${heightClass} bg-[#06081A] overflow-hidden touch-none`}>
        <canvas
          ref={canvasRef}
          width={560}
          height={260}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onClick={handleCanvasClick}
          className="w-full h-full cursor-crosshair block"
        />

        {/* Retro Map Zoom Controls (Left Stack matching Desktop Reference) */}
        <div className="absolute top-2 left-2 flex flex-col gap-1">
          <button
            type="button"
            onClick={() => {
              soundEffects.playClick();
              setZoom(z => Math.min(4.0, z * 1.25));
            }}
            aria-label="Zoom in map"
            className="pixel-btn w-7 h-7 bg-[#11112B] text-white flex items-center justify-center"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => {
              soundEffects.playClick();
              setZoom(z => Math.max(0.25, z / 1.25));
            }}
            aria-label="Zoom out map"
            className="pixel-btn w-7 h-7 bg-[#11112B] text-white flex items-center justify-center"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => {
              soundEffects.playClick();
              setZoom(0.65);
              setPan({ x: 0, y: 0 });
            }}
            aria-label="Reset map view"
            className="pixel-btn w-7 h-7 bg-[#11112B] text-white flex items-center justify-center"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="px-2.5 py-1 bg-[#0F0F23] border-t-2 border-white/50 font-mono text-[9px] sm:text-[10px] font-bold text-slate-200 flex items-center justify-between flex-wrap gap-1">
        <span>RES: {resStr} m/pixel</span>
        <span>|</span>
        <span>SIZE: {sizeStr}</span>
        <span>|</span>
        <span>AREA: {areaStr} m&sup2;</span>
      </div>
    </div>
  );
};

