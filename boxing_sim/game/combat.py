"""Hit detection and damage resolution."""
from __future__ import annotations

import math
import random

import numpy as np

from ..engine import math3d as m3
from .fighter import PUNCHES, Fighter

HEAD_RADIUS = 0.30
BODY_RADIUS = 0.42


class HitResult:
    __slots__ = ("landed", "blocked", "point", "damage", "to_body", "critical",
                 "punch", "attacker", "defender", "slipped")

    def __init__(self, landed=False, blocked=False, point=None, damage=0.0,
                 to_body=False, critical=False, punch=None, attacker=None,
                 defender=None, slipped=False):
        self.landed = landed
        self.blocked = blocked
        self.point = point
        self.damage = damage
        self.to_body = to_body
        self.critical = critical
        self.punch = punch
        self.attacker = attacker
        self.defender = defender
        self.slipped = slipped


def resolve_punch(attacker: Fighter, defender: Fighter, rng: random.Random):
    """Check the attacker's in-flight punch against the defender.

    Returns a HitResult if something happened this frame, else None.
    """
    if not attacker.punch.active or attacker.punch.landed:
        return None
    phase, u = attacker.punch_phase()
    if phase != "strike" or u < 0.34:
        return None
    if defender.out:
        return None

    pdef = PUNCHES[attacker.punch.key]
    glove = attacker.glove_world(pdef.hand)
    to_body = pdef.target == "body"
    target = defender.body_pos() if to_body else defender.head_pos()
    radius = BODY_RADIUS if to_body else HEAD_RADIUS

    delta = target - glove
    dist = m3.length(delta)
    if dist > radius + 0.14:
        return None

    attacker.punch.landed = True

    # --- did the defender slip it? -----------------------------------
    if not to_body and defender.duck > 0.55 and not defender.down:
        return HitResult(landed=False, slipped=True, point=glove.copy(),
                         punch=pdef, attacker=attacker, defender=defender)

    # --- blocking ------------------------------------------------------
    facing_dot = float(m3.normalize(attacker.pos - defender.pos) @ defender.forward())
    blocked = False
    if defender.block and facing_dot > 0.25 and not defender.down:
        # high guard covers the head well, body less so
        cover = 0.90 if not to_body else 0.55
        cover *= (1.0 - defender.guard_break * 0.55)
        if defender.stamina < 12.0:
            cover *= 0.6
        blocked = rng.random() < cover

    power = attacker.stats.power
    fatigue = 0.62 + 0.38 * (attacker.stamina / attacker.stats.stamina_max)
    critical = (not blocked) and rng.random() < 0.10 + 0.05 * attacker.combo
    damage = pdef.damage * power * fatigue
    if critical:
        damage *= 1.7
    # counter bonus: hitting someone mid-punch hurts more
    if defender.punch.active and not blocked:
        damage *= 1.28
        critical = True

    stun = pdef.stun * (1.35 if critical else 1.0)
    direction = m3.normalize(defender.pos - attacker.pos)
    if m3.length(direction) < 1e-5:
        direction = attacker.forward()

    defender.take_hit(damage, stun, direction, blocked, to_body)

    if not blocked:
        attacker.stats_landed += 1
        attacker.damage_dealt += damage
        attacker.combo += 1
        attacker.combo_timer = 1.35
        # flash knockdown chance on big shots to a hurt opponent
        if (not defender.down and defender.health > 0.0 and
                damage > 13.0 and defender.health < 42.0 and
                rng.random() < 0.16 + damage * 0.008):
            defender.go_down()
    else:
        attacker.combo = 0

    point = target - m3.normalize(delta) * radius * 0.65 if dist > 1e-5 else target
    return HitResult(landed=not blocked, blocked=blocked, point=point,
                     damage=damage, to_body=to_body, critical=critical,
                     punch=pdef, attacker=attacker, defender=defender)


def distance_between(a: Fighter, b: Fighter) -> float:
    d = a.pos - b.pos
    d[1] = 0.0
    return m3.length(d)
