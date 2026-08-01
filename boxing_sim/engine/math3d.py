"""Small right-handed 3D math library built on numpy.

Conventions
-----------
* Right handed world space:  +X right, +Y up, +Z toward the default camera.
* Camera space looks down -Z (OpenGL style).
* Matrices are 4x4, row-major, and multiply column vectors:  v' = M @ v.
"""
from __future__ import annotations

import math

import numpy as np

Vec3 = np.ndarray


def vec3(x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Vec3:
    return np.array([x, y, z], dtype=np.float32)


def normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n < 1e-9:
        return np.zeros_like(v)
    return v / n


def length(v: np.ndarray) -> float:
    return float(np.linalg.norm(v))


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ease_out(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - t) ** 3


def identity() -> np.ndarray:
    return np.eye(4, dtype=np.float32)


def translate(x: float, y: float = 0.0, z: float = 0.0) -> np.ndarray:
    m = np.eye(4, dtype=np.float32)
    m[0, 3] = x
    m[1, 3] = y
    m[2, 3] = z
    return m


def translate_v(v) -> np.ndarray:
    return translate(float(v[0]), float(v[1]), float(v[2]))


def scale(sx: float, sy: float = None, sz: float = None) -> np.ndarray:
    if sy is None:
        sy = sx
    if sz is None:
        sz = sx
    m = np.eye(4, dtype=np.float32)
    m[0, 0] = sx
    m[1, 1] = sy
    m[2, 2] = sz
    return m


def rot_x(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    m = np.eye(4, dtype=np.float32)
    m[1, 1] = c
    m[1, 2] = -s
    m[2, 1] = s
    m[2, 2] = c
    return m


def rot_y(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    m = np.eye(4, dtype=np.float32)
    m[0, 0] = c
    m[0, 2] = s
    m[2, 0] = -s
    m[2, 2] = c
    return m


def rot_z(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    m = np.eye(4, dtype=np.float32)
    m[0, 0] = c
    m[0, 1] = -s
    m[1, 0] = s
    m[1, 1] = c
    return m


def compose(*mats: np.ndarray) -> np.ndarray:
    """compose(A, B, C) == A @ B @ C (applied right to left)."""
    out = np.eye(4, dtype=np.float32)
    for m in mats:
        out = out @ m
    return out.astype(np.float32)


def basis_from_forward(forward: np.ndarray, up=(0.0, 1.0, 0.0)) -> np.ndarray:
    """Rotation matrix whose -Z axis... actually whose +Z axis points along `forward`."""
    f = normalize(np.asarray(forward, dtype=np.float32))
    if length(f) < 1e-6:
        f = vec3(0, 0, 1)
    u = np.asarray(up, dtype=np.float32)
    r = normalize(np.cross(u, f))
    if length(r) < 1e-6:
        r = vec3(1, 0, 0)
    u2 = np.cross(f, r)
    m = np.eye(4, dtype=np.float32)
    m[:3, 0] = r
    m[:3, 1] = u2
    m[:3, 2] = f
    return m


def look_at(eye, target, up=(0.0, 1.0, 0.0)) -> np.ndarray:
    eye = np.asarray(eye, dtype=np.float32)
    target = np.asarray(target, dtype=np.float32)
    up = np.asarray(up, dtype=np.float32)
    f = normalize(target - eye)
    if length(f) < 1e-6:
        f = vec3(0, 0, -1)
    s = normalize(np.cross(f, up))
    if length(s) < 1e-6:
        s = vec3(1, 0, 0)
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, :3] = s
    m[1, :3] = u
    m[2, :3] = -f
    m[:3, 3] = -(m[:3, :3] @ eye)
    return m


def transform_points(mat: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Apply a 4x4 matrix to an (N,3) array of points."""
    pts = np.asarray(pts, dtype=np.float32)
    return (pts @ mat[:3, :3].T) + mat[:3, 3]


def transform_point(mat: np.ndarray, p) -> np.ndarray:
    p = np.asarray(p, dtype=np.float32)
    return (mat[:3, :3] @ p) + mat[:3, 3]


def transform_dir(mat: np.ndarray, v) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    return mat[:3, :3] @ v


def angle_wrap(a: float) -> float:
    """Wrap an angle into [-pi, pi]."""
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a


def approach(current: float, target: float, max_delta: float) -> float:
    d = target - current
    if abs(d) <= max_delta:
        return target
    return current + math.copysign(max_delta, d)


def approach_angle(current: float, target: float, max_delta: float) -> float:
    d = angle_wrap(target - current)
    if abs(d) <= max_delta:
        return angle_wrap(target)
    return angle_wrap(current + math.copysign(max_delta, d))


def damp(current, target, rate: float, dt: float):
    """Frame-rate independent exponential smoothing."""
    t = 1.0 - math.exp(-rate * dt)
    return current + (target - current) * t
