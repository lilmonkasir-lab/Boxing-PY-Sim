"""Perspective camera with cinematic follow behaviour."""
from __future__ import annotations

import math

import numpy as np

from . import math3d as m3


class Camera:
    def __init__(self, width: int, height: int, fov_deg: float = 58.0,
                 near: float = 0.15, far: float = 220.0):
        self.width = width
        self.height = height
        self.fov = math.radians(fov_deg)
        self.near = near
        self.far = far
        self.eye = m3.vec3(0.0, 3.2, 9.5)
        self.target = m3.vec3(0.0, 1.5, 0.0)
        self.up = m3.vec3(0.0, 1.0, 0.0)
        self.shake = 0.0
        self._shake_off = m3.vec3()
        self._t = 0.0

    # ------------------------------------------------------------------
    def resize(self, width: int, height: int) -> None:
        self.width, self.height = width, height

    def set_fov(self, deg: float) -> None:
        self.fov = math.radians(max(20.0, min(100.0, deg)))

    @property
    def focal(self) -> float:
        return (self.height * 0.5) / math.tan(self.fov * 0.5)

    def view_matrix(self) -> np.ndarray:
        return m3.look_at(self.eye + self._shake_off, self.target + self._shake_off * 0.35, self.up)

    # ------------------------------------------------------------------
    def add_shake(self, amount: float) -> None:
        self.shake = min(1.4, self.shake + amount)

    def update(self, dt: float) -> None:
        self._t += dt
        self.shake = max(0.0, self.shake - dt * 2.2)
        if self.shake > 0.001:
            a = self.shake * 0.16
            t = self._t * 46.0
            self._shake_off = m3.vec3(
                math.sin(t * 1.7) * a,
                math.sin(t * 2.3 + 1.1) * a * 0.8,
                math.sin(t * 1.1 + 2.0) * a * 0.4,
            )
        else:
            self._shake_off = m3.vec3()

    # ------------------------------------------------------------------
    def project(self, pts: np.ndarray, view: np.ndarray | None = None):
        """Project world points -> (screen_xy, view_depth)."""
        if view is None:
            view = self.view_matrix()
        vs = m3.transform_points(view, np.atleast_2d(pts))
        z = -vs[:, 2]
        z = np.maximum(z, 1e-4)
        f = self.focal
        sx = self.width * 0.5 + vs[:, 0] * f / z
        sy = self.height * 0.5 - vs[:, 1] * f / z
        return np.stack([sx, sy], axis=1), z
