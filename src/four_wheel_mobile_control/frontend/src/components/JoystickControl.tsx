import React, { useState, useRef, useEffect, useCallback } from 'react';
import { rosService } from '../services/rosService';
import { RotateCcw, RotateCw, Gauge } from 'lucide-react';

interface JoystickControlProps {
  disabled: boolean;
  speedLimit: number;
  onSpeedLimitChange: (limit: number) => void;
}

export const JoystickControl: React.FC<JoystickControlProps> = ({
  disabled,
  speedLimit,
  onSpeedLimitChange
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [knobPos, setKnobPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [currentCmd, setCurrentCmd] = useState<{ vx: number; vy: number; wz: number }>({
    vx: 0,
    vy: 0,
    wz: 0
  });

  const [activeRotation, setActiveRotation] = useState<number>(0);
  const rotationTimerRef = useRef<any>(null);
  const dragTimerRef = useRef<any>(null);
  const isDraggingRef = useRef<boolean>(false);
  const latestCmdRef = useRef<{ vx: number; vy: number; wz: number }>({ vx: 0, vy: 0, wz: 0 });

  const radius = 70; // Joystick boundary radius in px

  const emitVelocity = useCallback((vx: number, vy: number, wz: number) => {
    if (disabled) {
      rosService.sendVelocity(0, 0, 0);
      latestCmdRef.current = { vx: 0, vy: 0, wz: 0 };
      setCurrentCmd({ vx: 0, vy: 0, wz: 0 });
      return;
    }
    rosService.sendVelocity(vx, vy, wz);
    latestCmdRef.current = { vx, vy, wz };
    setCurrentCmd({ vx, vy, wz });
  }, [disabled]);

  // Dead-man reset
  const handleStop = useCallback(() => {
    isDraggingRef.current = false;
    setIsDragging(false);
    if (dragTimerRef.current) {
      clearInterval(dragTimerRef.current);
      dragTimerRef.current = null;
    }
    setKnobPos({ x: 0, y: 0 });
    emitVelocity(0, 0, 0);
  }, [emitVelocity]);

  // Pointer event handlers for cross-platform touch/mouse
  const handlePointerDown = (e: React.PointerEvent) => {
    if (disabled) return;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    isDraggingRef.current = true;
    setIsDragging(true);
    handlePointerMove(e);
    if (dragTimerRef.current) clearInterval(dragTimerRef.current);
    dragTimerRef.current = setInterval(() => {
      if (isDraggingRef.current && !disabled) {
        const { vx, vy, wz } = latestCmdRef.current;
        rosService.sendVelocity(vx, vy, wz);
      }
    }, 100);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDraggingRef.current || disabled || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const dx = e.clientX - centerX;
    const dy = e.clientY - centerY;
    const distance = Math.hypot(dx, dy);

    let clampedX = dx;
    let clampedY = dy;
    if (distance > radius) {
      clampedX = (dx / distance) * radius;
      clampedY = (dy / distance) * radius;
    }

    setKnobPos({ x: clampedX, y: clampedY });

    // Normalize: -1.0 to +1.0
    // In robot frame: Forward is +X (upwards on joystick, so -dy), Left is +Y (left on joystick, so -dx)
    const normVx = -clampedY / radius;
    const normVy = -clampedX / radius;

    // Standard base max linear speed: 1.0 m/s
    const maxLinear = 1.0;
    const vx = parseFloat((normVx * maxLinear).toFixed(3));
    const vy = parseFloat((normVy * maxLinear).toFixed(3));

    emitVelocity(vx, vy, activeRotation);
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (isDraggingRef.current) {
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {}
      handleStop();
    }
  };

  // Rotation controls (CCW / CW)
  const startRotation = (wz: number) => {
    if (disabled) return;
    setActiveRotation(wz);
    emitVelocity(latestCmdRef.current.vx, latestCmdRef.current.vy, wz);

    if (rotationTimerRef.current) clearInterval(rotationTimerRef.current);
    rotationTimerRef.current = setInterval(() => {
      emitVelocity(latestCmdRef.current.vx, latestCmdRef.current.vy, wz);
    }, 100);
  };

  const stopRotation = () => {
    if (rotationTimerRef.current) {
      clearInterval(rotationTimerRef.current);
      rotationTimerRef.current = null;
    }
    setActiveRotation(0);
    emitVelocity(latestCmdRef.current.vx, latestCmdRef.current.vy, 0);
  };

  useEffect(() => {
    if (disabled) {
      handleStop();
      if (rotationTimerRef.current) {
        clearInterval(rotationTimerRef.current);
        rotationTimerRef.current = null;
      }
      setActiveRotation(0);
    }
  }, [disabled, handleStop]);

  useEffect(() => {
    return () => {
      if (rotationTimerRef.current) clearInterval(rotationTimerRef.current);
      if (dragTimerRef.current) clearInterval(dragTimerRef.current);
      rosService.sendVelocity(0, 0, 0);
    };
  }, []);

  return (
    <div className="w-full bg-gray-950 p-4 rounded-2xl border border-gray-800 flex flex-col items-center">
      {/* Header and Speed Limits */}
      <div className="w-full flex items-center justify-between mb-3">
        <span className="text-xs font-mono font-bold text-gray-400 tracking-wider flex items-center gap-1.5">
          <Gauge className="w-4 h-4 text-cyan-400" />
          SPEED LIMIT
        </span>
        <div className="flex gap-1 bg-gray-900 p-1 rounded-xl border border-gray-800">
          {[0.25, 0.5, 0.75, 1.0].map(val => (
            <button
              key={val}
              disabled={disabled}
              onClick={() => onSpeedLimitChange(val)}
              className={`px-2 py-0.5 text-xs font-mono font-bold rounded-lg transition-all ${
                speedLimit === val
                  ? 'bg-cyan-500 text-black shadow-[0_0_8px_rgba(6,182,212,0.4)]'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {val * 100}%
            </button>
          ))}
        </div>
      </div>

      {/* Main Joystick Pad and Rotation Controls */}
      <div className="w-full flex items-center justify-around gap-2 my-2">
        {/* Rotate Counter-Clockwise Button */}
        <button
          disabled={disabled}
          onPointerDown={() => startRotation(1.2)}
          onPointerUp={stopRotation}
          onPointerLeave={stopRotation}
          className="p-3.5 rounded-2xl bg-gray-900 border border-gray-800 text-cyan-400 active:bg-cyan-500/20 active:border-cyan-400 active:scale-95 transition-all flex flex-col items-center gap-1 shadow-lg"
          title="Hold to rotate Counter-Clockwise (Yaw Left)"
        >
          <RotateCcw className="w-6 h-6" />
          <span className="text-[10px] font-mono font-bold">CCW</span>
        </button>

        {/* Omnidirectional Virtual Joystick Base */}
        <div
          ref={containerRef}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          className={`relative w-44 h-44 rounded-full bg-gradient-to-b from-gray-900 to-gray-950 border-2 ${
            disabled ? 'border-gray-800 opacity-50' : 'border-cyan-500/40 shadow-[0_0_20px_rgba(6,182,212,0.15)]'
          } flex items-center justify-center touch-none select-none`}
        >
          {/* Concentric Guide Rings */}
          <div className="absolute w-32 h-32 rounded-full border border-gray-800/80 pointer-events-none" />
          <div className="absolute w-20 h-20 rounded-full border border-gray-800/80 pointer-events-none" />
          <div className="absolute w-full h-[1px] bg-gray-800/50 pointer-events-none" />
          <div className="absolute h-full w-[1px] bg-gray-800/50 pointer-events-none" />

          {/* Directional Labels */}
          <span className="absolute top-1 text-[9px] font-mono text-gray-500">FWD</span>
          <span className="absolute bottom-1 text-[9px] font-mono text-gray-500">REV</span>
          <span className="absolute left-1.5 text-[9px] font-mono text-gray-500">LFT</span>
          <span className="absolute right-1.5 text-[9px] font-mono text-gray-500">RGT</span>

          {/* Joystick Floating Knob */}
          <div
            style={{
              transform: `translate(${knobPos.x}px, ${knobPos.y}px)`,
              transition: isDragging ? 'none' : 'transform 0.15s cubic-bezier(0.2, 0.8, 0.2, 1)'
            }}
            className={`w-14 h-14 rounded-full bg-gradient-to-b from-cyan-400 to-cyan-600 border-2 border-cyan-200 shadow-[0_0_15px_rgba(6,182,212,0.5)] flex items-center justify-center pointer-events-none ${
              isDragging ? 'scale-105' : ''
            }`}
          >
            <div className="w-4 h-4 rounded-full bg-cyan-950/60 border border-cyan-200" />
          </div>
        </div>

        {/* Rotate Clockwise Button */}
        <button
          disabled={disabled}
          onPointerDown={() => startRotation(-1.2)}
          onPointerUp={stopRotation}
          onPointerLeave={stopRotation}
          className="p-3.5 rounded-2xl bg-gray-900 border border-gray-800 text-cyan-400 active:bg-cyan-500/20 active:border-cyan-400 active:scale-95 transition-all flex flex-col items-center gap-1 shadow-lg"
          title="Hold to rotate Clockwise (Yaw Right)"
        >
          <RotateCw className="w-6 h-6" />
          <span className="text-[10px] font-mono font-bold">CW</span>
        </button>
      </div>

      {/* Telemetry Readout */}
      <div className="w-full grid grid-cols-3 gap-2 mt-2 pt-2 border-t border-gray-900 text-center font-mono">
        <div className="bg-gray-900/60 p-1.5 rounded-lg">
          <div className="text-[9px] text-gray-500">LIN X</div>
          <div className="text-xs font-bold text-white">{(currentCmd.vx * speedLimit).toFixed(2)} m/s</div>
        </div>
        <div className="bg-gray-900/60 p-1.5 rounded-lg">
          <div className="text-[9px] text-gray-500">LIN Y (CRAB)</div>
          <div className="text-xs font-bold text-white">{(currentCmd.vy * speedLimit).toFixed(2)} m/s</div>
        </div>
        <div className="bg-gray-900/60 p-1.5 rounded-lg">
          <div className="text-[9px] text-gray-500">ANG Z (YAW)</div>
          <div className="text-xs font-bold text-white">{(currentCmd.wz * speedLimit).toFixed(2)} r/s</div>
        </div>
      </div>
    </div>
  );
};

