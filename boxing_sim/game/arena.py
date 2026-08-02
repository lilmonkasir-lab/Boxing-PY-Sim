"""The boxing ring + surrounding arena.

Geometry follows the layout of the reference model:
https://sketchfab.com/3d-models/boxing-ring-861f09ce71014e4baebeb79b2f99b1d2
(Kopag 3D, free standard licence) - raised apron platform, padded skirt, four
corner posts with pads, four rope runs with red turnbuckle wraps, plus the
crowd/lighting environment around it.

If you drop the actual downloaded OBJ into ``assets/models/`` the loader in
:mod:`boxing_sim.engine.objloader` will pick it up and it replaces the
procedural platform + ropes (see :func:`build_arena`).
"""
from __future__ import annotations

import math
import os
import random

import numpy as np

from ..engine import math3d as m3
from ..engine.mesh import Mesh
from ..engine.primitives import box, cylinder, quad, sphere, tube_between
from ..engine import objloader
from ..engine import renderer as renderer_layers

# ---------------------------------------------------------------------------
# ring metrics (metres)
# ---------------------------------------------------------------------------
RING_HALF = 4.6          # half width of the fighting surface (canvas)
APRON = 0.75             # canvas overhang beyond the ropes
FLOOR_Y = 1.05           # canvas height above arena floor
POST_H = 2.55            # post height above canvas
ROPE_HEIGHTS = (0.46, 0.94, 1.42, 1.90)

C_CANVAS = (142, 146, 156)
C_CANVAS_ALT = (133, 137, 147)
C_SKIRT = (28, 44, 96)
C_APRON_TRIM = (196, 30, 46)
C_POST = (208, 210, 214)
C_POST_RED = (196, 40, 52)
C_POST_BLUE = (44, 78, 176)
C_ROPE = (232, 232, 236)
C_ROPE_RED = (206, 46, 56)
C_STEEL = (86, 90, 104)


def _post_pad(x, z, color):
    """Corner post with a padded wrap, matching the reference silhouette."""
    parts = []
    base_y = FLOOR_Y
    parts.append(cylinder(0.115, POST_H, 10, C_POST,
                          (x, base_y + POST_H / 2, z), name="post"))
    # padded turnbuckle wrap
    parts.append(cylinder(0.175, 1.62, 10, color,
                          (x, base_y + 0.30 + 0.81, z), name="pad"))
    # cap
    parts.append(sphere(0.135, 5, 10, C_POST, (x, base_y + POST_H, z)))
    # base plate
    parts.append(box(0.36, 0.09, 0.36, C_STEEL, (x, base_y + 0.045, z)))
    return Mesh.combine(parts, "corner").with_material("metal")


def _ropes():
    """Four rope runs, kept as separate meshes (one per side of the ring).

    Splitting them lets the renderer drop whichever run sits between the
    camera and the fighters, which is exactly what a real broadcast does by
    shooting through the ropes.  Returns {side_normal: Mesh}.
    """
    runs = {}
    r = RING_HALF
    corners = [(-r, -r), (r, -r), (r, r), (-r, r)]
    # outward normal of each run, in the same order as `corners`
    normals = [(0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)]
    for i in range(4):
        parts = []
        for h in ROPE_HEIGHTS:
            y = FLOOR_Y + h
            x0, z0 = corners[i]
            x1, z1 = corners[(i + 1) % 4]
            # slight sag in the middle of each run
            sag = 0.055
            mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
            parts.append(tube_between((x0, y, z0), (mx, y - sag, mz), 0.042, 5, C_ROPE))
            parts.append(tube_between((mx, y - sag, mz), (x1, y, z1), 0.042, 5, C_ROPE))
            # red turnbuckle wraps near each post
            for t in (0.10, 0.90):
                px = x0 + (x1 - x0) * t
                pz = z0 + (z1 - z0) * t
                dx = (x1 - x0) * 0.055
                dz = (z1 - z0) * 0.055
                parts.append(tube_between((px - dx, y, pz - dz),
                                          (px + dx, y, pz + dz), 0.050, 5, C_ROPE_RED))
        runs[normals[i]] = Mesh.combine(parts, f"rope_run_{i}").with_material("rope")
    return runs


def _canvas():
    """Raised platform: canvas top, red trim, sponsor skirt, steel frame.

    The sides are built as four separate thin panels rather than one big box.
    That matters: the renderer sorts by triangle centroid depth (painter's
    algorithm), and a single box spanning the whole ring has its centroid in
    the middle of the ring, so its huge side quads would incorrectly sort in
    front of the fighters.  Per-side panels keep each centroid where the
    geometry actually is.
    """
    parts = []
    o = RING_HALF + APRON

    # Canvas top, split into a grid so long thin tris never span the ring.
    # The grid is also used to bake a lighting pool into the vertex colours:
    # the canvas faces straight up into the overhead key and would otherwise
    # render as one flat blown-out slab that swallows the fighters.  Darkening
    # toward the ropes reproduces the falloff of a real overhead rig and gives
    # the eye somewhere to rest.
    n = 8
    step = (o * 2) / n
    for i in range(n):
        for j in range(n):
            x = -o + (i + 0.5) * step
            z = -o + (j + 0.5) * step
            base = C_CANVAS if (i + j) % 2 == 0 else C_CANVAS_ALT
            r = math.hypot(x, z) / o                      # 0 centre -> 1 edge
            fall = 1.0 - 0.50 * min(1.0, r ** 1.4)
            c = tuple(v * fall for v in base)
            parts.append(box(step, 0.10, step, c, (x, FLOOR_Y - 0.05, z), name="canvas"))

    trim_y = FLOOR_Y - 0.16
    skirt_h = FLOOR_Y - 0.22
    for sx, sz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        # red apron trim band (one panel per side)
        if sx:
            parts.append(box(0.10, 0.13, o * 2 + 0.10, C_APRON_TRIM,
                             (sx * (o + 0.03), trim_y, 0), name="trim"))
            parts.append(box(0.06, skirt_h, o * 2 + 0.02, C_SKIRT,
                             (sx * o, skirt_h / 2, 0), name="skirt"))
            parts.append(box(0.20, 0.12, o * 2 + 0.20, C_STEEL,
                             (sx * (o + 0.05), 0.06, 0), name="frame"))
        else:
            parts.append(box(o * 2 + 0.10, 0.13, 0.10, C_APRON_TRIM,
                             (0, trim_y, sz * (o + 0.03)), name="trim"))
            parts.append(box(o * 2 + 0.02, skirt_h, 0.06, C_SKIRT,
                             (0, skirt_h / 2, sz * o), name="skirt"))
            parts.append(box(o * 2 + 0.20, 0.12, 0.20, C_STEEL,
                             (0, 0.06, sz * (o + 0.05)), name="frame"))
    return Mesh.combine(parts, "platform")


def _centre_logo():
    """Faint centre-circle marking on the canvas (drawn as flat unlit tris)."""
    verts = [[0.0, FLOOR_Y + 0.002, 0.0]]
    faces, cols = [], []
    n = 26
    r = 1.85
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        verts.append([math.cos(a) * r, FLOOR_Y + 0.002, math.sin(a) * r])
    for i in range(1, n + 1):
        faces.append([0, i + 1, i])
        cols.append((150, 154, 166))
    m = Mesh(np.array(verts, np.float32), np.array(faces, np.int32),
             np.array(cols, np.float32), "logo")
    return m


def _floor():
    # Subdivided rather than one giant quad: big polygons are disproportionately
    # expensive for the software rasteriser, and per-tile centroids sort far
    # better under the painter's algorithm.
    parts = []
    n, size = 6, 46.0
    step = size / n
    for i in range(n):
        for j in range(n):
            x = -size / 2 + (i + 0.5) * step
            z = -size / 2 + (j + 0.5) * step
            c = (26, 26, 36) if (i + j) % 2 == 0 else (22, 22, 31)
            parts.append(box(step, 0.2, step, c, (x, -0.1, z), name="floor"))
    return Mesh.combine(parts, "floor")


def _crowd(seed=7, tiers=4, density=1.0):
    """Tiered blocks of spectators - cheap, but sells the arena.

    Each spectator is a single box (no separate head mesh): at these distances
    the head is a couple of pixels, and halving the triangle count here is the
    single biggest win for the software rasteriser.
    """
    rng = random.Random(seed)
    parts = []
    for t in range(tiers):
        inner = 9.5 + t * 2.4
        y = 0.55 + t * 0.9
        count = int((14 + t * 2) * density)
        for side in range(4):
            for i in range(count):
                u = (i + 0.5) / count * 2.0 - 1.0
                jitter = rng.uniform(-0.25, 0.25)
                a = u * (inner + 1.2) + jitter
                b = inner + rng.uniform(-0.3, 0.3)
                if side == 0:
                    px, pz = a, b
                elif side == 1:
                    px, pz = b, a
                elif side == 2:
                    px, pz = a, -b
                else:
                    px, pz = -b, a
                shade = rng.uniform(0.55, 1.05)
                base = rng.choice([(58, 60, 86), (44, 46, 70), (70, 58, 78), (40, 52, 74)])
                col = tuple(min(255, c * shade) for c in base)
                h = rng.uniform(1.05, 1.45)
                parts.append(box(0.44, h, 0.34, col, (px, y + h / 2, pz)))

    # tier risers, built as four panels per tier (see _canvas for why)
    for t in range(tiers):
        inner = 9.5 + t * 2.4
        y = t * 0.9
        span = inner * 2 + 3.0
        for sx, sz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if sx:
                parts.append(box(2.6, 0.9, span, (18, 18, 28),
                                 (sx * (inner + 0.5), y + 0.45, 0)))
            else:
                parts.append(box(span, 0.9, 2.6, (18, 18, 28),
                                 (0, y + 0.45, sz * (inner + 0.5))))
    return Mesh.combine(parts, "crowd")


def _lights():
    parts = []
    rig_y = 11.0
    for x in (-6.0, 6.0):
        for z in (-6.0, 6.0):
            parts.append(box(1.5, 0.3, 1.5, (30, 30, 38), (x, rig_y, z)))
            parts.append(box(1.2, 0.14, 1.2, (255, 246, 214), (x, rig_y - 0.2, z)))
    # truss
    for x in (-6.0, 6.0):
        parts.append(box(0.18, 0.18, 13.5, (48, 48, 58), (x, rig_y + 0.25, 0)))
    for z in (-6.0, 6.0):
        parts.append(box(13.5, 0.18, 0.18, (48, 48, 58), (0, rig_y + 0.25, z)))
    m = Mesh.combine(parts, "lights")
    m.unlit = False
    return m


def _light_glow():
    """Unlit quads faking the hot pools of light on the canvas."""
    parts = []
    for x in (-6.0, 6.0):
        for z in (-6.0, 6.0):
            parts.append(quad((x - 1.0, 10.6, z - 1.0), (x + 1.0, 10.6, z - 1.0),
                              (x + 1.0, 10.6, z + 1.0), (x - 1.0, 10.6, z + 1.0),
                              (255, 250, 226), double_sided=True, unlit=True))
    return Mesh.combine(parts, "glow")


# ---------------------------------------------------------------------------
class Arena:
    """Static scene geometry, pre-baked into a handful of big meshes."""

    def __init__(self, use_external_model: bool = True, model_dir: str | None = None,
                 crowd: bool = True):
        self.external_model = None
        self.external_path = None
        if use_external_model and model_dir:
            self._try_external(model_dir)

        self.post_list = []
        if self.external_model is not None:
            self.platform = self.external_model
            self.ropes = {}
            self.posts = None
            self.logo = None
        else:
            self.platform = Mesh.combine([_canvas()], "platform")
            self.logo = _centre_logo()
            r = RING_HALF
            # kept per-corner so the one nearest the camera can be dropped
            self.post_list = [
                ((-r, -r), _post_pad(-r, -r, C_POST_RED)),
                ((r, -r), _post_pad(r, -r, C_POST_BLUE)),
                ((r, r), _post_pad(r, r, C_POST_RED)),
                ((-r, r), _post_pad(-r, r, C_POST_BLUE)),
            ]
            self.posts = Mesh.combine([m for _c, m in self.post_list], "posts")
            self.ropes = _ropes()

        self.floor = _floor()
        self.crowd = _crowd() if crowd else None
        self.lights = _lights()
        self.glow = _light_glow()
        self._ident = m3.identity()
        self._hidden_posts = set()

    # ------------------------------------------------------------------
    def _try_external(self, model_dir: str):
        path = objloader.find_model(model_dir, "ring")
        if not path:
            return
        try:
            mesh = objloader.load_obj(path, max_tris=5000)
            mesh = mesh.center_on_origin(keep_floor=True)
            mesh = mesh.fit_to_size((RING_HALF + APRON) * 2.0)
            self.external_model = mesh
            self.external_path = path
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[arena] could not load {path}: {exc}")

    # ------------------------------------------------------------------
    @property
    def canvas_y(self) -> float:
        return FLOOR_Y

    def clamp_to_ring(self, pos, radius: float = 0.34):
        """Keep a fighter inside the ropes; returns (pos, hit_ropes)."""
        lim = RING_HALF - radius
        x = m3.clamp(float(pos[0]), -lim, lim)
        z = m3.clamp(float(pos[2]), -lim, lim)
        hit = (abs(x - float(pos[0])) > 1e-6) or (abs(z - float(pos[2])) > 1e-6)
        return m3.vec3(x, float(pos[1]), z), hit

    def corner_pos(self, red: bool):
        r = RING_HALF - 1.0
        return m3.vec3(-r, FLOOR_Y, -r) if red else m3.vec3(r, FLOOR_Y, r)

    # ------------------------------------------------------------------
    def update_occlusion(self, camera, focus):
        """Work out which corner post sits between the camera and the action.

        Call once per frame *before* :meth:`submit`.  A post that lands on the
        sight line covers the boxers completely, so it is simply not drawn -
        the same trick a camera operator performs by leaning around it.
        """
        self._hidden_posts = set()
        if camera is None or not self.post_list or focus is None:
            return
        eye = np.asarray(camera.eye, np.float32)
        seg = np.asarray(focus, np.float32) - eye
        seg_len = float(np.linalg.norm(seg))
        if seg_len < 1e-4:
            return
        dirn = seg / seg_len
        for (cx, cz), _m in self.post_list:
            post = np.array([cx, FLOOR_Y + POST_H * 0.5, cz], np.float32)
            t = float((post - eye) @ dirn)
            if 0.2 < t < seg_len:      # genuinely in front of the fighters
                if float(np.linalg.norm(eye + dirn * t - post)) < 0.85:
                    self._hidden_posts.add((cx, cz))

    # ------------------------------------------------------------------
    def submit(self, renderer, draw_crowd=True):
        bg = renderer_layers.LAYER_BACKDROP
        ring = renderer_layers.LAYER_RING
        renderer.submit(self.floor, self._ident, layer=bg)
        if draw_crowd and self.crowd is not None:
            renderer.submit(self.crowd, self._ident, layer=bg)
        renderer.submit(self.lights, self._ident, layer=bg)
        renderer.submit(self.glow, self._ident, layer=bg)
        renderer.submit(self.platform, self._ident, layer=ring)
        if self.logo is not None:
            renderer.submit(self.logo, self._ident, sort_bias=-0.02, layer=ring)
        if self.post_list:
            for corner, mesh in self.post_list:
                if corner in self._hidden_posts:
                    continue
                renderer.submit(mesh, self._ident, layer=ring)
        elif self.posts is not None:
            renderer.submit(self.posts, self._ident, layer=ring)

    def submit_ropes(self, renderer, camera=None, focus=None):
        """Ropes draw last so they overlay the fighters, as they do on TV.

        The run between the camera and the action is skipped; otherwise a
        ringside camera spends most of the fight looking at a giant white bar.
        """
        if not self.ropes:
            return
        skip = set()
        if camera is not None:
            focus = m3.vec3(0.0, FLOOR_Y, 0.0) if focus is None else focus
            view_dir = np.asarray(focus, np.float32) - np.asarray(camera.eye, np.float32)
            view_dir = m3.normalize(m3.vec3(float(view_dir[0]), 0.0, float(view_dir[2])))
            # A run is in the way when its outward normal opposes our view.
            # Cull *every* such run, not just the worst one: from a corner or
            # diagonal angle two runs face the camera at once, and culling only
            # one still leaves a white bar across the fighters.
            for n in self.ropes:
                if -(view_dir[0] * n[0] + view_dir[2] * n[1]) > 0.34:
                    skip.add(n)
        for n, mesh in self.ropes.items():
            if n in skip:
                continue
            renderer.submit(mesh, self._ident,
                            layer=renderer_layers.LAYER_FOREGROUND)


def build_arena(model_dir: str | None = None, crowd: bool = True) -> Arena:
    if model_dir is None:
        here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_dir = os.path.join(here, "assets", "models")
    return Arena(use_external_model=True, model_dir=model_dir, crowd=crowd)
