"""Lighting rig for the software renderer.

A boxing hall is lit from directly above by a truss of hard lamps, which is
what gives fighters their signature look: blown-out shoulders, deep shadow
under the brow and chin, and a bright rim where the back lights catch sweat.
Reproducing that needs more than one lamp, so the renderer runs a small
three-point rig plus a hemispheric ambient term.

Everything is stored as plain arrays and consumed by
:meth:`boxing_sim.engine.renderer.Renderer.render` in a single vectorised
pass, so the cost is independent of how many triangles are on screen.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import math3d as m3


@dataclass
class Light:
    """A directional light.  `direction` points *from* the lamp *toward* the scene."""

    direction: np.ndarray
    color: tuple = (255.0, 255.0, 255.0)
    intensity: float = 1.0
    specular: float = 1.0

    def __post_init__(self):
        self.direction = m3.normalize(np.asarray(self.direction, np.float32))


@dataclass
class LightRig:
    """Three-point rig + hemispheric ambient.

    ambient_sky / ambient_ground give cheap directional ambience: surfaces
    facing up pick up the white glare of the overhead truss, surfaces facing
    down pick up bounce from the canvas.  It costs one dot product and does
    more for perceived depth than any number of extra lamps.
    """

    lights: list = field(default_factory=list)
    ambient_sky: tuple = (52.0, 56.0, 74.0)
    ambient_ground: tuple = (14.0, 13.0, 18.0)
    exposure: float = 1.0

    # cached view-space data, rebuilt once per frame
    _dirs_view: np.ndarray | None = None
    _cols: np.ndarray | None = None
    _spec: np.ndarray | None = None

    @classmethod
    def arena(cls) -> "LightRig":
        """The default hall rig: hard key overhead, cool fill, warm back light."""
        return cls(lights=[
            # key - the overhead truss, slightly to camera-left
            Light((-0.28, -1.0, -0.22), (255, 244, 222), 1.15, 1.0),
            # fill - soft, cool, from the opposite side to open up the shadows
            Light((0.62, -0.35, 0.45), (140, 164, 210), 0.26, 0.25),
            # back / rim - low and behind, separates fighters from the crowd
            Light((0.10, 0.42, 1.00), (255, 206, 164), 0.34, 0.95),
        ])

    # ------------------------------------------------------------------
    def prepare(self, view: np.ndarray) -> None:
        """Transform the rig into view space.  Call once per frame."""
        dirs, cols, spec = [], [], []
        for lt in self.lights:
            d = m3.transform_dir(view, lt.direction)
            n = float(np.linalg.norm(d))
            if n > 1e-9:
                d = d / n
            dirs.append(d)
            cols.append(np.asarray(lt.color, np.float32) / 255.0 * lt.intensity)
            spec.append(lt.specular * lt.intensity)
        self._dirs_view = np.asarray(dirs, np.float32) if dirs else np.zeros((0, 3), np.float32)
        self._cols = np.asarray(cols, np.float32) if cols else np.zeros((0, 3), np.float32)
        self._spec = np.asarray(spec, np.float32) if spec else np.zeros(0, np.float32)

    # ------------------------------------------------------------------
    def shade(self, normals: np.ndarray, centroids: np.ndarray, up_view: np.ndarray,
              spec_strength: np.ndarray, shininess: np.ndarray):
        """Return (diffuse_rgb, specular_rgb) multipliers for every triangle.

        normals / centroids are view space, shape (N,3).  The camera sits at
        the origin looking down -Z, so the view vector is just -normalize(c).
        """
        n_tris = len(normals)
        # hemispheric ambient
        ny = normals @ up_view
        t = (ny * 0.5 + 0.5)[:, None]
        sky = np.asarray(self.ambient_sky, np.float32) / 255.0
        ground = np.asarray(self.ambient_ground, np.float32) / 255.0
        diffuse = ground[None, :] + (sky - ground)[None, :] * t
        specular = np.zeros((n_tris, 3), np.float32)

        if self._dirs_view is None or len(self._dirs_view) == 0:
            return diffuse, specular

        # view vector per face
        vlen = np.linalg.norm(centroids, axis=1, keepdims=True)
        vlen[vlen < 1e-9] = 1.0
        vdir = -centroids / vlen

        any_spec = bool((spec_strength > 1e-4).any())
        for i in range(len(self._dirs_view)):
            ldir = self._dirs_view[i]
            # direction toward the lamp
            to_light = -ldir
            ndl = normals @ to_light
            np.maximum(ndl, 0.0, out=ndl)
            if not ndl.any():
                continue
            diffuse += self._cols[i][None, :] * ndl[:, None]

            if any_spec and self._spec[i] > 1e-4:
                # Blinn-Phong: cheaper than reflect() and looks the same here
                h = to_light[None, :] + vdir
                hl = np.linalg.norm(h, axis=1, keepdims=True)
                hl[hl < 1e-9] = 1.0
                ndh = np.einsum("ij,ij->i", normals, h / hl)
                np.maximum(ndh, 0.0, out=ndh)
                s = np.power(ndh, shininess) * spec_strength * self._spec[i]
                specular += self._cols[i][None, :] * s[:, None]

        return diffuse, specular
