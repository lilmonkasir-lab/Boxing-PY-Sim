"""Regression tests for the boxing sim.

These lock down the bugs that were actually hit while building it:
  * punches must physically reach (the rig once maxed out at 0.54 m)
  * the AI's punch ranges must agree with the hit detection
  * the renderer must clip huge polygons instead of handing them to SDL
  * rounds must be judged independently of each other

Run with:  python -m pytest tests -q
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from boxing_sim.engine import math3d as m3           # noqa: E402
from boxing_sim.engine.camera import Camera          # noqa: E402
from boxing_sim.engine.mesh import Mesh              # noqa: E402
from boxing_sim.engine.primitives import box, capsule, cylinder, sphere  # noqa: E402
from boxing_sim.engine.renderer import Renderer      # noqa: E402
from boxing_sim.game.ai import punch_range           # noqa: E402
from boxing_sim.game.arena import build_arena        # noqa: E402
from boxing_sim.game.combat import (BODY_RADIUS, HEAD_RADIUS,  # noqa: E402
                                    resolve_punch)
from boxing_sim.game.fighter import (PUNCHES, PUNCH_ORDER, Fighter,  # noqa: E402
                                     FighterStats)


# ---------------------------------------------------------------------------
# math
# ---------------------------------------------------------------------------
def test_look_at_is_orthonormal():
    v = m3.look_at((3, 4, 5), (0, 1, 0))
    r = v[:3, :3]
    assert np.allclose(r @ r.T, np.eye(3), atol=1e-5)


def test_angle_wrap_and_approach():
    assert math.isclose(m3.angle_wrap(3 * math.pi), math.pi, abs_tol=1e-6)
    # crossing the +-pi seam should take the short way round (~0.28 rad),
    # not unwind the long way through zero
    out = m3.approach_angle(3.0, -3.0, 0.5)
    assert abs(m3.angle_wrap(out - 3.0)) <= 0.5 + 1e-6
    assert abs(m3.angle_wrap(out - (-3.0))) < 1e-6, "should have reached the target"

    # a large gap should move by exactly max_delta along the short arc
    out = m3.approach_angle(0.0, 3.0, 0.25)
    assert out == pytest.approx(0.25, abs=1e-6)


def test_transform_point_matches_matrix_product():
    mat = m3.compose(m3.translate(1, 2, 3), m3.rot_y(0.7), m3.scale(2))
    p = np.array([0.3, -0.4, 0.9], np.float32)
    got = m3.transform_point(mat, p)
    want = (mat @ np.array([*p, 1.0], np.float32))[:3]
    assert np.allclose(got, want, atol=1e-5)


# ---------------------------------------------------------------------------
# meshes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("mesh", [
    box(1, 2, 3), cylinder(0.4, 1.0, 10), sphere(0.5, 6, 10), capsule(0.2, 0.6),
])
def test_primitive_meshes_are_well_formed(mesh):
    assert mesh.tri_count > 0
    assert mesh.faces.max() < len(mesh.verts)
    assert mesh.faces.min() >= 0
    assert len(mesh.colors) == mesh.tri_count
    assert np.isfinite(mesh.verts).all()


def test_box_normals_point_outward():
    m = box(2, 2, 2)
    v = m.verts[m.faces]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    centroid = v.mean(axis=1)
    # for a box centred on the origin, outward normals agree with the centroid
    assert (np.einsum("ij,ij->i", n, centroid) > 0).all()


def test_combine_preserves_triangle_count():
    a, b = box(1, 1, 1), sphere(0.5, 5, 8)
    c = Mesh.combine([a, b])
    assert c.tri_count == a.tri_count + b.tri_count
    assert c.faces.max() < len(c.verts)


def test_decimate_respects_budget():
    m = sphere(1.0, 40, 60)
    assert m.tri_count > 2000
    d = m.decimate(400)
    assert d.tri_count <= 400
    assert d.tri_count > 0
    assert d.faces.max() < len(d.verts)


def test_mirrored_transform_flips_winding():
    m = box(1, 1, 1)
    mirrored = m.transform(m3.scale(-1, 1, 1))
    v = mirrored.verts[mirrored.faces]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    assert (np.einsum("ij,ij->i", n, v.mean(axis=1)) > 0).all()


# ---------------------------------------------------------------------------
# renderer
# ---------------------------------------------------------------------------
def _renderer(w=320, h=200):
    import pygame
    pygame.init()
    surf = pygame.Surface((w, h))
    cam = Camera(w, h)
    return Renderer(surf, cam), surf


def test_screen_clip_bounds_a_huge_polygon():
    r, _ = _renderer()
    poly = [[-90000.0, -90000.0], [90000.0, -40000.0], [0.0, 120000.0]]
    out = r._clip_screen(poly, (-2.0, -2.0, 322.0, 202.0))
    assert len(out) >= 3
    xs = [p[0] for p in out]
    ys = [p[1] for p in out]
    assert min(xs) >= -2.1 and max(xs) <= 322.1
    assert min(ys) >= -2.1 and max(ys) <= 202.1


def test_clip_screen_keeps_contained_polygon_untouched():
    r, _ = _renderer()
    poly = [[10.0, 10.0], [50.0, 12.0], [30.0, 60.0]]
    out = r._clip_screen(poly, (-2.0, -2.0, 322.0, 202.0))
    assert len(out) == 3


def test_geometry_behind_camera_is_dropped():
    r, _ = _renderer()
    r.begin()
    # entirely behind the eye (camera looks down -Z from +Z)
    r.submit(box(1, 1, 1, center=(0, 0, 60)))
    assert r.render() == 0


def test_renderer_draws_visible_geometry():
    r, surf = _renderer()
    r.begin()
    r.submit(box(2, 2, 2, color=(255, 0, 0), center=(0, 1.5, 0)))
    assert r.render() > 0
    arr = np.array(surf.get_view("3"), copy=True)
    assert arr.sum() > 0, "nothing was rasterised"


def test_layers_sort_before_depth():
    """A far foreground triangle must still paint over a near backdrop one."""
    import pygame
    from boxing_sim.engine.renderer import LAYER_BACKDROP, LAYER_FOREGROUND
    r, surf = _renderer()
    r.camera.eye = m3.vec3(0, 0, 6)
    r.camera.target = m3.vec3(0, 0, 0)
    r.begin()
    # near, backdrop layer, red
    r.submit(box(4, 4, 0.2, color=(255, 0, 0), center=(0, 0, 2)),
             layer=LAYER_BACKDROP)
    # far, foreground layer, green
    r.submit(box(4, 4, 0.2, color=(0, 255, 0), center=(0, 0, -2)),
             layer=LAYER_FOREGROUND)
    r.render()
    px = surf.get_at((160, 100))
    assert px.g > px.r, "foreground layer did not win over a nearer backdrop"


# ---------------------------------------------------------------------------
# fighter rig / reach
# ---------------------------------------------------------------------------
class _FlatArena:
    """Arena stub with no walls, for isolating rig behaviour."""

    def clamp_to_ring(self, pos, radius=0.34):
        return pos, False


@pytest.mark.parametrize("key", PUNCH_ORDER)
def test_declared_reach_matches_the_animated_rig(key):
    """PUNCHES[key].reach is what the AI trusts, so it must match reality.

    Regenerate with tools/calibrate_reach.py whenever the rig changes.
    """
    from tools.calibrate_reach import max_connect_distance
    hit_r = BODY_RADIUS if PUNCHES[key].target == "body" else HEAD_RADIUS
    measured = max_connect_distance(key) - hit_r - 0.10
    declared = PUNCHES[key].reach
    assert measured == pytest.approx(declared, abs=0.06), (
        f"{key}: rig reaches {measured:.2f} m but declares {declared:.2f} m "
        f"- rerun tools/calibrate_reach.py")


@pytest.mark.parametrize("key", PUNCH_ORDER)
def test_every_punch_can_actually_land(key):
    """Regression: the original rig could never reach the opponent at all."""
    p = PUNCHES[key]
    reach = punch_range(key)
    f = Fighter(FighterStats(), m3.vec3(0, 1.05, 0), 0.0, True)
    o = Fighter(FighterStats(), m3.vec3(0, 1.05, reach - 0.05), math.pi, False)
    arena = _FlatArena()
    import random
    rng = random.Random(0)
    f.try_punch(key)
    landed = False
    for _ in range(400):
        f.update(1 / 240.0, o, arena, (0, 0), False, False)
        o.update(1 / 240.0, f, arena, (0, 0), False, False)
        res = resolve_punch(f, o, rng)
        if res is not None and (res.landed or res.blocked):
            landed = True
            break
        if not f.punch.active:
            break
    assert landed, f"{key} could not connect at its own stated range"


def test_guard_keeps_gloves_near_the_head():
    f = Fighter(FighterStats(), m3.vec3(0, 1.05, 0), 0.0, True)
    f.update(1 / 60.0, f, _FlatArena(), (0, 0), True, False)
    head_h = float(f.head_pos()[1])
    for hand in ("lead", "rear"):
        gy = float(f.glove_world(hand)[1])
        assert abs(gy - head_h) < 0.5, f"{hand} glove is not guarding the head"


def test_body_shots_stay_below_head_shots():
    f = Fighter(FighterStats(), m3.vec3(0, 1.05, 0), 0.0, True)
    o = Fighter(FighterStats(), m3.vec3(0, 1.05, 6.0), math.pi, False)
    heights = {}
    for key in ("jab", "body_jab"):
        g = Fighter(FighterStats(), m3.vec3(0, 1.05, 0), 0.0, True)
        g.try_punch(key)
        peak_z, h = -9.0, 0.0
        while g.punch.active:
            g.update(1 / 240.0, o, _FlatArena(), (0, 0), False, False)
            gw = g.glove_world(PUNCHES[key].hand)
            if gw[2] - g.pos[2] > peak_z:
                peak_z, h = float(gw[2] - g.pos[2]), float(gw[1])
        heights[key] = h
    assert heights["body_jab"] < heights["jab"] - 0.1


def test_fighters_cannot_leave_the_ring():
    arena = build_arena(crowd=False)
    f = Fighter(FighterStats(), arena.corner_pos(True), 0.0, True)
    o = Fighter(FighterStats(), arena.corner_pos(False), math.pi, False)
    for _ in range(600):
        f.update(1 / 60.0, o, arena, (1.0, 1.0), False, False)
    from boxing_sim.game.arena import RING_HALF
    assert abs(float(f.pos[0])) <= RING_HALF + 1e-3
    assert abs(float(f.pos[2])) <= RING_HALF + 1e-3


def test_fighters_do_not_occupy_the_same_space():
    arena = build_arena(crowd=False)
    f = Fighter(FighterStats(), m3.vec3(0, 1.05, 0), 0.0, True)
    o = Fighter(FighterStats(), m3.vec3(0, 1.05, 0.05), math.pi, False)
    for _ in range(240):
        f.update(1 / 60.0, o, arena, (0.0, 1.0), False, False)
        o.update(1 / 60.0, f, arena, (0.0, 1.0), False, False)
    d = np.linalg.norm((f.pos - o.pos)[[0, 2]])
    assert d > 0.4, f"fighters interpenetrated (separation {d:.2f} m)"


# ---------------------------------------------------------------------------
# combat rules
# ---------------------------------------------------------------------------
def test_blocking_reduces_damage_taken():
    import random

    def run(block: bool) -> float:
        f = Fighter(FighterStats(power=3.0), m3.vec3(0, 1.05, 0), 0.0, True)
        o = Fighter(FighterStats(), m3.vec3(0, 1.05, 1.0), math.pi, False)
        rng = random.Random(1)
        arena = _FlatArena()
        for _ in range(14):
            f.try_punch("cross")
            while f.punch.active:
                f.update(1 / 240.0, o, arena, (0, 0), False, False)
                o.update(1 / 240.0, f, arena, (0, 0), block, False)
                resolve_punch(f, o, rng)
        return 100.0 - o.health

    assert run(block=True) < run(block=False) * 0.8


def test_knockdown_when_health_is_exhausted():
    f = Fighter(FighterStats(), m3.vec3(0, 1.05, 0), 0.0, True)
    f.take_hit(500.0, 1.0, m3.vec3(0, 0, 1), blocked=False, to_body=False)
    assert f.health == 0.0
    assert f.down and f.knockdowns == 1


def test_body_shots_drain_stamina_more_than_health():
    body = Fighter(FighterStats(), m3.vec3(0, 1.05, 0), 0.0, True)
    head = Fighter(FighterStats(), m3.vec3(0, 1.05, 0), 0.0, True)
    body.take_hit(20.0, 0.2, m3.vec3(0, 0, 1), False, to_body=True)
    head.take_hit(20.0, 0.2, m3.vec3(0, 0, 1), False, to_body=False)
    assert body.stamina < head.stamina
    assert body.health > head.health


def test_punch_costs_stamina_and_is_refused_when_spent():
    f = Fighter(FighterStats(), m3.vec3(0, 1.05, 0), 0.0, True)
    before = f.stamina
    assert f.try_punch("uppercut")
    assert f.stamina < before
    f.stamina = 0.1
    f.punch.key = ""          # clear the in-flight punch
    assert not f.try_punch("uppercut")


def test_ai_ranges_agree_with_hit_detection():
    """punch_range() must not promise more than resolve_punch() delivers."""
    for key in PUNCH_ORDER:
        p = PUNCHES[key]
        hit_r = BODY_RADIUS if p.target == "body" else HEAD_RADIUS
        assert punch_range(key) <= p.reach + hit_r + 0.15


# ---------------------------------------------------------------------------
# match flow
# ---------------------------------------------------------------------------
def _match(**kw):
    from boxing_sim.game.match import Match
    arena = build_arena(crowd=False)
    return Match(arena, FighterStats(name="P"), FighterStats(name="O"),
                 rounds=kw.pop("rounds", 2), difficulty="Contender",
                 round_length=kw.pop("round_length", 3.0), seed=5)


def _idle():
    return dict(move=(0.0, 0.0), block=False, duck=False, punches=(), mash=False)


def test_match_reaches_a_decision_and_scores_every_round():
    m = _match(rounds=2, round_length=2.0)
    for _ in range(4000):
        m.update(1 / 60.0, _idle())
        m.drain_events()
        if m.state == "over":
            break
    assert m.state == "over"
    assert m.result_title
    # two rounds on the 10-point-must system
    assert m.score_player + m.score_opponent >= 36


def test_rounds_are_judged_independently():
    """Regression: judging once used cumulative damage, so round 1's winner
    automatically won every later round."""
    m = _match(rounds=3, round_length=2.0)
    m.player.damage_dealt = 500.0      # blow out round 1
    m._snapshot_round()                # ... then start a fresh round
    m.opponent.damage_dealt = 40.0
    m.round_no = 2
    m._end_round()
    assert m.score_opponent > m.score_player, "stale cumulative damage leaked in"


def test_knockdown_costs_a_point_on_the_cards():
    m = _match(rounds=3, round_length=2.0)
    m._snapshot_round()
    m.player.damage_dealt += 50.0      # player clearly wins the round
    m.player.knockdowns += 1           # but was dropped once
    m._end_round()
    assert m.score_player == 9
    assert m.score_opponent == 9


def test_three_knockdowns_ends_the_fight():
    m = _match(rounds=6, round_length=60.0)
    m.state = "fight"
    for _ in range(3):
        m.player.knockdowns = 3
        m.player.down = True
        m.down_fighter = m.player
        m.state = "knockdown"
        m.count = 11.0
        m.update(1 / 60.0, _idle())
        m.drain_events()
    assert m.state == "over"
    assert "WINS" in m.result_title


def test_events_are_drained_not_duplicated():
    m = _match()
    m.emit("bell")
    assert len(m.drain_events()) == 1
    assert m.drain_events() == []


# ---------------------------------------------------------------------------
# arena
# ---------------------------------------------------------------------------
def test_arena_builds_and_has_geometry():
    a = build_arena(crowd=False)
    assert a.platform.tri_count > 0
    assert a.posts.tri_count > 0
    assert isinstance(a.ropes, dict) and len(a.ropes) == 4


def test_rope_run_facing_the_camera_is_culled():
    a = build_arena(crowd=False)
    r, _ = _renderer()
    r.begin()
    r.camera.eye = m3.vec3(0.0, 2.0, 14.0)     # looking from +Z
    r.camera.target = m3.vec3(0.0, 1.4, 0.0)
    a.submit_ropes(r, r.camera, m3.vec3(0, 1.05, 0))
    assert len(r._items) == 3, "the near rope run should have been skipped"


def test_all_four_rope_runs_draw_without_a_camera():
    a = build_arena(crowd=False)
    r, _ = _renderer()
    r.begin()
    a.submit_ropes(r)
    assert len(r._items) == 4


# ---------------------------------------------------------------------------
# OBJ loading (the Sketchfab drop-in path)
# ---------------------------------------------------------------------------
def _write_fake_export(root: str) -> str:
    """An OBJ shaped like a real Sketchfab export: materials, quads, negatives."""
    os.makedirs(os.path.join(root, "ring"), exist_ok=True)
    m = sphere(1.0, 30, 40)
    with open(os.path.join(root, "ring", "ring.mtl"), "w") as fh:
        fh.write("newmtl canvas\nKd 0.8 0.1 0.1\nnewmtl rope\nKd 0.1 0.2 0.9\n")
    path = os.path.join(root, "ring", "boxing_ring.obj")
    with open(path, "w") as fh:
        fh.write("# exported\nmtllib ring.mtl\n")
        for v in m.verts:
            fh.write(f"v {v[0]} {v[1]} {v[2]}\n")
        half = len(m.faces) // 2
        fh.write("usemtl canvas\n")
        for f in m.faces[:half]:                     # v/vt/vn form
            fh.write(f"f {f[0]+1}/1/1 {f[1]+1}/1/1 {f[2]+1}/1/1\n")
        fh.write("usemtl rope\n")
        for f in m.faces[half:]:                     # bare v form
            fh.write(f"f {f[0]+1} {f[1]+1} {f[2]+1}\n")
        fh.write("f -1 -2 -3 -4\n")                  # quad, negative indices
    return path


def test_obj_loader_handles_a_sketchfab_style_export(tmp_path):
    from boxing_sim.engine.objloader import find_model, load_obj
    written = _write_fake_export(str(tmp_path))
    found = find_model(str(tmp_path), "ring")
    assert found is not None and os.path.basename(found) == os.path.basename(written)

    mesh = load_obj(found)
    assert mesh.tri_count > 0
    assert mesh.faces.max() < len(mesh.verts)
    # both materials should have been resolved to distinct colours
    assert len(np.unique(mesh.colors, axis=0)) == 2


def test_obj_loader_enforces_the_triangle_budget(tmp_path):
    from boxing_sim.engine.objloader import load_obj
    path = _write_fake_export(str(tmp_path))
    full = load_obj(path)
    small = load_obj(path, max_tris=400)
    assert full.tri_count > 400
    assert 0 < small.tri_count <= 400


def test_external_model_is_fitted_to_the_ring(tmp_path):
    """A downloaded ring must land on the canvas at the right size."""
    from boxing_sim.game.arena import APRON, RING_HALF, Arena
    _write_fake_export(str(tmp_path))
    a = Arena(use_external_model=True, model_dir=str(tmp_path), crowd=False)
    assert a.external_path is not None
    lo, hi = a.platform.bounds()
    assert float(lo[1]) == pytest.approx(0.0, abs=1e-3), "model should sit on the floor"
    assert float(hi[0] - lo[0]) == pytest.approx((RING_HALF + APRON) * 2, rel=0.02)


def test_missing_model_dir_falls_back_to_the_procedural_ring():
    from boxing_sim.game.arena import Arena
    a = Arena(use_external_model=True, model_dir="/nonexistent/path", crowd=False)
    assert a.external_path is None
    assert a.platform.tri_count > 0
    assert len(a.ropes) == 4
