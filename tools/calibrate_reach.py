#!/usr/bin/env python3
"""Measure the true connect range of every punch and print a PUNCHES table.

`PunchDef.reach` is consumed by the AI to decide when to throw, and by the
tests, so it must be the distance at which the animated rig *actually* lands a
punch - not a hand-written guess.  This binary-searches that distance against
the real hit detection and prints values to paste into fighter.py.

    python tools/calibrate_reach.py
"""
from __future__ import annotations

import math
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from boxing_sim.engine import math3d as m3          # noqa: E402
from boxing_sim.game.combat import (BODY_RADIUS, HEAD_RADIUS,  # noqa: E402
                                    resolve_punch)
from boxing_sim.game.fighter import (PUNCHES, PUNCH_ORDER, Fighter,  # noqa: E402
                                     FighterStats)


class _FlatArena:
    def clamp_to_ring(self, pos, radius=0.34):
        return pos, False


def connects_at(key: str, sep: float) -> bool:
    """Does `key` land on a stationary opponent `sep` metres directly ahead?"""
    f = Fighter(FighterStats(), m3.vec3(0, 1.05, 0), 0.0, True)
    o = Fighter(FighterStats(), m3.vec3(0, 1.05, sep), math.pi, False)
    arena = _FlatArena()
    rng = random.Random(0)
    if not f.try_punch(key):
        return False
    for _ in range(600):
        f.update(1 / 240.0, o, arena, (0, 0), False, False)
        o.update(1 / 240.0, f, arena, (0, 0), False, False)
        res = resolve_punch(f, o, rng)
        if res is not None and (res.landed or res.blocked):
            return True
        if not f.punch.active:
            return False
    return False


def max_connect_distance(key: str, lo=0.45, hi=2.6, iters=22) -> float:
    if not connects_at(key, lo):
        return 0.0
    for _ in range(iters):
        mid = (lo + hi) / 2
        if connects_at(key, mid):
            lo = mid
        else:
            hi = mid
    return lo


def main():
    print(f"{'punch':12s} {'connects up to':>15s} {'implied reach':>14s} "
          f"{'declared':>9s}")
    print("-" * 56)
    reaches = {}
    for key in PUNCH_ORDER:
        p = PUNCHES[key]
        hit_r = BODY_RADIUS if p.target == "body" else HEAD_RADIUS
        d = max_connect_distance(key)
        # invert punch_range(): reach = connect_distance - hit_radius - margin
        reach = max(0.0, d - hit_r - 0.10)
        reaches[key] = reach
        print(f"{key:12s} {d:13.3f} m {reach:12.3f} m {p.reach:8.3f}")
    print("\nPaste into boxing_sim/game/fighter.py:\n")
    for key in PUNCH_ORDER:
        print(f"    {key:12s} reach={reaches[key]:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
