"""Opponent AI - a small utility/state machine boxer brain."""
from __future__ import annotations

import math
import random

from ..engine import math3d as m3
from .combat import BODY_RADIUS, HEAD_RADIUS, distance_between
from .fighter import PUNCHES, Fighter


def punch_range(key: str, reach_stat: float = 1.0) -> float:
    """Max centre-to-centre distance at which `key` can connect.

    glove travel + the target's hit radius, i.e. exactly the condition
    :func:`boxing_sim.game.combat.resolve_punch` tests.
    """
    p = PUNCHES[key]
    hit_r = BODY_RADIUS if p.target == "body" else HEAD_RADIUS
    return p.reach * reach_stat + hit_r + 0.10

COMBOS = [
    ["jab"],
    ["jab", "cross"],
    ["jab", "jab", "cross"],
    ["jab", "cross", "lead_hook"],
    ["body_jab", "cross"],
    ["cross", "lead_hook"],
    ["jab", "body_hook"],
    ["lead_hook", "cross"],
    ["jab", "cross", "uppercut"],
    ["body_hook", "uppercut", "cross"],
]

DIFFICULTIES = {
    # parry / counter are the "skill" dials: higher tiers read your rhythm and
    # punish recovery frames instead of just trading.
    "Amateur":   dict(react=0.36, aggro=0.42, block=0.32, slip=0.10, combo=0.35,
                      err=0.32, parry=0.02, counter=0.10, adapt=0.10),
    "Contender": dict(react=0.24, aggro=0.58, block=0.50, slip=0.22, combo=0.55,
                      err=0.20, parry=0.10, counter=0.30, adapt=0.35),
    "Champion":  dict(react=0.15, aggro=0.72, block=0.66, slip=0.34, combo=0.75,
                      err=0.10, parry=0.22, counter=0.55, adapt=0.65),
    "Legend":    dict(react=0.09, aggro=0.85, block=0.80, slip=0.48, combo=0.92,
                      err=0.04, parry=0.36, counter=0.80, adapt=0.90),
}


class BoxerAI:
    def __init__(self, fighter: Fighter, difficulty: str = "Contender", seed=None):
        self.f = fighter
        self.difficulty = difficulty
        self.p = DIFFICULTIES.get(difficulty, DIFFICULTIES["Contender"])
        self.rng = random.Random(seed)
        self.state = "circle"
        self.state_t = 0.0
        self.think_t = 0.0
        self.queue: list[str] = []
        self.queue_gap = 0.0
        self.circle_dir = self.rng.choice((-1.0, 1.0))
        self.want_block = False
        self.want_duck = False
        self.want_parry = False
        self.move = (0.0, 0.0)
        self.pressure = 0.5
        # reads the player's habits: which punches they favour, how often they
        # guard.  Feeds `adapt`, so higher tiers start countering your pattern.
        self.seen_punches: dict[str, int] = {}
        self.seen_guard = 0.0
        self.seen_frames = 0.0

    # ------------------------------------------------------------------
    def _set_state(self, s: str):
        if self.state != s:
            self.state = s
            self.state_t = 0.0

    def observe(self, opp: Fighter, dt: float) -> None:
        """Build a picture of the player's habits (used by `adapt`)."""
        self.seen_frames += dt
        if opp.block:
            self.seen_guard += dt
        if opp.punch.active and opp.punch.t < 1e-3:
            self.seen_punches[opp.punch.key] = self.seen_punches.get(opp.punch.key, 0) + 1

    @property
    def guard_rate(self) -> float:
        """Fraction of observed time the opponent spent behind a high guard.

        Needs a little evidence before it means anything, so it reads 0 for
        the first second rather than swinging wildly off two frames.
        """
        if self.seen_frames < 1.0:
            return 0.0
        return self.seen_guard / self.seen_frames

    def update(self, dt: float, opp: Fighter, arena):
        f = self.f
        self.observe(opp, dt)
        self.state_t += dt
        self.think_t -= dt
        self.queue_gap -= dt
        p = self.p

        if f.out or f.down:
            self.move = (0.0, 0.0)
            self.want_block = False
            self.want_duck = False
            return

        dist = distance_between(f, opp)
        hp_ratio = f.health / 100.0
        stam = f.stamina / f.stats.stamina_max
        opp_hurt = opp.health < 38.0

        # ---------------- reactive defence -----------------------------
        threat = 0.0
        if opp.punch.active:
            phase, u = opp.punch_phase()
            if phase == "wind":
                threat = 1.0
            elif phase == "strike" and u < 0.5:
                threat = 0.8
        incoming_body = opp.punch.active and PUNCHES[opp.punch.key].target == "body"

        self.want_block = False
        self.want_duck = False
        self.want_parry = False
        if threat > 0.4 and dist < 2.4:
            r = self.rng.random()
            # a parry is the highest-skill answer, so it is gated hardest
            if r < p["parry"] and f.parry.ready and not incoming_body:
                self.want_parry = True
            elif r < p["parry"] + p["slip"] and not incoming_body and f.dodge_cool <= 0.0:
                self.want_duck = True
                f.dodge_cool = 0.55
            elif r < p["parry"] + p["slip"] + p["block"]:
                self.want_block = True

        # low stamina / hurt -> turtle up more
        if (stam < 0.22 or hp_ratio < 0.25) and dist < 2.2:
            if self.rng.random() < 0.55:
                self.want_block = True

        # ---------------- state selection --------------------------------
        if self.think_t <= 0.0:
            self.think_t = p["react"] * self.rng.uniform(0.7, 1.5)
            aggro = p["aggro"]
            aggro *= 0.55 + 0.9 * stam
            if opp_hurt:
                aggro *= 1.5
            if hp_ratio < 0.3:
                aggro *= 0.7
            roll = self.rng.random()
            if stam < 0.18:
                self._set_state("recover")
            elif roll < aggro * 0.62:
                self._set_state("attack")
            elif roll < aggro * 0.62 + 0.24:
                self._set_state("circle")
            else:
                self._set_state("retreat" if self.rng.random() < 0.4 else "circle")
            if self.rng.random() < 0.25:
                self.circle_dir *= -1.0

        # ---------------- movement ---------------------------------------
        # ideal separations are derived from real punch reach (see PUNCH_RANGE)
        ideal = 1.05 if self.state == "attack" else (1.9 if self.state == "circle" else 2.8)
        if self.state == "recover":
            ideal = 3.2
        err = 1.0 + self.rng.uniform(-p["err"], p["err"]) * 0.5
        ideal *= err

        fwd = 0.0
        if dist > ideal + 0.15:
            fwd = 1.0
        elif dist < ideal - 0.15:
            fwd = -1.0
        strafe = self.circle_dir * (0.75 if self.state in ("circle", "retreat") else 0.30)
        if self.want_block:
            fwd *= 0.4
        self.move = (strafe, fwd)

        # ---------------- punching -----------------------------------------
        if self.queue and self.queue_gap <= 0.0 and not f.punch.active and not self.want_block:
            key = self.queue[0]
            reach = punch_range(key, f.stats.reach)
            if dist <= reach:
                if f.try_punch(key):
                    self.queue.pop(0)
                    self.queue_gap = self.rng.uniform(0.03, 0.14)
                else:
                    self.queue.clear()
            elif dist > reach + 0.9:
                self.queue.clear()

        if (not self.queue and self.state == "attack" and not f.punch.active
                and dist < 1.7 and stam > 0.15):
            if self.rng.random() < 0.5 + p["combo"] * 0.5:
                combo = self._pick_combo(dist, opp)
                self.queue = list(combo)
                self.queue_gap = self.rng.uniform(0.0, 0.12)

        # counter-punch window: punish the opponent's recovery frames
        if (not self.queue and opp.punch.active and not f.punch.active
                and dist < 1.4 and self.rng.random() < p["counter"] * dt * 14.0):
            phase, u = opp.punch_phase()
            if phase == "recover" and u < 0.5:
                self.queue = ["cross"] if self.rng.random() < 0.6 else ["lead_hook"]

        # adapt the stance to how the fight is going
        if self.rng.random() < p["adapt"] * dt * 0.6:
            if f.health < opp.health * 0.7:
                f.stance.nudge(0.10)      # hurt -> tighten up, longer range
            elif opp.health < 45.0:
                f.stance.nudge(-0.12)     # smell blood -> square up for power

    # ------------------------------------------------------------------
    def _pick_combo(self, dist: float, opp: Fighter):
        pool = COMBOS
        if dist > 1.15:
            pool = [c for c in COMBOS if c[0] in ("jab", "cross", "body_jab")]
        elif dist < 0.85:
            pool = [c for c in COMBOS if any(k in ("uppercut", "lead_hook", "rear_hook",
                                                   "body_hook") for k in c)] or COMBOS
        # if they hide behind a high guard, go downstairs
        if self.guard_rate > 0.35 and self.rng.random() < self.p["adapt"]:
            pool = [c for c in COMBOS if any("body" in k for k in c)] or pool
        combo = list(self.rng.choice(pool))
        maxlen = 1 + int(self.p["combo"] * 3.2)
        if opp.block and self.rng.random() < 0.5:
            combo = [k if "body" not in k else k for k in combo]
            combo.insert(0, "body_jab")
        return combo[:max(1, maxlen)]
