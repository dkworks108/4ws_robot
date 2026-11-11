import React from 'react';
import { SteeringMode } from '../types/ros';

export const PixelRobotLogo: React.FC<{ className?: string }> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 16 16" className={className} shapeRendering="crispEdges" aria-hidden="true">
    {/* Wheels */}
    <rect x="1" y="3" width="3" height="4" fill="#FFFFFF" />
    <rect x="12" y="3" width="3" height="4" fill="#FFFFFF" />
    <rect x="1" y="9" width="3" height="4" fill="#FFFFFF" />
    <rect x="12" y="9" width="3" height="4" fill="#FFFFFF" />
    {/* Chassis */}
    <rect x="4" y="2" width="8" height="12" fill="#0000FF" />
    <rect x="5" y="3" width="6" height="10" fill="#60A5FA" />
    {/* Mast / LiDAR */}
    <rect x="6" y="5" width="4" height="4" fill="#0F0F23" />
    <rect x="7" y="6" width="2" height="2" fill="#00FF00" />
    {/* Headlights */}
    <rect x="5" y="2" width="2" height="1" fill="#FFFF00" />
    <rect x="9" y="2" width="2" height="1" fill="#FFFF00" />
  </svg>
);

export const PixelSteeringDiagram: React.FC<{ mode: SteeringMode; active?: boolean }> = ({
  mode,
  active = false,
}) => {
  const wheelColor = active ? '#000000' : '#00FF00';
  const bodyColor = active ? '#0F0F23' : '#FFFFFF';

  const getAngles = (): [number, number, number, number] => {
    switch (mode) {
      case 'front_steer':
        return [-25, -20, 0, 0];
      case 'four_wheel_steer':
        return [-25, -25, 25, 25];
      case 'crab':
        return [35, 35, 35, 35];
      case 'generalized':
        return [-35, -15, 20, 40];
      case 'in_place_spin':
        return [-45, 45, 45, -45];
    }
  };

  const [fl, fr, rl, rr] = getAngles();
  const wheels = [
    { x: 6, y: 6, deg: fl },
    { x: 22, y: 6, deg: fr },
    { x: 6, y: 18, deg: rl },
    { x: 22, y: 18, deg: rr },
  ];

  return (
    <svg viewBox="0 0 28 24" className="w-8 h-7 shrink-0" shapeRendering="crispEdges" aria-hidden="true">
      {/* Axles */}
      <line x1="6" y1="6" x2="22" y2="6" stroke={bodyColor} strokeWidth="1.5" />
      <line x1="6" y1="18" x2="22" y2="18" stroke={bodyColor} strokeWidth="1.5" />
      <line x1="14" y1="6" x2="14" y2="18" stroke={bodyColor} strokeWidth="1.5" />
      {/* Wheels */}
      {wheels.map((w, i) => (
        <g key={i} transform={`translate(${w.x}, ${w.y}) rotate(${w.deg})`}>
          <rect x="-2" y="-4" width="4" height="8" fill={wheelColor} stroke={bodyColor} strokeWidth="1" />
        </g>
      ))}
    </svg>
  );
};

export const PixelShieldIcon: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 16 16" className={className} shapeRendering="crispEdges" aria-hidden="true">
    <path d="M2 2h12v6c0 4-6 6-6 6s-6-2-6-6V2z" fill="#FFFFFF" />
    <path d="M4 4h8v4c0 2.5-4 4-4 4s-4-1.5-4-4V4z" fill="#FF0000" />
    <rect x="7" y="5" width="2" height="3" fill="#FFFFFF" />
    <rect x="7" y="9" width="2" height="1" fill="#FFFFFF" />
  </svg>
);

export const PixelWarningIcon: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 16 16" className={className} shapeRendering="crispEdges" aria-hidden="true">
    <polygon points="8,1 15,14 1,14" fill="#FFFFFF" />
    <rect x="7" y="5" width="2" height="5" fill="#FF0000" />
    <rect x="7" y="11" width="2" height="2" fill="#FF0000" />
  </svg>
);

export const PixelGamepadIcon: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 16 16" className={className} shapeRendering="crispEdges" aria-hidden="true">
    <rect x="1" y="4" width="14" height="8" fill="currentColor" />
    <rect x="3" y="7" width="4" height="2" fill="#0F0F23" />
    <rect x="4" y="6" width="2" height="4" fill="#0F0F23" />
    <rect x="10" y="6" width="2" height="2" fill="#FF0000" />
    <rect x="12" y="8" width="2" height="2" fill="#00FF00" />
  </svg>
);

export const PixelNavIcon: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 16 16" className={className} shapeRendering="crispEdges" aria-hidden="true">
    <polygon points="2,8 14,2 10,14 8,9" fill="currentColor" />
  </svg>
);

export const PixelExploreIcon: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 16 16" className={className} shapeRendering="crispEdges" aria-hidden="true">
    <polygon points="8,2 15,6 8,10 1,6" fill="currentColor" />
    <polyline points="2,9 8,12 14,9" fill="none" stroke="currentColor" strokeWidth="1.5" />
    <polyline points="2,12 8,15 14,12" fill="none" stroke="currentColor" strokeWidth="1.5" />
  </svg>
);

export const PixelRotateIcon: React.FC<{ dir: 'ccw' | 'cw'; className?: string }> = ({
  dir,
  className = 'w-5 h-5',
}) => (
  <svg
    viewBox="0 0 16 16"
    className={className}
    shapeRendering="crispEdges"
    style={{ transform: dir === 'cw' ? 'scaleX(-1)' : undefined }}
    aria-hidden="true"
  >
    <path d="M8 2a6 6 0 1 1-5 9" fill="none" stroke="currentColor" strokeWidth="2" />
    <polygon points="2,2 2,7 7,4" fill="currentColor" />
  </svg>
);

export const PixelSoundIcon: React.FC<{ muted: boolean; className?: string }> = ({
  muted,
  className = 'w-4 h-4',
}) => (
  <svg viewBox="0 0 16 16" className={className} shapeRendering="crispEdges" aria-hidden="true">
    <polygon points="2,6 6,6 10,2 10,14 6,10 2,10" fill="currentColor" />
    {muted ? (
      <>
        <line x1="12" y1="5" x2="15" y2="11" stroke="#FF0000" strokeWidth="2" />
        <line x1="15" y1="5" x2="12" y2="11" stroke="#FF0000" strokeWidth="2" />
      </>
    ) : (
      <>
        <rect x="12" y="5" width="1.5" height="6" fill="#00FF00" />
        <rect x="14" y="3" width="1.5" height="10" fill="#00FF00" />
      </>
    )}
  </svg>
);

export const PixelImuTriad: React.FC<{ className?: string }> = ({ className = 'w-14 h-14' }) => (
  <svg viewBox="0 0 32 32" className={className} shapeRendering="crispEdges" aria-hidden="true">
    {/* Z axis (blue up) */}
    <line x1="14" y1="20" x2="14" y2="4" stroke="#38BDF8" strokeWidth="2.5" />
    <polygon points="14,1 10,7 18,7" fill="#38BDF8" />
    <text x="17" y="8" fill="#38BDF8" fontSize="7" fontFamily="monospace" fontWeight="bold">Z</text>
    {/* Y axis (green up-right) */}
    <line x1="14" y1="20" x2="25" y2="12" stroke="#00FF00" strokeWidth="2.5" />
    <polygon points="28,10 21,11 25,16" fill="#00FF00" />
    <text x="24" y="9" fill="#00FF00" fontSize="7" fontFamily="monospace" fontWeight="bold">Y</text>
    {/* X axis (red down-right) */}
    <line x1="14" y1="20" x2="26" y2="26" stroke="#FF0000" strokeWidth="2.5" />
    <polygon points="29,27 22,28 24,22" fill="#FF0000" />
    <text x="26" y="24" fill="#FF0000" fontSize="7" fontFamily="monospace" fontWeight="bold">X</text>
    {/* Origin */}
    <rect x="12" y="18" width="4" height="4" fill="#FFFFFF" />
  </svg>
);

