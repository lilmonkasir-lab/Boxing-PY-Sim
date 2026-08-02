"""Vectorised software 3D renderer on top of pygame's polygon rasteriser.

Why not OpenGL?  Because "3D out of pygame" should actually run anywhere
pygame runs - no GPU drivers, no PyOpenGL wheels, no shader compilation.  So
this module implements a small but complete fixed-function pipeline:

    model -> world -> view -> near-plane clip -> perspective divide
          -> backface cull -> Lambert + rim + fog shading
          -> depth sort (painter) -> pygame.draw.polygon

All per-triangle maths is done with numpy on whole arrays at once, so the only
python-level loop left is the final draw loop (which is unavoidable, and is
C code inside pygame).
"""
from __future__ import annotations

import math

import numpy as np
import pygame

from . import math3d as m3
from .lighting import LightRig
from .mesh import Mesh


# Draw layers.  A pure depth sort by triangle centroid breaks down when
# objects differ wildly in size (a 7 m floor tile's centroid can be nearer than
# a small canvas tile that is visually on top of it, so the floor paints over
# the ring).  Sorting by layer first and depth second fixes that class of
# artefact outright, which is why the scene is authored in these bands.
LAYER_BACKDROP = 0     # hall floor, crowd, lighting truss
LAYER_RING = 1         # platform, canvas, posts
LAYER_ACTORS = 2       # the fighters
LAYER_FOREGROUND = 3   # ropes, which must overlay the boxers


class RenderItem:
    """A mesh plus the transform it should be drawn with."""

    __slots__ = ("mesh", "matrix", "shade", "sort_bias", "layer", "visible")

    def __init__(self, mesh: Mesh, matrix=None, shade: float = 1.0,
                 sort_bias: float = 0.0, layer: int = LAYER_RING):
        self.mesh = mesh
        self.matrix = m3.identity() if matrix is None else matrix
        self.shade = shade
        self.sort_bias = sort_bias
        self.layer = layer
        self.visible = True


class Renderer:
    def __init__(self, surface: pygame.Surface, camera):
        self.surface = surface
        self.camera = camera
        self.rig = LightRig.arena()
        # legacy single-light knobs, kept so existing code/tests keep working
        self.light_dir = m3.normalize(m3.vec3(-0.45, -1.0, -0.35))
        self.ambient = 0.42
        self.diffuse = 0.72
        self.rim = 0.20
        self.tone_map = True
        self.fog_color = np.array([16.0, 14.0, 26.0], dtype=np.float32)
        self.fog_start = 16.0
        self.fog_end = 90.0
        self.backface_cull = True
        self.tris_drawn = 0
        self._items: list[RenderItem] = []
        # scratch buffers reused across frames
        self._poly_cache: list = []

    # ------------------------------------------------------------------
    def resize(self, surface: pygame.Surface) -> None:
        self.surface = surface

    def begin(self) -> None:
        self._items.clear()
        self.tris_drawn = 0

    def submit(self, mesh: Mesh, matrix=None, shade: float = 1.0,
               sort_bias: float = 0.0, layer: int = LAYER_RING) -> None:
        if mesh is None or len(mesh.faces) == 0:
            return
        self._items.append(RenderItem(mesh, matrix, shade, sort_bias, layer))

    # ------------------------------------------------------------------
    def _gather(self, view: np.ndarray):
        """Transform every submitted mesh into view space.

        Returns concatenated arrays of triangle corners in view space plus
        per-triangle colour / flags.
        """
        tri_a, tri_b, tri_c = [], [], []
        cols, biases, flags, layers = [], [], [], []
        for it in self._items:
            if not it.visible:
                continue
            mesh = it.mesh
            mv = view @ it.matrix
            v = m3.transform_points(mv, mesh.verts)
            f = mesh.faces
            a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
            # cheap reject: entirely behind the eye
            keep = ~((a[:, 2] > -self.camera.near) &
                     (b[:, 2] > -self.camera.near) &
                     (c[:, 2] > -self.camera.near))
            if not keep.any():
                continue
            a, b, c = a[keep], b[keep], c[keep]
            col = mesh.colors[keep] * it.shade
            tri_a.append(a)
            tri_b.append(b)
            tri_c.append(c)
            cols.append(col)
            biases.append(np.full(len(a), it.sort_bias, np.float32))
            layers.append(np.full(len(a), it.layer, np.float32))
            fl = np.zeros((len(a), 4), np.float32)
            fl[:, 0] = 1.0 if mesh.double_sided else 0.0
            fl[:, 1] = 1.0 if mesh.unlit else 0.0
            fl[:, 2] = getattr(mesh, "spec", 0.0)
            fl[:, 3] = getattr(mesh, "shine", 1.0)
            flags.append(fl)
        if not tri_a:
            return None
        return (np.concatenate(tri_a), np.concatenate(tri_b), np.concatenate(tri_c),
                np.clip(np.concatenate(cols), 0, 255), np.concatenate(biases),
                np.concatenate(flags), np.concatenate(layers))

    # ------------------------------------------------------------------
    @staticmethod
    def _clip_near(a, b, c, col, bias, flags, layer, near):
        """Sutherland-Hodgman clip of triangles against z = -near.

        Triangles fully inside pass through untouched.  Straddling triangles
        are re-triangulated (1 or 2 new triangles).
        """
        za, zb, zc = a[:, 2], b[:, 2], c[:, 2]
        ia, ib, ic = za <= -near, zb <= -near, zc <= -near
        n_in = ia.astype(np.int8) + ib.astype(np.int8) + ic.astype(np.int8)

        partial_any = ((n_in == 1) | (n_in == 2)).any()
        if not partial_any:
            # overwhelmingly the common case: nothing crosses the near plane,
            # so skip the python re-triangulation loop altogether
            full = n_in == 3
            return (a[full], b[full], c[full], col[full], bias[full],
                    flags[full], layer[full])

        full = n_in == 3
        out_a, out_b, out_c = [a[full]], [b[full]], [c[full]]
        out_col, out_bias, out_flags = [col[full]], [bias[full]], [flags[full]]
        out_layer = [layer[full]]

        partial = (n_in == 1) | (n_in == 2)
        if partial.any():
            pa, pb, pc = a[partial], b[partial], c[partial]
            pcol, pbias, pfl = col[partial], bias[partial], flags[partial]
            play = layer[partial]
            tris = np.stack([pa, pb, pc], axis=1)          # (N,3,3)
            inside = tris[:, :, 2] <= -near                 # (N,3)
            # python loop only over the handful of straddling triangles
            na, nb, nc, nco, nbi, nf, nly = [], [], [], [], [], [], []
            for i in range(len(tris)):
                poly = []
                for k in range(3):
                    cur, nxt = tris[i, k], tris[i, (k + 1) % 3]
                    ci, ni = inside[i, k], inside[i, (k + 1) % 3]
                    if ci:
                        poly.append(cur)
                    if ci != ni:
                        d = (-near - cur[2]) / (nxt[2] - cur[2])
                        poly.append(cur + (nxt - cur) * d)
                for k in range(1, len(poly) - 1):
                    na.append(poly[0])
                    nb.append(poly[k])
                    nc.append(poly[k + 1])
                    nco.append(pcol[i])
                    nbi.append(pbias[i])
                    nf.append(pfl[i])
                    nly.append(play[i])
            if na:
                out_a.append(np.array(na, np.float32))
                out_b.append(np.array(nb, np.float32))
                out_c.append(np.array(nc, np.float32))
                out_col.append(np.array(nco, np.float32))
                out_bias.append(np.array(nbi, np.float32))
                out_flags.append(np.array(nf, np.float32))
                out_layer.append(np.array(nly, np.float32))
        return (np.concatenate(out_a), np.concatenate(out_b), np.concatenate(out_c),
                np.concatenate(out_col), np.concatenate(out_bias),
                np.concatenate(out_flags), np.concatenate(out_layer))

    # ------------------------------------------------------------------
    def render(self) -> int:
        cam = self.camera
        view = cam.view_matrix()
        got = self._gather(view)
        if got is None:
            return 0
        a, b, c, col, bias, flags, layer = got
        a, b, c, col, bias, flags, layer = self._clip_near(
            a, b, c, col, bias, flags, layer, cam.near)
        if len(a) == 0:
            return 0

        # --- lighting (view space normals) -----------------------------
        e1 = b - a
        e2 = c - a
        n = np.cross(e1, e2)
        nl = np.linalg.norm(n, axis=1, keepdims=True)
        nl[nl < 1e-12] = 1.0
        n = n / nl

        # --- perspective projection ------------------------------------
        f = cam.focal
        cx, cy = cam.width * 0.5, cam.height * 0.5
        za = np.maximum(-a[:, 2], 1e-4)
        zb = np.maximum(-b[:, 2], 1e-4)
        zc = np.maximum(-c[:, 2], 1e-4)
        ax = cx + a[:, 0] * f / za
        ay = cy - a[:, 1] * f / za
        bx = cx + b[:, 0] * f / zb
        by = cy - b[:, 1] * f / zb
        cxp = cx + c[:, 0] * f / zc
        cyp = cy - c[:, 1] * f / zc

        # --- backface cull via signed screen area ----------------------
        area = (bx - ax) * (cyp - ay) - (cxp - ax) * (by - ay)
        double_sided = flags[:, 0] > 0.5
        if self.backface_cull:
            keep = (area < -1e-6) | (double_sided & (np.abs(area) > 1e-6))
        else:
            keep = np.abs(area) > 1e-6

        # --- screen bounds cull ----------------------------------------
        minx = np.minimum(np.minimum(ax, bx), cxp)
        maxx = np.maximum(np.maximum(ax, bx), cxp)
        miny = np.minimum(np.minimum(ay, by), cyp)
        maxy = np.maximum(np.maximum(ay, by), cyp)
        keep &= (maxx >= 0) & (minx < cam.width) & (maxy >= 0) & (miny < cam.height)
        # drop sub-pixel slivers
        keep &= ((maxx - minx) > 0.6) | ((maxy - miny) > 0.6)
        if not keep.any():
            return 0

        idx = np.flatnonzero(keep)
        ax, ay = ax[idx], ay[idx]
        bx, by = bx[idx], by[idx]
        cxp, cyp = cxp[idx], cyp[idx]
        n = n[idx]
        col = col[idx]
        bias = bias[idx]
        layer = layer[idx]
        area = area[idx]
        unlit = flags[idx, 1] > 0.5
        zmid = (za[idx] + zb[idx] + zc[idx]) / 3.0

        # flip normals of back-facing double sided tris toward the viewer
        flip = area > 0
        n[flip] *= -1.0

        # --- shading ----------------------------------------------------
        centroid = (a[idx] + b[idx] + c[idx]) / 3.0
        spec_strength = flags[idx, 2]
        shininess = np.maximum(flags[idx, 3], 1.0)

        self.rig.prepare(view)
        up_view = m3.transform_dir(view, m3.vec3(0.0, 1.0, 0.0))
        up_view = up_view / max(float(np.linalg.norm(up_view)), 1e-9)
        diffuse, specular = self.rig.shade(n, centroid, up_view,
                                           spec_strength, shininess)

        rgb = col * diffuse
        # specular is a highlight *added* on top, not a tint of the base colour
        rgb = rgb + specular * 255.0

        if self.rim > 0.0:
            # fresnel-ish rim: bright edge where a surface turns away from us
            vlen = np.linalg.norm(centroid, axis=1, keepdims=True)
            vlen[vlen < 1e-9] = 1.0
            vdot = np.abs(np.einsum("ij,ij->i", n, -centroid / vlen))
            rim = np.clip(1.0 - vdot, 0.0, 1.0) ** 3
            rgb = rgb + (rim * self.rim * 190.0)[:, None]

        rgb = np.where(unlit[:, None], col, rgb)

        if self.tone_map:
            # Reinhard-style roll-off: keeps the bright overhead key from
            # flat-clipping every shoulder to pure white
            x = np.maximum(rgb, 0.0) / 255.0
            rgb = (x / (1.0 + x * 0.85)) * 255.0 * 1.34

        # --- distance fog -------------------------------------------------
        if self.fog_end > self.fog_start:
            t = np.clip((zmid - self.fog_start) / (self.fog_end - self.fog_start), 0.0, 1.0)
            t = np.where(unlit, 0.0, t)
            rgb = rgb * (1.0 - t)[:, None] + self.fog_color[None, :] * t[:, None]
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)

        # --- painter's algorithm ------------------------------------------
        # Sort by layer first, then far-to-near within the layer.  Depth range
        # is bounded by the far plane, so scaling the layer by a value larger
        # than any depth keeps the bands strictly ordered.
        span = self.camera.far * 4.0
        key = layer * span - (zmid + bias)
        order = np.argsort(key)
        pts = np.stack([np.stack([ax, ay], 1), np.stack([bx, by], 1),
                        np.stack([cxp, cyp], 1)], axis=1)[order]
        rgb = rgb[order]

        # SDL rasterises the *entire* area of a polygon, including the parts
        # hanging off-screen, so a triangle 100x the size of the viewport costs
        # ~1000x a small one.  Near-plane clipping alone leaves plenty of those
        # (a floor quad seen edge-on projects enormous), so anything sticking
        # out past a margin gets clipped to the viewport first.
        w, h = cam.width, cam.height
        big = ((pts[:, :, 0].min(axis=1) < -w) | (pts[:, :, 0].max(axis=1) > 2 * w) |
               (pts[:, :, 1].min(axis=1) < -h) | (pts[:, :, 1].max(axis=1) > 2 * h))

        surf = self.surface
        draw = pygame.draw.polygon
        # tolist() once is far faster than touching numpy per triangle
        pts_l = pts.tolist()
        rgb_l = rgb.tolist()
        big_l = big.tolist()
        clip = self._clip_screen
        rect = (-2.0, -2.0, w + 2.0, h + 2.0)
        drawn = 0
        for i in range(len(pts_l)):
            poly = pts_l[i]
            if big_l[i]:
                poly = clip(poly, rect)
                if len(poly) < 3:
                    continue
            draw(surf, rgb_l[i], poly)
            drawn += 1
        self.tris_drawn = drawn
        return drawn

    # ------------------------------------------------------------------
    @staticmethod
    def _clip_screen(poly, rect):
        """Sutherland-Hodgman clip of a polygon against the viewport rect."""
        x0, y0, x1, y1 = rect
        # (inside test, intersect axis, bound)
        for edge in range(4):
            if not poly:
                return poly
            out = []
            n = len(poly)
            for i in range(n):
                cur = poly[i]
                prv = poly[i - 1]
                if edge == 0:
                    ci, pi_ = cur[0] >= x0, prv[0] >= x0
                elif edge == 1:
                    ci, pi_ = cur[0] <= x1, prv[0] <= x1
                elif edge == 2:
                    ci, pi_ = cur[1] >= y0, prv[1] >= y0
                else:
                    ci, pi_ = cur[1] <= y1, prv[1] <= y1
                if ci != pi_:
                    if edge < 2:
                        b = x0 if edge == 0 else x1
                        dx = cur[0] - prv[0]
                        t = 0.0 if dx == 0 else (b - prv[0]) / dx
                        out.append([b, prv[1] + (cur[1] - prv[1]) * t])
                    else:
                        b = y0 if edge == 2 else y1
                        dy = cur[1] - prv[1]
                        t = 0.0 if dy == 0 else (b - prv[1]) / dy
                        out.append([prv[0] + (cur[0] - prv[0]) * t, b])
                if ci:
                    out.append(cur)
            poly = out
        return poly

    # ------------------------------------------------------------------
    def project_point(self, p):
        """World point -> (x, y, depth) or None if behind the camera."""
        cam = self.camera
        v = m3.transform_point(cam.view_matrix(), p)
        if v[2] > -cam.near:
            return None
        z = -v[2]
        f = cam.focal
        return (cam.width * 0.5 + v[0] * f / z, cam.height * 0.5 - v[1] * f / z, z)
