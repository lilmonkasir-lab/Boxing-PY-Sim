"""Hit detection and damage resolution."""
from __future__ import annotations

import math
import random

import numpy as np

from ..engine import math3d as m3
from .fighter import PUNCHES, Fighter, PunchState
from .skills import CounterWindow

HEAD_RADIUS = 0.30
BODY_RADIUS = 0.42


class HitResult:
    __slots__ = ("landed", "blocked", "point", "damage", "to_body", "critical",
                 "punch", "attacker", "defender", "slipped", "parried",
                 "counter", "condition_event")

    def __init__(self, landed=False, blocked=False, point=None, damage=0.0,
                 to_body=False, critical=False, punch=None, attacker=None,
                 defender=None, slipped=False, parried=False, counter=False,
                 condition_event=None):
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
        self.parried = parried
        self.counter = counter
        self.condition_event = condition_event


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

    # --- parry: a well-timed guard tap deflects the shot ----------------
    facing_ok = float(m3.normalize(attacker.pos - defender.pos) @ defender.forward()) > 0.1
    if defender.parry.active and facing_ok and not defender.down:
        q = defender.parry.quality()
        defender.parry.consume()
        defender.parries_landed += 1
        # a clean parry costs the attacker their balance and momentum
        attacker.stun = max(attacker.stun, 0.16 + 0.34 * q)
        attacker.combo = 0
        attacker.momentum.drain(0.30)
        attacker.punch = PunchState()
        defender.momentum.add(0.16 + 0.12 * q)
        defender.stamina = max(0.0, defender.stamina - 2.0)
        defender.last_parry_flash = 1.0
        return HitResult(landed=False, parried=True, point=glove.copy(),
                         punch=pdef, attacker=attacker, defender=defender)

    # --- did the defender slip it? -----------------------------------
    slip_chance = defender.evasion
    if not to_body and defender.duck > 0.55 and not defender.down:
        return HitResult(landed=False, slipped=True, point=glove.copy(),
                         punch=pdef, attacker=attacker, defender=defender)
    if (not to_body and slip_chance > 0.0 and not defender.down
            and rng.random() < slip_chance):
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

    power = attacker.effective_power
    fatigue = 0.62 + 0.38 * (attacker.stamina / max(attacker.stats.stamina_max, 1e-6))
    critical = (not blocked) and rng.random() < 0.10 + 0.05 * attacker.combo
    damage = pdef.damage * power * fatigue
    if critical:
        damage *= 1.7

    # counter: landing inside the opponent's recovery frames
    counter_mult = CounterWindow.bonus_against(defender)
    is_counter = (not blocked) and counter_mult > 1.3
    if not blocked:
        damage *= counter_mult
        if is_counter:
            critical = True
            attacker.counters_landed += 1

    stun = pdef.stun * (1.35 if critical else 1.0)
    direction = m3.normalize(defender.pos - attacker.pos)
    if m3.length(direction) < 1e-5:
        direction = attacker.forward()

    defender.take_hit(damage, stun, direction, blocked, to_body)

    condition_event = None
    if not blocked:
        attacker.stats_landed += 1
        attacker.damage_dealt += damage
        attacker.combo += 1
        attacker.combo_timer = 1.35
        # momentum swings on clean work
        attacker.momentum.add(0.055 + damage * 0.004 + (0.06 if is_counter else 0.0))
        defender.momentum.drain(0.05 + damage * 0.003)
        condition_event = defender.condition.take(damage, not to_body, rng)
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
                     punch=pdef, attacker=attacker, defender=defender,
                     counter=is_counter, condition_event=condition_event)


def distance_between(a: Fighter, b: Fighter) -> float:
    d = a.pos - b.pos
    d[1] = 0.0
    return m3.length(d)
