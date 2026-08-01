"""Procedural mesh primitives (box, cylinder, sphere, capsule, tube...).

Everything the sim draws is built from these, so the game runs with zero
external asset files.  A downloaded OBJ can still be dropped in on top - see
`boxing_sim.engine.objloader`.
"""
from __future__ import annotations

import math

import numpy as np

from .mesh import Mesh

# ---------------------------------------------------------------------------
# box
# ---------------------------------------------------------------------------
_BOX_V = np.array([
    [-0.5, -0.5, -0.5], [0.5, -0.5, -0.5], [0.5, 0.5, -0.5], [-0.5, 0.5, -0.5],
    [-0.5, -0.5, 0.5], [0.5, -0.5, 0.5], [0.5, 0.5, 0.5], [-0.5, 0.5, 0.5],
], dtype=np.float32)

# CCW when viewed from outside
_BOX_F = np.array([
    [4, 5, 6], [4, 6, 7],      # +Z
    [1, 0, 3], [1, 3, 2],      # -Z
    [5, 1, 2], [5, 2, 6],      # +X
    [0, 4, 7], [0, 7, 3],      # -X
    [3, 7, 6], [3, 6, 2],      # +Y
    [0, 1, 5], [0, 5, 4],      # -Y
], dtype=np.int32)


def box(sx=1.0, sy=1.0, sz=1.0, color=(200, 200, 200), center=(0, 0, 0),
        face_shades=None, name="box") -> Mesh:
    """Axis aligned box centred on `center`."""
    v = _BOX_V * np.array([sx, sy, sz], dtype=np.float32) + np.asarray(center, np.float32)
    col = np.tile(np.asarray(color, np.float32), (12, 1))
    if face_shades:
        for i, f in enumerate(face_shades):
            col[i * 2:i * 2 + 2] *= f
    return Mesh(v, _BOX_F.copy(), np.clip(col, 0, 255), name)


def slab(x0, x1, y0, y1, z0, z1, color=(200, 200, 200), name="slab") -> Mesh:
    return box(x1 - x0, y1 - y0, z1 - z0, color,
               ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), name=name)


# ---------------------------------------------------------------------------
# cylinder / cone / capsule
# ---------------------------------------------------------------------------
def cylinder(radius=0.5, height=1.0, segments=12, color=(200, 200, 200),
             center=(0, 0, 0), axis="y", cap=True, radius_top=None,
             name="cyl") -> Mesh:
    """Cylinder centred on `center`, extending +-height/2 along `axis`."""
    if radius_top is None:
        radius_top = radius
    ang = np.linspace(0.0, 2.0 * math.pi, segments, endpoint=False, dtype=np.float32)
    cs, sn = np.cos(ang), np.sin(ang)
    h = height * 0.5
    bottom = np.stack([cs * radius, np.full(segments, -h, np.float32), sn * radius], 1)
    top = np.stack([cs * radius_top, np.full(segments, h, np.float32), sn * radius_top], 1)
    verts = [bottom, top]
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        b0, b1 = i, j
        t0, t1 = segments + i, segments + j
        faces.append([b0, b1, t1])
        faces.append([b0, t1, t0])
    n = 2 * segments
    if cap:
        verts.append(np.array([[0, -h, 0], [0, h, 0]], np.float32))
        cb, ct = n, n + 1
        for i in range(segments):
            j = (i + 1) % segments
            faces.append([cb, j, i])
            faces.append([ct, segments + i, segments + j])
    v = np.concatenate(verts)
    if axis == "x":
        v = v[:, [1, 0, 2]] * np.array([1, 1, 1], np.float32)
        v[:, 1] *= -1
    elif axis == "z":
        v = v[:, [0, 2, 1]]
        v[:, 2] *= -1
    v = v + np.asarray(center, np.float32)
    return Mesh(v, np.array(faces, np.int32), np.asarray(color, np.float32), name)


def tube_between(p0, p1, radius=0.05, segments=8, color=(200, 200, 200),
                 name="tube") -> Mesh:
    """A cylinder stretched between two arbitrary world points."""
    p0 = np.asarray(p0, np.float32)
    p1 = np.asarray(p1, np.float32)
    d = p1 - p0
    ln = float(np.linalg.norm(d))
    if ln < 1e-6:
        return Mesh(np.zeros((0, 3), np.float32), np.zeros((0, 3), np.int32))
    f = d / ln
    up = np.array([0, 1, 0], np.float32)
    if abs(float(np.dot(f, up))) > 0.98:
        up = np.array([1, 0, 0], np.float32)
    r = np.cross(up, f)
    r /= np.linalg.norm(r)
    u = np.cross(f, r)
    ang = np.linspace(0, 2 * math.pi, segments, endpoint=False, dtype=np.float32)
    ring = (np.cos(ang)[:, None] * r + np.sin(ang)[:, None] * u) * radius
    v = np.concatenate([ring + p0, ring + p1])
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append([i, j, segments + j])
        faces.append([i, segments + j, segments + i])
    return Mesh(v, np.array(faces, np.int32), np.asarray(color, np.float32), name)


def sphere(radius=0.5, rings=8, segments=12, color=(200, 200, 200),
           center=(0, 0, 0), squash=(1.0, 1.0, 1.0), name="sphere") -> Mesh:
    verts = [[0.0, radius, 0.0]]
    for i in range(1, rings):
        phi = math.pi * i / rings
        y = math.cos(phi) * radius
        r = math.sin(phi) * radius
        for j in range(segments):
            th = 2 * math.pi * j / segments
            verts.append([math.cos(th) * r, y, math.sin(th) * r])
    verts.append([0.0, -radius, 0.0])
    v = np.array(verts, np.float32)
    faces = []
    for j in range(segments):
        faces.append([0, 1 + j, 1 + (j + 1) % segments])
    for i in range(rings - 2):
        a = 1 + i * segments
        b = 1 + (i + 1) * segments
        for j in range(segments):
            j2 = (j + 1) % segments
            faces.append([a + j, b + j, b + j2])
            faces.append([a + j, b + j2, a + j2])
    last = len(v) - 1
    a = 1 + (rings - 2) * segments
    for j in range(segments):
        faces.append([last, a + (j + 1) % segments, a + j])
    v = v * np.asarray(squash, np.float32) + np.asarray(center, np.float32)
    return Mesh(v, np.array(faces, np.int32), np.asarray(color, np.float32), name)


def capsule(radius=0.2, height=1.0, rings=4, segments=10, color=(200, 200, 200),
            center=(0, 0, 0), name="capsule") -> Mesh:
    """Y-aligned capsule: cylinder of `height` plus hemispherical caps."""
    h = height * 0.5
    body = cylinder(radius, height, segments, color, (0, 0, 0), cap=False)
    top = sphere(radius, rings * 2, segments, color, (0, h, 0))
    bot = sphere(radius, rings * 2, segments, color, (0, -h, 0))
    # trim the hemispheres so we do not pay for hidden geometry
    top = _cut(top, axis=1, keep_above=h - 1e-4)
    bot = _cut(bot, axis=1, keep_below=-h + 1e-4)
    m = Mesh.combine([body, top, bot], name)
    return m.translated(*np.asarray(center, np.float32))


def _cut(mesh: Mesh, axis=1, keep_above=None, keep_below=None) -> Mesh:
    c = mesh.verts[mesh.faces][:, :, axis].mean(axis=1)
    if keep_above is not None:
        keep = c >= keep_above
    else:
        keep = c <= keep_below
    return Mesh(mesh.verts.copy(), mesh.faces[keep], mesh.colors[keep],
                mesh.name, mesh.double_sided, mesh.unlit)


def quad(p0, p1, p2, p3, color=(200, 200, 200), double_sided=False, unlit=False,
         name="quad") -> Mesh:
    v = np.array([p0, p1, p2, p3], np.float32)
    f = np.array([[0, 1, 2], [0, 2, 3]], np.int32)
    return Mesh(v, f, np.asarray(color, np.float32), name,
                double_sided=double_sided, unlit=unlit)


def grid_plane(size=10.0, divisions=1, y=0.0, color=(120, 120, 120),
               checker=None, name="plane") -> Mesh:
    """Flat plane on XZ.  `checker` = (colorA, colorB) for a chequerboard."""
    step = size / divisions
    half = size * 0.5
    verts, faces, colors = [], [], []
    idx = 0
    for i in range(divisions):
        for j in range(divisions):
            x0 = -half + i * step
            z0 = -half + j * step
            verts += [[x0, y, z0], [x0 + step, y, z0],
                      [x0 + step, y, z0 + step], [x0, y, z0 + step]]
            faces += [[idx, idx + 2, idx + 1], [idx, idx + 3, idx + 2]]
            c = color if checker is None else (checker[(i + j) % 2])
            colors += [c, c]
            idx += 4
    return Mesh(np.array(verts, np.float32), np.array(faces, np.int32),
                np.array(colors, np.float32), name)
