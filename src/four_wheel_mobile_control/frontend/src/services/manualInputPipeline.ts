import { rosService } from './rosService';
import {
  ActiveKeysState,
  ConnectionStatus,
  KeyboardControlState,
  OperatingMode,
} from '../types/ros';
import { soundEffects } from '../utils/soundEffects';

export interface ManualCommandSnapshot {
  vx: number;
  vy: number;
  wz: number;
  source: 'idle' | 'joystick' | 'keyboard';
  activeKeys: ActiveKeysState;
  keyboardStatus: KeyboardControlState;
}

const DEFAULT_KEYS: ActiveKeysState = {
  w: false,
  a: false,
  s: false,
  d: false,
  q: false,
  e: false,
  space: false,
};

const STORAGE_KB_ENABLED = '4ws_kb_enabled';
const STORAGE_KB_SENS = '4ws_kb_sensitivity';

class ManualInputPipeline {
  private listeners: Array<(snap: ManualCommandSnapshot) => void> = [];
  private timerId: any = null;

  // Environmental & Safety Gates
  private connectionStatus: ConnectionStatus = 'disconnected';
  private operatingMode: OperatingMode = 'MANUAL';
  private estopActive: boolean = false;
  private windowFocused: boolean = typeof document !== 'undefined' ? document.hasFocus() : true;
  private pageVisible: boolean = typeof document !== 'undefined' ? !document.hidden : true;

  // Keyboard Settings
  private keyboardEnabled: boolean = true;
  private keyboardSensitivity: number = 0.75; // 0.25 .. 1.0

  // Input Sources
  private joystickActive: boolean = false;
  private joystickVec = { vx: 0, vy: 0, wz: 0 };
  private keys: ActiveKeysState = { ...DEFAULT_KEYS };

  // Output State
  private lastPublished = { vx: 0, vy: 0, wz: 0 };
  private currentSource: 'idle' | 'joystick' | 'keyboard' = 'idle';

  constructor() {
    try {
      const en = localStorage.getItem(STORAGE_KB_ENABLED);
      if (en !== null) this.keyboardEnabled = en !== 'false';
      const sens = localStorage.getItem(STORAGE_KB_SENS);
      if (sens !== null) {
        const parsed = parseFloat(sens);
        if (!Number.isNaN(parsed) && parsed >= 0.25 && parsed <= 1.0) {
          this.keyboardSensitivity = parsed;
        }
      }
    } catch {
      // ignore storage errors
    }
  }

  public isManualAllowed(): boolean {
    return (
      this.connectionStatus === 'connected' &&
      this.operatingMode === 'MANUAL' &&
      !this.estopActive
    );
  }

  public getKeyboardStatus(): KeyboardControlState {
    if (this.connectionStatus !== 'connected') return 'DISCONNECTED';
    if (this.operatingMode !== 'MANUAL' || this.estopActive) return 'MANUAL AUTHORITY REQUIRED';
    if (!this.keyboardEnabled) return 'DISABLED';
    if (!this.windowFocused || !this.pageVisible) return 'WINDOW UNFOCUSED';
    return 'ENABLED';
  }

  public isKeyboardEnabled(): boolean {
    return this.keyboardEnabled;
  }

  public getKeyboardSensitivity(): number {
    return this.keyboardSensitivity;
  }

  public setKeyboardEnabled(enabled: boolean) {
    this.keyboardEnabled = enabled;
    try {
      localStorage.setItem(STORAGE_KB_ENABLED, String(enabled));
    } catch {
      // ignore
    }
    if (!enabled) {
      this.clearKeyboardKeys(true);
    }
    this.notify();
  }

  public setKeyboardSensitivity(sens: number) {
    const clamped = Math.max(0.25, Math.min(1.0, sens));
    this.keyboardSensitivity = clamped;
    try {
      localStorage.setItem(STORAGE_KB_SENS, String(clamped));
    } catch {
      // ignore
    }
    this.recomputeAndPublish();
  }

  public updateSystemState(
    connectionStatus: ConnectionStatus,
    operatingMode: OperatingMode,
    estopActive: boolean
  ) {
    const prevAllowed = this.isManualAllowed();
    this.connectionStatus = connectionStatus;
    this.operatingMode = operatingMode;
    this.estopActive = estopActive;

    const nowAllowed = this.isManualAllowed();
    if (prevAllowed && !nowAllowed) {
      this.forceStopAll();
    } else {
      this.notify();
    }
  }

  public setWindowFocus(focused: boolean) {
    this.windowFocused = focused;
    if (!focused) {
      this.clearKeyboardKeys(true);
    } else {
      this.notify();
    }
  }

  public setPageVisibility(visible: boolean) {
    this.pageVisible = visible;
    if (!visible) {
      this.clearKeyboardKeys(true);
    } else {
      this.notify();
    }
  }

  /**
   * Called by Desktop or Mobile Pointer Joystick / Rotation buttons.
   * Pointer joystick takes priority over keyboard while active.
   */
  public setJoystickCommand(active: boolean, vx: number, vy: number, wz: number) {
    if (!this.isManualAllowed()) {
      this.joystickActive = false;
      this.joystickVec = { vx: 0, vy: 0, wz: 0 };
      this.stopLoopAndSendZero();
      this.notify();
      return;
    }

    if (active) {
      // Neutralize any held keyboard keys cleanly when joystick takes over
      this.keys = { ...DEFAULT_KEYS };
      this.joystickActive = true;
      this.joystickVec = { vx, vy, wz };
    } else {
      this.joystickActive = false;
      this.joystickVec = { vx: 0, vy: 0, wz: 0 };
    }
    this.recomputeAndPublish();
  }

  /**
   * Handle physical keyboard KeyDown. Ignores editable form fields.
   */
  public handleKeyDown(e: KeyboardEvent): boolean {
    if (this.isEditableTarget(e.target)) return false;

    const key = e.key.toLowerCase();
    const isMovementKey = ['w', 'a', 's', 'd', 'q', 'e', ' '].includes(key) || e.code === 'Space';
    if (!isMovementKey) return false;

    // Spacebar always acts as immediate zero-velocity stop if keyboard enabled & manual
    if (e.code === 'Space' || key === ' ') {
      if (this.keyboardEnabled) {
        e.preventDefault();
        if (!e.repeat) {
          soundEffects.playKeyStop();
        }
        this.keys = { ...DEFAULT_KEYS, space: true };
        this.joystickActive = false;
        this.joystickVec = { vx: 0, vy: 0, wz: 0 };
        this.stopLoopAndSendZero();
        this.notify();
        return true;
      }
      return false;
    }

    if (typeof document !== 'undefined' && document.hasFocus()) {
      this.windowFocused = true;
      this.pageVisible = !document.hidden;
    }

    if (this.getKeyboardStatus() !== 'ENABLED') {
      return false;
    }

    // Prevent page scroll or button activation while driving
    e.preventDefault();
    if (e.repeat) return true;

    // If joystick was active, hand over safely to keyboard
    if (this.joystickActive) {
      this.joystickActive = false;
      this.joystickVec = { vx: 0, vy: 0, wz: 0 };
    }

    if (key === 'w') this.keys.w = true;
    if (key === 's') this.keys.s = true;
    if (key === 'a') this.keys.a = true;
    if (key === 'd') this.keys.d = true;
    if (key === 'q') this.keys.q = true;
    if (key === 'e') this.keys.e = true;
    this.keys.space = false;

    this.recomputeAndPublish();
    return true;
  }

  /**
   * Handle physical keyboard KeyUp.
   */
  public handleKeyUp(e: KeyboardEvent) {
    const key = e.key.toLowerCase();
    let changed = false;

    if (e.code === 'Space' || key === ' ') {
      if (this.keys.space) {
        this.keys.space = false;
        changed = true;
      }
    }
    if (key === 'w' && this.keys.w) { this.keys.w = false; changed = true; }
    if (key === 's' && this.keys.s) { this.keys.s = false; changed = true; }
    if (key === 'a' && this.keys.a) { this.keys.a = false; changed = true; }
    if (key === 'd' && this.keys.d) { this.keys.d = false; changed = true; }
    if (key === 'q' && this.keys.q) { this.keys.q = false; changed = true; }
    if (key === 'e' && this.keys.e) { this.keys.e = false; changed = true; }

    if (changed) {
      this.recomputeAndPublish();
    }
  }

  public clearKeyboardKeys(sendZero: boolean) {
    const hadAny =
      this.keys.w || this.keys.a || this.keys.s || this.keys.d || this.keys.q || this.keys.e || this.keys.space;
    this.keys = { ...DEFAULT_KEYS };
    if (hadAny && sendZero && !this.joystickActive) {
      this.stopLoopAndSendZero();
    }
    this.notify();
  }

  public forceStopAll() {
    this.keys = { ...DEFAULT_KEYS };
    this.joystickActive = false;
    this.joystickVec = { vx: 0, vy: 0, wz: 0 };
    this.stopLoopAndSendZero();
    this.notify();
  }

  private isEditableTarget(target: EventTarget | null): boolean {
    if (!target || !(target instanceof HTMLElement)) return false;
    const tag = target.tagName;
    return (
      tag === 'INPUT' ||
      tag === 'TEXTAREA' ||
      tag === 'SELECT' ||
      target.isContentEditable
    );
  }

  private computeKeyboardVelocity(): { vx: number; vy: number; wz: number; anyPressed: boolean } {
    const fwd = (this.keys.w ? 1 : 0) - (this.keys.s ? 1 : 0);
    const lat = (this.keys.a ? 1 : 0) - (this.keys.d ? 1 : 0);
    const yaw = (this.keys.q ? 1 : 0) - (this.keys.e ? 1 : 0);
    const anyPressed = fwd !== 0 || lat !== 0 || yaw !== 0;

    if (!anyPressed || this.getKeyboardStatus() !== 'ENABLED') {
      return { vx: 0, vy: 0, wz: 0, anyPressed: false };
    }

    // Normalize planar diagonal vector so W+A doesn't exceed 1.0x speed
    const mag = Math.hypot(fwd, lat);
    const nx = mag > 1.0 ? fwd / mag : fwd;
    const ny = mag > 1.0 ? lat / mag : lat;

    const maxLinear = 1.0 * this.keyboardSensitivity;
    const maxAngular = 1.2 * this.keyboardSensitivity;

    return {
      vx: parseFloat((nx * maxLinear).toFixed(3)),
      vy: parseFloat((ny * maxLinear).toFixed(3)),
      wz: parseFloat((yaw * maxAngular).toFixed(3)),
      anyPressed: true,
    };
  }

  private recomputeAndPublish() {
    if (!this.isManualAllowed()) {
      this.stopLoopAndSendZero();
      this.notify();
      return;
    }

    if (this.joystickActive) {
      this.currentSource = 'joystick';
      this.lastPublished = { ...this.joystickVec };
      this.publishAndEnsureLoop();
      this.notify();
      return;
    }

    const kb = this.computeKeyboardVelocity();
    if (kb.anyPressed) {
      this.currentSource = 'keyboard';
      this.lastPublished = { vx: kb.vx, vy: kb.vy, wz: kb.wz };
      this.publishAndEnsureLoop();
      this.notify();
      return;
    }

    this.stopLoopAndSendZero();
    this.notify();
  }

  private publishAndEnsureLoop() {
    rosService.sendVelocity(this.lastPublished.vx, this.lastPublished.vy, this.lastPublished.wz);
    if (!this.timerId) {
      // 10 Hz keep-alive publish to satisfy 400ms command arbiter watchdog
      this.timerId = setInterval(() => {
        if (!this.isManualAllowed() || this.currentSource === 'idle') {
          this.stopLoopAndSendZero();
          return;
        }
        rosService.sendVelocity(this.lastPublished.vx, this.lastPublished.vy, this.lastPublished.wz);
      }, 100);
    }
  }

  private stopLoopAndSendZero() {
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
    this.currentSource = 'idle';
    this.lastPublished = { vx: 0, vy: 0, wz: 0 };
    rosService.sendVelocity(0, 0, 0);
  }

  public getSnapshot(): ManualCommandSnapshot {
    return {
      vx: this.lastPublished.vx,
      vy: this.lastPublished.vy,
      wz: this.lastPublished.wz,
      source: this.currentSource,
      activeKeys: { ...this.keys },
      keyboardStatus: this.getKeyboardStatus(),
    };
  }

  public subscribe(cb: (snap: ManualCommandSnapshot) => void) {
    this.listeners.push(cb);
    cb(this.getSnapshot());
    return () => {
      this.listeners = this.listeners.filter(l => l !== cb);
    };
  }

  private notify() {
    const snap = this.getSnapshot();
    this.listeners.forEach(cb => cb(snap));
  }
}

export const manualInputPipeline = new ManualInputPipeline();
