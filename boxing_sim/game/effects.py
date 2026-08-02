"""3D particle effects: sweat, impact sparks, and floating damage numbers."""
from __future__ import annotations

import math
import random

import numpy as np

from ..engine import math3d as m3


class Particles:
    """Billboarded point particles drawn straight to the screen surface."""

    MAX = 420

    def __init__(self):
        n = self.MAX
        self.pos = np.zeros((n, 3), np.float32)
        self.vel = np.zeros((n, 3), np.float32)
        self.life = np.zeros(n, np.float32)
        self.max_life = np.ones(n, np.float32)
        self.size = np.zeros(n, np.float32)
        self.col = np.zeros((n, 3), np.float32)
        self.grav = np.zeros(n, np.float32)
        self._next = 0
        self.rng = random.Random(1234)

    def _alloc(self) -> int:
        i = self._next
        self._next = (self._next + 1) % self.MAX
        return i

    def spawn(self, pos, count=8, speed=3.0, color=(255, 230, 200), size=5.0,
              life=0.42, gravity=7.0, spread=1.0):
        rng = self.rng
        for _ in range(count):
            i = self._alloc()
            self.pos[i] = pos
            d = np.array([rng.uniform(-1, 1), rng.uniform(-0.3, 1.0), rng.uniform(-1, 1)],
                         np.float32)
            n = np.linalg.norm(d)
            if n > 1e-6:
                d /= n
            self.vel[i] = d * speed * rng.uniform(0.45, 1.0) * spread
            lf = life * rng.uniform(0.7, 1.3)
            self.life[i] = lf
            self.max_life[i] = lf
            self.size[i] = size * rng.uniform(0.7, 1.35)
            self.col[i] = color
            self.grav[i] = gravity

    def burst_impact(self, pos, big=False):
        if big:
            self.spawn(pos, 14, 5.2, (255, 246, 220), 5.5, 0.34, 9.0)
            self.spawn(pos, 8, 3.0, (255, 186, 130), 7.0, 0.26, 4.0)
        else:
            self.spawn(pos, 7, 3.4, (255, 242, 224), 4.0, 0.24, 8.0)

    def burst_sweat(self, pos, direction):
        d = np.asarray(direction, np.float32)
        for _ in range(6):
            i = self._alloc()
            self.pos[i] = pos
            jitter = np.array([self.rng.uniform(-.6, .6), self.rng.uniform(-.2, .8),
                               self.rng.uniform(-.6, .6)], np.float32)
            self.vel[i] = d * self.rng.uniform(1.5, 4.0) + jitter
            self.life[i] = self.max_life[i] = self.rng.uniform(0.35, 0.7)
            self.size[i] = self.rng.uniform(1.8, 3.2)
            self.col[i] = (215, 235, 255)
            self.grav[i] = 9.8

    def burst_block(self, pos):
        self.spawn(pos, 7, 2.6, (200, 215, 255), 4.5, 0.24, 6.0)

    def update(self, dt: float):
        alive = self.life > 0.0
        if not alive.any():
            return
        self.life[alive] -= dt
        self.vel[alive, 1] -= self.grav[alive] * dt
        self.pos[alive] += self.vel[alive] * dt
        # floor bounce on the canvas
        hit = alive & (self.pos[:, 1] < 1.06) & (self.vel[:, 1] < 0)
        self.vel[hit, 1] *= -0.28
        self.vel[hit, 0] *= 0.6
        self.vel[hit, 2] *= 0.6
        self.pos[hit, 1] = 1.06

    def draw(self, renderer, surface):
        import pygame
        alive = np.flatnonzero(self.life > 0.0)
        if len(alive) == 0:
            return
        cam = renderer.camera
        view = cam.view_matrix()
        pts = self.pos[alive]
        vs = m3.transform_points(view, pts)
        z = -vs[:, 2]
        ok = z > cam.near
        if not ok.any():
            return
        idx = alive[ok]
        vs = vs[ok]
        z = z[ok]
        f = cam.focal
        sx = cam.width * 0.5 + vs[:, 0] * f / z
        sy = cam.height * 0.5 - vs[:, 1] * f / z
        t = np.clip(self.life[idx] / np.maximum(self.max_life[idx], 1e-6), 0.0, 1.0)
        rad = np.maximum(1.0, self.size[idx] * f / (z * 260.0) * (0.45 + 0.55 * t))
        cols = np.clip(self.col[idx] * (0.62 + 0.38 * t)[:, None], 0, 255).astype(int)
        order = np.argsort(-z)
        for k in order:
            pygame.draw.circle(surface, cols[k], (int(sx[k]), int(sy[k])), int(rad[k]))


class FloatingText:
    """Damage numbers / callouts that float up in world space."""

    def __init__(self):
        self.items: list[dict] = []

    def add(self, pos, text, color=(255, 240, 200), life=0.9, size=1.0,
            rise=1.4):
        self.items.append(dict(pos=np.asarray(pos, np.float32).copy(), text=text,
                               color=color, life=life, max_life=life, size=size,
                               rise=rise,
                               drift=np.array([random.uniform(-.4, .4), 0.0,
                                               random.uniform(-.4, .4)], np.float32)))

    def update(self, dt):
        for it in self.items:
            it["life"] -= dt
            it["pos"][1] += it["rise"] * dt
            it["pos"] += it["drift"] * dt
        self.items = [i for i in self.items if i["life"] > 0.0]

    def draw(self, renderer, surface, font):
        for it in self.items:
            pr = renderer.project_point(it["pos"])
            if pr is None:
                continue
            x, y, z = pr
            t = it["life"] / it["max_life"]
            scale = m3.clamp(it["size"] * 46.0 / max(z, 0.5), 0.35, 2.2)
            surf = font.render(it["text"], True, it["color"])
            w = max(1, int(surf.get_width() * scale))
            h = max(1, int(surf.get_height() * scale))
            import pygame
            surf = pygame.transform.smoothscale(surf, (w, h))
            surf.set_alpha(int(255 * min(1.0, t * 1.8)))
            surface.blit(surf, (int(x - w / 2), int(y - h / 2)))
