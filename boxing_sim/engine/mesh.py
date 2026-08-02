"""Triangle mesh container used by the software renderer.

Every mesh is stored as:
    verts   (N,3) float32   - model space vertices
    faces   (M,3) int32     - triangle indices (CCW when seen from outside)
    colors  (M,3) float32   - per-face RGB in 0..255

Per-face colours keep the renderer completely vectorised: no UV lookups, no
texture sampling, just flat/Lambert shading which suits the chunky low-poly
look of the reference boxing-ring model.
"""
from __future__ import annotations

import numpy as np


#: Surface finishes.  (specular strength, shininess exponent)
#: These drive the Blinn-Phong term in the renderer, and are what makes
#: gloves read as glossy leather next to matte canvas and soft skin.
MATERIALS = {
    "matte":   (0.00, 1.0),     # canvas, crowd, concrete
    "skin":    (0.16, 12.0),    # soft sheen, broadens as fighters sweat
    "leather": (0.55, 34.0),    # gloves, turnbuckle pads
    "satin":   (0.34, 20.0),    # trunks
    "metal":   (0.72, 58.0),    # posts, truss, ring frame
    "rope":    (0.20, 14.0),
}


class Mesh:
    __slots__ = ("verts", "faces", "colors", "name", "double_sided", "unlit",
                 "spec", "shine")

    def __init__(self, verts, faces, colors=None, name: str = "mesh",
                 double_sided: bool = False, unlit: bool = False,
                 material: str = "matte"):
        self.verts = np.asarray(verts, dtype=np.float32).reshape(-1, 3)
        self.faces = np.asarray(faces, dtype=np.int32).reshape(-1, 3)
        if colors is None:
            colors = np.full((len(self.faces), 3), 200.0, dtype=np.float32)
        colors = np.asarray(colors, dtype=np.float32)
        if colors.ndim == 1:
            colors = np.tile(colors, (len(self.faces), 1))
        self.colors = colors.astype(np.float32).reshape(-1, 3)
        self.name = name
        self.double_sided = double_sided
        self.unlit = unlit
        spec, shine = MATERIALS.get(material, MATERIALS["matte"])
        self.spec = float(spec)
        self.shine = float(shine)

    # ------------------------------------------------------------------
    @property
    def tri_count(self) -> int:
        return len(self.faces)

    def copy(self) -> "Mesh":
        return self._like(self.verts.copy(), self.faces.copy(), self.colors.copy())

    def _like(self, verts, faces, colors) -> "Mesh":
        """A new mesh carrying this one's name, flags and surface finish."""
        m = Mesh(verts, faces, colors, self.name, self.double_sided, self.unlit)
        m.spec, m.shine = self.spec, self.shine
        return m

    def with_material(self, material: str) -> "Mesh":
        m = self.copy()
        spec, shine = MATERIALS.get(material, MATERIALS["matte"])
        m.spec, m.shine = float(spec), float(shine)
        return m

    def transform(self, mat: np.ndarray) -> "Mesh":
        """Return a copy baked through a 4x4 matrix."""
        v = (self.verts @ mat[:3, :3].T) + mat[:3, 3]
        det = float(np.linalg.det(mat[:3, :3]))
        faces = self.faces
        if det < 0:  # mirrored -> flip winding so normals stay outward
            faces = faces[:, ::-1].copy()
        return self._like(v, faces, self.colors.copy())

    def translated(self, x, y, z) -> "Mesh":
        v = self.verts + np.array([x, y, z], dtype=np.float32)
        return self._like(v, self.faces.copy(), self.colors.copy())

    def tinted(self, factor: float) -> "Mesh":
        m = self.copy()
        m.colors = np.clip(m.colors * factor, 0, 255)
        return m

    def recolor(self, rgb) -> "Mesh":
        m = self.copy()
        m.colors[:] = np.asarray(rgb, dtype=np.float32)
        return m

    # ------------------------------------------------------------------
    def bounds(self):
        if len(self.verts) == 0:
            z = np.zeros(3, dtype=np.float32)
            return z, z
        return self.verts.min(axis=0), self.verts.max(axis=0)

    def center_on_origin(self, keep_floor: bool = True) -> "Mesh":
        lo, hi = self.bounds()
        c = (lo + hi) * 0.5
        dy = lo[1] if keep_floor else c[1]
        return self.translated(-c[0], -dy, -c[2])

    def fit_to_size(self, target_x: float) -> "Mesh":
        lo, hi = self.bounds()
        span = float(max(hi[0] - lo[0], hi[2] - lo[2]))
        if span < 1e-6:
            return self.copy()
        s = target_x / span
        v = self.verts * s
        return self._like(v, self.faces.copy(), self.colors.copy())

    # ------------------------------------------------------------------
    @staticmethod
    def combine(meshes, name: str = "combined") -> "Mesh":
        meshes = [m for m in meshes if m is not None and len(m.faces)]
        if not meshes:
            return Mesh(np.zeros((0, 3), np.float32), np.zeros((0, 3), np.int32),
                        np.zeros((0, 3), np.float32), name)
        verts, faces, colors = [], [], []
        off = 0
        for m in meshes:
            verts.append(m.verts)
            faces.append(m.faces + off)
            colors.append(m.colors)
            off += len(m.verts)
        out = Mesh(np.concatenate(verts), np.concatenate(faces),
                   np.concatenate(colors), name,
                   double_sided=meshes[0].double_sided,
                   unlit=meshes[0].unlit)
        out.spec, out.shine = meshes[0].spec, meshes[0].shine
        return out

    # ------------------------------------------------------------------
    def decimate(self, max_tris: int, grid: int = 96) -> "Mesh":
        """Vertex-clustering decimation.

        Downloaded Sketchfab models happily ship 160k triangles which no pure
        python rasteriser will ever enjoy.  We snap vertices to a uniform grid,
        weld them, and drop degenerate triangles.  The grid is refined /
        coarsened until the triangle budget is met.
        """
        if len(self.faces) <= max_tris:
            return self.copy()
        lo, hi = self.bounds()
        size = np.maximum(hi - lo, 1e-6)
        best = None
        g = grid
        for _ in range(12):
            cell = size / g
            keys = np.floor((self.verts - lo) / cell).astype(np.int64)
            keys = np.minimum(keys, g - 1)
            flat = (keys[:, 0] * (g + 1) + keys[:, 1]) * (g + 1) + keys[:, 2]
            uniq, inv = np.unique(flat, return_inverse=True)
            # cluster representative = mean of the members
            nv = len(uniq)
            acc = np.zeros((nv, 3), dtype=np.float64)
            cnt = np.zeros(nv, dtype=np.int64)
            np.add.at(acc, inv, self.verts)
            np.add.at(cnt, inv, 1)
            newverts = (acc / cnt[:, None]).astype(np.float32)
            nf = inv[self.faces]
            keep = (nf[:, 0] != nf[:, 1]) & (nf[:, 1] != nf[:, 2]) & (nf[:, 0] != nf[:, 2])
            nf = nf[keep]
            ncol = self.colors[keep]
            best = self._like(newverts, nf, ncol)
            if len(nf) <= max_tris:
                break
            g = max(4, int(g * 0.72))
        return best if best is not None else self.copy()
