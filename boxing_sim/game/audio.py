"""Procedurally synthesised sound - no audio files needed.

All samples are generated with numpy at startup, so the game ships as pure
source.  If the mixer cannot be initialised (headless CI, no sound card) every
call becomes a no-op.
"""
from __future__ import annotations

import math

import numpy as np

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None

SR = 22050


def _env(n, attack=0.005, decay=0.25, power=2.0):
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)
    a = int(max(1, attack * n))
    env = np.ones(n, np.float32)
    env[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32)
    env[a:] = np.linspace(1.0, 0.0, n - a, dtype=np.float32) ** power
    return env


def _noise(n, rng):
    return rng.standard_normal(n).astype(np.float32)


def _lowpass(x, alpha=0.2):
    out = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha * (x[i] - acc)
        out[i] = acc
    return out


def _tone(freq, n, sr=SR, kind="sine"):
    t = np.arange(n, dtype=np.float32) / sr
    if kind == "square":
        return np.sign(np.sin(2 * math.pi * freq * t)).astype(np.float32)
    return np.sin(2 * math.pi * freq * t).astype(np.float32)


class Audio:
    def __init__(self, enabled=True):
        self.ok = False
        self.enabled = enabled
        self.sounds = {}
        self.crowd_chan = None
        if not enabled or pygame is None:
            return
        try:
            pygame.mixer.pre_init(SR, -16, 2, 512)
            pygame.mixer.init()
            self.ok = True
        except Exception:
            self.ok = False
            return
        self._build()

    # ------------------------------------------------------------------
    def _mk(self, name, mono, volume=0.6):
        mono = np.clip(mono, -1.0, 1.0)
        data = (mono * 32767 * volume).astype(np.int16)
        stereo = np.stack([data, data], axis=1)
        self.sounds[name] = pygame.sndarray.make_sound(np.ascontiguousarray(stereo))

    def _build(self):
        rng = np.random.default_rng(9)

        # light punch: short filtered noise thwack
        n = int(SR * 0.13)
        s = _lowpass(_noise(n, rng), 0.35) * _env(n, 0.002, 0.1, 3.0)
        s += _tone(150, n) * _env(n, 0.001, 0.1, 4.0) * 0.6
        self._mk("hit_light", s / np.abs(s).max(), 0.45)

        # heavy punch: deeper thud + crack
        n = int(SR * 0.26)
        s = _lowpass(_noise(n, rng), 0.18) * _env(n, 0.002, 0.2, 2.2)
        s += _tone(88, n) * _env(n, 0.001, 0.2, 2.0) * 0.9
        s += _lowpass(_noise(n, rng), 0.7) * _env(n, 0.001, 0.05, 6.0) * 0.5
        self._mk("hit_heavy", s / np.abs(s).max(), 0.62)

        # block: leather slap
        n = int(SR * 0.12)
        s = _lowpass(_noise(n, rng), 0.55) * _env(n, 0.001, 0.09, 4.0)
        s += _tone(320, n) * _env(n, 0.001, 0.06, 5.0) * 0.35
        self._mk("block", s / np.abs(s).max(), 0.38)

        # whiff: airy swoosh
        n = int(SR * 0.2)
        sweep = np.linspace(0.65, 0.12, n).astype(np.float32)
        raw = _noise(n, rng)
        out = np.empty(n, np.float32)
        acc = 0.0
        for i in range(n):
            acc += sweep[i] * (raw[i] - acc)
            out[i] = acc
        self._mk("whiff", out / np.abs(out).max() * _env(n, 0.05, 0.15, 1.6), 0.22)

        # bell: metallic strike (inharmonic partials)
        n = int(SR * 1.5)
        s = np.zeros(n, np.float32)
        for f, a, d in ((784, 1.0, 1.6), (1180, 0.62, 1.9), (1567, 0.4, 2.4),
                        (2350, 0.24, 3.2), (3100, 0.14, 4.0)):
            s += _tone(f, n) * a * _env(n, 0.001, 1.0, d)
        self._mk("bell", s / np.abs(s).max(), 0.5)

        # knockdown thud
        n = int(SR * 0.5)
        s = _tone(52, n) * _env(n, 0.002, 0.4, 1.8)
        s += _lowpass(_noise(n, rng), 0.08) * _env(n, 0.002, 0.4, 2.0) * 0.8
        self._mk("thud", s / np.abs(s).max(), 0.7)

        # crowd loop: filtered noise with slow swells
        n = int(SR * 4.0)
        base = _lowpass(_noise(n, rng), 0.05)
        base = base / np.abs(base).max()
        t = np.arange(n, dtype=np.float32) / SR
        swell = 0.55 + 0.45 * (0.5 + 0.5 * np.sin(2 * math.pi * 0.17 * t)) \
            * (0.5 + 0.5 * np.sin(2 * math.pi * 0.07 * t + 1.3))
        # loop-safe crossfade
        fade = int(SR * 0.35)
        w = base * swell
        w[:fade] *= np.linspace(0, 1, fade)
        w[-fade:] *= np.linspace(1, 0, fade)
        self._mk("crowd", w, 0.30)

        # crowd roar (on knockdowns / big hits)
        n = int(SR * 1.8)
        r = _lowpass(_noise(n, rng), 0.09)
        r = r / np.abs(r).max() * _env(n, 0.08, 1.0, 1.1)
        self._mk("roar", r, 0.55)

    # ------------------------------------------------------------------
    def play(self, name, volume=1.0):
        if not self.ok or not self.enabled:
            return
        s = self.sounds.get(name)
        if s is None:
            return
        try:
            ch = pygame.mixer.find_channel(True)
            if ch:
                ch.set_volume(max(0.0, min(1.0, volume)))
                ch.play(s)
        except Exception:
            pass

    def start_crowd(self):
        if not self.ok or not self.enabled:
            return
        s = self.sounds.get("crowd")
        if s is None:
            return
        try:
            self.crowd_chan = pygame.mixer.Channel(0)
            self.crowd_chan.set_volume(0.35)
            self.crowd_chan.play(s, loops=-1)
        except Exception:
            self.crowd_chan = None

    def crowd_level(self, v: float):
        if self.crowd_chan is not None:
            try:
                self.crowd_chan.set_volume(max(0.1, min(0.85, v)))
            except Exception:
                pass

    def toggle(self):
        self.enabled = not self.enabled
        if not self.enabled and self.crowd_chan:
            try:
                self.crowd_chan.set_volume(0.0)
            except Exception:
                pass
        elif self.enabled and self.crowd_chan:
            self.crowd_level(0.35)
        return self.enabled
