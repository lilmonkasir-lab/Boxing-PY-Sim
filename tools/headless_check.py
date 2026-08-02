#!/usr/bin/env python3
"""Headless smoke test / screenshot tool.

Runs the sim with the dummy SDL video driver, drives synthetic input, and can
dump PNG frames so the renderer can be inspected without a display.

    python tools/headless_check.py --seconds 20 --shots 6 --out /tmp/shots
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from boxing_sim.app import Game  # noqa: E402
from boxing_sim.game.fighter import PUNCH_ORDER  # noqa: E402


class ScriptedGame(Game):
    """Game subclass whose player input comes from a scripted bot."""

    def __init__(self, *a, **kw):
        self.script_rng = random.Random(kw.pop("script_seed", 3))
        super().__init__(*a, **kw)
        self._queue = []
        self._gap = 0.0

    def handle_events(self):
        pygame.event.pump()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False

    def gather_input(self):
        rng = self.script_rng
        m = self.match
        p, o = m.player, m.opponent
        d = o.pos - p.pos
        d[1] = 0.0
        dist = float((d @ d) ** 0.5)

        fwd = 1.0 if dist > 1.15 else (-1.0 if dist < 0.80 else 0.0)
        strafe = math.sin(self.time * 0.7) * 0.8
        block = dist < 1.5 and rng.random() < 0.12
        duck = rng.random() < 0.03

        # use the skill mechanics too, otherwise the scripted side is being
        # measured against an opponent playing a strictly richer game
        threat = 0.0
        if o.punch.active:
            phase, _u = o.punch_phase()
            threat = 1.0 if phase == "wind" else (0.7 if phase == "strike" else 0.0)
        parry = bool(threat > 0.5 and dist < 1.6 and p.parry.ready
                     and rng.random() < 0.30)
        # punish recovery frames
        counter_now = False
        if o.punch.active:
            phase, u = o.punch_phase()
            counter_now = phase == "recover" and u < 0.5 and dist < 1.3
        punches = []
        self._gap -= 1 / 60.0
        if counter_now and not self._queue and rng.random() < 0.55:
            self._queue = ["cross"]
        if not self._queue and dist < 1.35 and rng.random() < 0.10:
            n = rng.randint(1, 3)
            self._queue = [rng.choice(PUNCH_ORDER) for _ in range(n)]
        if self._queue and self._gap <= 0 and not p.punch.active:
            punches = [self._queue.pop(0)]
            self._gap = 0.09
        return dict(move=(strafe, fwd), block=block, duck=duck, punches=punches,
                    mash=rng.random() < 0.35, parry=parry,
                    stance_toggle=False, stance_nudge=0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--shots", type=int, default=0)
    ap.add_argument("--out", default="/tmp/boxshots")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--quality", default="high")
    ap.add_argument("--difficulty", default="Contender")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--round-length", type=float, default=60.0)
    ap.add_argument("--camera", type=int, default=None)
    ap.add_argument("--bench", action="store_true")
    args = ap.parse_args()

    g = ScriptedGame(width=args.width, height=args.height, rounds=args.rounds,
                     difficulty=args.difficulty, round_length=args.round_length,
                     no_audio=True, quality=args.quality, seed=11)
    if args.camera is not None:
        g.cam_mode = args.camera

    os.makedirs(args.out, exist_ok=True)
    dt = 1.0 / 60.0
    steps = int(args.seconds / dt)
    shot_every = max(1, steps // args.shots) if args.shots else 0

    import time
    t0 = time.perf_counter()
    frames = 0
    shot_i = 0
    for i in range(steps):
        g.handle_events()
        g.update(dt)
        g.draw()
        frames += 1
        if shot_every and i % shot_every == 0 and shot_i < args.shots:
            path = os.path.join(args.out, f"shot_{shot_i:02d}.png")
            pygame.image.save(g.screen, path)
            print(f"saved {path}  state={g.match.state} round={g.match.round_no}")
            shot_i += 1
        if not g.running:
            break
    el = time.perf_counter() - t0

    m = g.match
    print("-" * 58)
    print(f"simulated {frames} frames in {el:.2f}s  -> {frames/el:.1f} fps "
          f"({el/frames*1000:.2f} ms/frame)")
    print(f"tris last frame: {g.renderer.tris_drawn}")
    print(f"state={m.state} round={m.round_no}/{m.total_rounds} "
          f"time_left={m.round_time:.1f}")
    print(f"player  hp={m.player.health:5.1f} st={m.player.stamina:5.1f} "
          f"landed={m.player.stats_landed}/{m.player.stats_thrown} kd={m.player.knockdowns}")
    print(f"opponent hp={m.opponent.health:5.1f} st={m.opponent.stamina:5.1f} "
          f"landed={m.opponent.stats_landed}/{m.opponent.stats_thrown} kd={m.opponent.knockdowns}")
    if m.state == "over":
        print(f"RESULT: {m.result_title} - {m.result_sub}  "
              f"cards {m.score_player}-{m.score_opponent}")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
