/**
 * Retro 8-Bit / 16-Bit Web Audio Sound Effects Synthesizer for 4WS Ground Control.
 * Zero external audio assets required; respects user mute preference.
 */

const STORAGE_KEY_MUTE = '4ws_sfx_muted';

class RetroSoundEffects {
  private ctx: AudioContext | null = null;
  private muted: boolean = false;

  constructor() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_MUTE);
      this.muted = saved === 'true';
    } catch {
      this.muted = false;
    }
  }

  public isMuted(): boolean {
    return this.muted;
  }

  public setMuted(mute: boolean): void {
    this.muted = mute;
    try {
      localStorage.setItem(STORAGE_KEY_MUTE, String(mute));
    } catch {
      // ignore storage failure
    }
  }

  public toggleMute(): boolean {
    this.setMuted(!this.muted);
    if (!this.muted) {
      this.playClick();
    }
    return this.muted;
  }

  private getContext(): AudioContext | null {
    if (this.muted || typeof window === 'undefined') return null;
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return null;
      if (!this.ctx) {
        this.ctx = new AudioCtx();
      }
      if (this.ctx.state === 'suspended') {
        this.ctx.resume().catch(() => {});
      }
      return this.ctx;
    } catch {
      return null;
    }
  }

  private playTone(
    freq: number,
    durationSec: number,
    type: OscillatorType = 'square',
    gainLevel: number = 0.06,
    delaySec: number = 0,
    endFreq?: number
  ) {
    const ctx = this.getContext();
    if (!ctx) return;
    try {
      const now = ctx.currentTime + delaySec;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, now);
      if (endFreq !== undefined) {
        osc.frequency.exponentialRampToValueAtTime(Math.max(20, endFreq), now + durationSec);
      }
      gain.gain.setValueAtTime(gainLevel, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + durationSec);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + durationSec + 0.01);
    } catch {
      // ignore audio errors
    }
  }

  public playClick() {
    this.playTone(740, 0.045, 'square', 0.045, 0, 920);
  }

  public playModeChange() {
    this.playTone(523.25, 0.055, 'square', 0.05, 0);
    this.playTone(659.25, 0.075, 'square', 0.05, 0.055);
  }

  public playAuthorityChange() {
    this.playTone(440, 0.05, 'square', 0.05, 0);
    this.playTone(554.37, 0.05, 'square', 0.05, 0.05);
    this.playTone(659.25, 0.08, 'square', 0.05, 0.10);
  }

  public playEstop() {
    this.playTone(880, 0.14, 'sawtooth', 0.09, 0, 320);
    this.playTone(660, 0.18, 'sawtooth', 0.09, 0.14, 180);
  }

  public playEstopReset() {
    this.playTone(392.0, 0.06, 'triangle', 0.06, 0);
    this.playTone(523.25, 0.06, 'triangle', 0.06, 0.065);
    this.playTone(783.99, 0.11, 'triangle', 0.06, 0.13);
  }

  public playGoalDispatch() {
    this.playTone(587.33, 0.06, 'square', 0.045, 0);
    this.playTone(880.0, 0.10, 'square', 0.05, 0.065);
  }

  public playKeyStop() {
    this.playTone(220, 0.07, 'triangle', 0.06, 0, 90);
  }

  public playConnect() {
    this.playTone(523.25, 0.06, 'triangle', 0.05, 0);
    this.playTone(1046.5, 0.10, 'triangle', 0.05, 0.065);
  }

  public playDisconnect() {
    this.playTone(440, 0.08, 'triangle', 0.05, 0, 220);
  }
}

export const soundEffects = new RetroSoundEffects();

