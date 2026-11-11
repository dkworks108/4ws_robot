import React, { useState, useRef, useEffect, useCallback } from 'react';
import { manualInputPipeline } from '../services/manualInputPipeline';
import { PixelRotateIcon } from './PixelIcons';
import { Handedness } from '../types/ros';

interface JoystickControlProps {
  disabled: boolean;
  compact?: boolean;
  handedness?: Handedness;
  showVelocityRow?: boolean;
  vxFeedback?: number;
  vyFeedback?: number;
  wzFeedback?: number;
}

export const JoystickControl: React.FC<JoystickControlProps> = ({
  disabled,
  compact = false,
  handedness = 'right',
  showVelocityRow = false,
  vxFeedback = 0,
  vyFeedback = 0,
  wzFeedback = 0,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [knobPos, setKnobPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const isDraggingRef = useRef(false);
  const latestVecRef = useRef<{ vx: number; vy: number }>({ vx: 0, vy: 0 });
  const activeRotRef = useRef<number>(0);
  const [activeRot, setActiveRot] = useState<number>(0);

  const padSize = compact ? 156 : 196;
  const maxRadius = compact ? 52 : 66;
  const deadZone = 0.08;

  const pushCommand = useCallback(
    (active: boolean, vx: number, vy: number, wz: number) => {
      if (disabled || !active) {
        manualInputPipeline.setJoystickCommand(false, 0, 0, 0);
        return;
      }
      manualInputPipeline.setJoystickCommand(true, vx, vy, wz);
    },
    [disabled]
  );

  const handleStopDrag = useCallback(() => {
    isDraggingRef.current = false;
    setIsDragging(false);
    setKnobPos({ x: 0, y: 0 });
    latestVecRef.current = { vx: 0, vy: 0 };
    if (activeRotRef.current !== 0 && !disabled) {
      pushCommand(true, 0, 0, activeRotRef.current);
    } else {
      pushCommand(false, 0, 0, 0);
    }
  }, [disabled, pushCommand]);

  const updateFromPointer = (clientX: number, clientY: number) => {
    if (!containerRef.current || disabled) return;
    const rect = containerRef.current.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = clientX - cx;
    const dy = clientY - cy;
    const dist = Math.hypot(dx, dy);

    let clampedX = dx;
    let clampedY = dy;
    if (dist > maxRadius) {
      clampedX = (dx / dist) * maxRadius;
      clampedY = (dy / dist) * maxRadius;
    }

    setKnobPos({ x: clampedX, y: clampedY });

    // Apply dead-zone cleanly
    let normX = -clampedY / maxRadius; // +vx forward
    let normY = -clampedX / maxRadius; // +vy left
    if (Math.hypot(normX, normY) < deadZone) {
      normX = 0;
      normY = 0;
    }

    const maxLinear = 1.0;
    const vx = parseFloat((normX * maxLinear).toFixed(3));
    const vy = parseFloat((normY * maxLinear).toFixed(3));
    latestVecRef.current = { vx, vy };
    pushCommand(true, vx, vy, activeRotRef.current);
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    if (disabled) return;
    e.preventDefault();
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    isDraggingRef.current = true;
    setIsDragging(true);
    updateFromPointer(e.clientX, e.clientY);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDraggingRef.current || disabled) return;
    e.preventDefault();
    updateFromPointer(e.clientX, e.clientY);
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (isDraggingRef.current) {
      try {
        (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        // ignore
      }
      handleStopDrag();
    }
  };

  const startRotation = (wz: number) => {
    if (disabled) return;
    activeRotRef.current = wz;
    setActiveRot(wz);
    pushCommand(true, latestVecRef.current.vx, latestVecRef.current.vy, wz);
  };

  const stopRotation = () => {
    if (activeRotRef.current === 0) return;
    activeRotRef.current = 0;
    setActiveRot(0);
    if (isDraggingRef.current && !disabled) {
      pushCommand(true, latestVecRef.current.vx, latestVecRef.current.vy, 0);
    } else {
      pushCommand(false, 0, 0, 0);
    }
  };

  useEffect(() => {
    if (disabled) {
      activeRotRef.current = 0;
      setActiveRot(0);
      isDraggingRef.current = false;
      setIsDragging(false);
      setKnobPos({ x: 0, y: 0 });
      latestVecRef.current = { vx: 0, vy: 0 };
      manualInputPipeline.setJoystickCommand(false, 0, 0, 0);
    }
  }, [disabled]);

  const rotationColumn = (
    <div className="flex flex-col gap-2.5 justify-center">
      <button
        type="button"
        disabled={disabled}
        onPointerDown={() => startRotation(1.2)}
        onPointerUp={stopRotation}
        onPointerLeave={stopRotation}
        onPointerCancel={stopRotation}
        aria-label="Hold to rotate counter-clockwise"
        className={`pixel-btn ${
          compact ? 'w-14 h-14' : 'w-16 h-16'
        } flex flex-col items-center justify-center gap-1 font-pixel text-[8px] touch-none ${
          activeRot > 0
            ? 'bg-[#FFFF00] text-black border-black'
            : 'bg-[#080818] text-white border-white hover:bg-[#141436]'
        } ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
      >
        <PixelRotateIcon dir="ccw" className="w-5 h-5" />
        <span>CCW</span>
      </button>

      <button
        type="button"
        disabled={disabled}
        onPointerDown={() => startRotation(-1.2)}
        onPointerUp={stopRotation}
        onPointerLeave={stopRotation}
        onPointerCancel={stopRotation}
        aria-label="Hold to rotate clockwise"
        className={`pixel-btn ${
          compact ? 'w-14 h-14' : 'w-16 h-16'
        } flex flex-col items-center justify-center gap-1 font-pixel text-[8px] touch-none ${
          activeRot < 0
            ? 'bg-[#FFFF00] text-black border-black'
            : 'bg-[#080818] text-white border-white hover:bg-[#141436]'
        } ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
      >
        <PixelRotateIcon dir="cw" className="w-5 h-5" />
        <span>CW</span>
      </button>
    </div>
  );

  const joystickPad = (
    <div
      ref={containerRef}
      role="slider"
      aria-label="Omnidirectional Manual Control Joystick"
      aria-valuetext={`X ${latestVecRef.current.vx}, Y ${latestVecRef.current.vy}`}
      tabIndex={disabled ? -1 : 0}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      style={{ width: padSize, height: padSize }}
      className={`relative rounded-full touch-none select-none flex items-center justify-center shrink-0 ${
        disabled ? 'opacity-45 cursor-not-allowed' : 'cursor-grab active:cursor-grabbing'
      }`}
    >
      {/* Retro Pixelated Outer Blue Ring SVG */}
      <svg
        viewBox="0 0 128 128"
        className="absolute inset-0 w-full h-full pointer-events-none"
        shapeRendering="crispEdges"
      >
        {/* Outer bright blue pixel ring */}
        <circle cx="64" cy="64" r="60" fill="#060B28" stroke="#1E78FF" strokeWidth="6" />
        <circle cx="64" cy="64" r="53" fill="#091645" stroke="#0038A8" strokeWidth="3" />
        {/* Pixelated Crosshair Lines */}
        <line x1="64" y1="18" x2="64" y2="110" stroke="#1E40AF" strokeWidth="2" strokeDasharray="4 4" />
        <line x1="18" y1="64" x2="110" y2="64" stroke="#1E40AF" strokeWidth="2" strokeDasharray="4 4" />
        {/* 4 White Pixel Directional Arrows */}
        {/* Up */}
        <polygon points="64,12 56,22 61,22 61,32 67,32 67,22 72,22" fill="#FFFFFF" />
        {/* Down */}
        <polygon points="64,116 56,106 61,106 61,96 67,96 67,106 72,106" fill="#FFFFFF" />
        {/* Left */}
        <polygon points="12,64 22,56 22,61 32,61 32,67 22,67 22,72" fill="#FFFFFF" />
        {/* Right */}
        <polygon points="116,64 106,56 106,61 96,61 96,67 106,67 106,72" fill="#FFFFFF" />
      </svg>

      {/* Pixelated Yellow Thumb Sphere */}
      <div
        style={{
          transform: `translate3d(${knobPos.x}px, ${knobPos.y}px, 0)`,
          width: compact ? 50 : 60,
          height: compact ? 50 : 60,
        }}
        className={`relative pointer-events-none ${
          isDragging ? 'scale-105' : 'transition-transform duration-75'
        }`}
      >
        <svg viewBox="0 0 32 32" className="w-full h-full drop-shadow-[2px_3px_0_#000000]" shapeRendering="crispEdges">
          <circle cx="16" cy="16" r="14" fill="#EAB308" stroke="#000000" strokeWidth="2.5" />
          <circle cx="15" cy="15" r="10.5" fill="#FFFF00" />
          {/* Pixel specular highlight */}
          <rect x="9" y="8" width="5" height="3" fill="#FFFFFF" />
          <rect x="8" y="11" width="3" height="3" fill="#FFFFFF" />
        </svg>
      </div>
    </div>
  );

  // Mobile order flips cleanly when handedness changes
  const isLeftHandedMobile = compact && handedness === 'left';

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-center gap-3 sm:gap-4">
        {isLeftHandedMobile ? (
          <>
            {joystickPad}
            {rotationColumn}
          </>
        ) : compact ? (
          <>
            {rotationColumn}
            {joystickPad}
          </>
        ) : (
          <>
            {joystickPad}
            {rotationColumn}
          </>
        )}
      </div>

      {showVelocityRow && (
        <div className="grid grid-cols-3 gap-1.5 pt-1">
          <div className="bg-[#0F0F23] border-2 border-white/60 px-2 py-1 text-center">
            <div className="font-mono text-[9px] text-slate-300">Vx</div>
            <div className="font-mono text-xs font-extrabold text-[#FFFF00]">
              {vxFeedback.toFixed(2)} m/s
            </div>
          </div>
          <div className="bg-[#0F0F23] border-2 border-white/60 px-2 py-1 text-center">
            <div className="font-mono text-[9px] text-slate-300">Vy</div>
            <div className="font-mono text-xs font-extrabold text-[#FFFF00]">
              {vyFeedback.toFixed(2)} m/s
            </div>
          </div>
          <div className="bg-[#0F0F23] border-2 border-white/60 px-2 py-1 text-center">
            <div className="font-mono text-[9px] text-slate-300">&omega;Z</div>
            <div className="font-mono text-xs font-extrabold text-[#FFFF00]">
              {wzFeedback.toFixed(2)} rad/s
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
