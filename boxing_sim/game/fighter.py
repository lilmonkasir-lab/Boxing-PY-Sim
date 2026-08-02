"""The boxer: a small skeletal rig, procedurally animated.

The rig is deliberately simple (torso, head, 2 arms x 2 segments + glove,
2 legs x 2 segments) but it is a real hierarchy, so punches, blocks, guard,
stance sway, knockdowns and staggers all come out of joint angles rather than
canned sprite frames.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..engine import math3d as m3
from ..engine.mesh import Mesh
from ..engine import renderer as _R
from ..engine.primitives import box, capsule, cylinder, sphere

# ---------------------------------------------------------------------------
# punch definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PunchDef:
    name: str
    hand: str            # "lead" | "rear"
    wind: float          # seconds of wind-up
    strike: float        # seconds of extension
    recover: float       # seconds back to guard
    reach: float         # measured glove travel from the body centre, metres
    damage: float
    stamina: float
    stun: float
    target: str = "head"   # "head" | "body"
    hook: float = 0.0      # lateral arc
    upward: float = 0.0    # uppercut arc


# `reach` is not a design wish - it is measured from the animated rig by
# tools/calibrate_reach.py, which binary-searches the real hit detection.  The AI compares it against the real distance to
# decide when a punch can land, so if the rig changes these must be re-measured
# or the AI will punch at thin air.
PUNCHES = {
    "jab":       PunchDef("Jab", "lead", 0.055, 0.085, 0.135, 0.80, 6.5, 4.0, 0.16),
    "cross":     PunchDef("Cross", "rear", 0.085, 0.105, 0.185, 1.06, 12.0, 7.5, 0.30),
    "lead_hook": PunchDef("Lead Hook", "lead", 0.095, 0.105, 0.195, 0.70, 11.0, 7.5, 0.32,
                          hook=1.0),
    "rear_hook": PunchDef("Rear Hook", "rear", 0.115, 0.115, 0.225, 0.94, 15.0, 9.5, 0.42,
                          hook=1.0),
    "uppercut":  PunchDef("Uppercut", "rear", 0.125, 0.115, 0.235, 0.78, 16.5, 10.5, 0.46,
                          upward=1.0),
    "body_jab":  PunchDef("Body Jab", "lead", 0.065, 0.090, 0.145, 0.72, 6.0, 4.5, 0.10,
                          target="body"),
    "body_hook": PunchDef("Body Hook", "rear", 0.110, 0.115, 0.220, 0.84, 13.0, 9.0, 0.22,
                          target="body", hook=1.0),
}

PUNCH_ORDER = ["jab", "cross", "lead_hook", "rear_hook", "uppercut", "body_jab", "body_hook"]


# ---------------------------------------------------------------------------
@dataclass
class FighterStats:
    name: str = "Boxer"
    power: float = 1.0
    speed: float = 1.0
    chin: float = 1.0        # damage resistance
    stamina_max: float = 100.0
    reach: float = 1.0
    skin: tuple = (196, 150, 118)
    trunks: tuple = (196, 40, 52)
    trunks_trim: tuple = (240, 240, 240)
    glove: tuple = (208, 36, 46)
    boot: tuple = (238, 238, 242)
    hair: tuple = (36, 28, 24)


# ---------------------------------------------------------------------------
class FighterMeshes:
    """Cached body-part meshes (shared between all fighters of a colourway)."""

    _cache: dict = {}

    def __init__(self, stats: FighterStats):
        key = (stats.skin, stats.trunks, stats.trunks_trim, stats.glove,
               stats.boot, stats.hair)
        cached = FighterMeshes._cache.get(key)
        if cached is not None:
            self.__dict__.update(cached.__dict__)
            return
        s, t, tt = stats.skin, stats.trunks, stats.trunks_trim
        g, b, hr = stats.glove, stats.boot, stats.hair

        # torso: chest + abdomen, slightly tapered
        self.chest = Mesh.combine([
            box(0.56, 0.42, 0.32, s, (0, 0.21, 0)),
            box(0.50, 0.10, 0.30, tuple(min(255, c * 0.94) for c in s), (0, 0.45, 0)),
        ], "chest")
        self.abdomen = Mesh.combine([
            box(0.46, 0.30, 0.28, s, (0, -0.15, 0)),
        ], "abs")
        self.hips = Mesh.combine([
            box(0.50, 0.30, 0.30, t, (0, -0.15, 0)),
            box(0.52, 0.07, 0.32, tt, (0, -0.02, 0)),
        ], "hips")
        self.head = Mesh.combine([
            box(0.26, 0.30, 0.26, s, (0, 0.15, 0)),
            box(0.27, 0.10, 0.25, hr, (0, 0.30, 0)),
            box(0.10, 0.05, 0.03, (30, 30, 34), (-0.07, 0.16, 0.13)),
            box(0.10, 0.05, 0.03, (30, 30, 34), (0.07, 0.16, 0.13)),
        ], "head")
        self.neck = cylinder(0.075, 0.10, 6, tuple(min(255, c * 0.9) for c in s), (0, 0.05, 0))
        # segment meshes span exactly Fighter.UPPER_ARM / Fighter.FOREARM so
        # the visible limb matches the reach used for hit detection
        self.upper_arm = capsule(0.085, 0.36 - 2 * 0.085, 3, 8, s, (0, -0.18, 0))
        self.forearm = capsule(0.078, 0.38 - 2 * 0.078, 3, 8, s, (0, -0.19, 0))
        self.glove = Mesh.combine([
            sphere(0.135, 5, 9, g, (0, -0.02, 0)),
            box(0.16, 0.09, 0.16, tuple(min(255, c * 0.82) for c in g), (0, 0.10, 0)),
        ], "glove")
        self.thigh = capsule(0.105, 0.30, 3, 8, s, (0, -0.20, 0))
        self.shin = capsule(0.088, 0.30, 3, 8, s, (0, -0.20, 0))
        self.foot = Mesh.combine([
            box(0.15, 0.11, 0.30, b, (0, -0.05, 0.05)),
            box(0.14, 0.16, 0.13, b, (0, 0.05, -0.03)),
        ], "boot")
        self.shadow = self._shadow()
        FighterMeshes._cache[key] = self

    @staticmethod
    def _shadow():
        verts = [[0.0, 0.0, 0.0]]
        faces, cols = [], []
        n = 12
        for i in range(n + 1):
            a = 2 * math.pi * i / n
            verts.append([math.cos(a) * 0.42, 0.0, math.sin(a) * 0.30])
        for i in range(1, n + 1):
            faces.append([0, i + 1, i])
            cols.append((44, 44, 56))
        return Mesh(np.array(verts, np.float32), np.array(faces, np.int32),
                    np.array(cols, np.float32), "shadow")


# ---------------------------------------------------------------------------
@dataclass
class PunchState:
    key: str = ""
    t: float = 0.0
    total: float = 0.0
    landed: bool = False
    hand: str = "lead"

    @property
    def active(self) -> bool:
        return self.key != ""


class Fighter:
    """A boxer: state machine + procedural animation + hit volumes."""

    HEIGHT = 1.82
    # Arm segment lengths.  These are the numbers that decide whether a punch
    # can physically reach the opponent, so they are tuned against the combat
    # ranges in PUNCHES (a fully extended cross must cover ~1.4 m from the
    # body centre) rather than against strict human proportions.
    UPPER_ARM = 0.36
    FOREARM = 0.38

    def __init__(self, stats: FighterStats, pos, facing: float, is_player: bool):
        self.stats = stats
        self.meshes = FighterMeshes(stats)
        self.pos = np.asarray(pos, dtype=np.float32).copy()
        self.vel = m3.vec3()
        self.facing = facing           # yaw, radians; 0 => +Z
        self.is_player = is_player

        self.health = 100.0
        self.stamina = stats.stamina_max
        self.punch = PunchState()
        self.block = False
        self.block_hold = 0.0
        self.duck = 0.0
        self.duck_target = 0.0
        self.lean = 0.0
        self.lean_target = 0.0
        self.stun = 0.0
        self.hurt_flash = 0.0
        self.down = False
        self.down_timer = 0.0
        self.get_up_t = 0.0
        self.knockdowns = 0
        self.out = False
        self.guard_break = 0.0
        self.dodge_cool = 0.0
        self.combo = 0
        self.combo_timer = 0.0

        self.bob = 0.0
        # world point the punching hand steers toward (set from the opponent)
        self.aim_point = np.asarray(pos, dtype=np.float32) + m3.vec3(0, 1.6, 1.0)
        self._t = 0.0
        self._step = 0.0
        self._recoil = 0.0
        self._recoil_dir = m3.vec3()
        self._last_hit_dir = m3.vec3(0, 0, 1)

        self.stats_landed = 0
        self.stats_thrown = 0
        self.stats_blocked = 0
        self.damage_dealt = 0.0

        # joint angles (radians) - filled by _animate
        self.j = {}
        self._matrices = {}

    # ------------------------------------------------------------------
    @property
    def alive(self) -> bool:
        return not self.out

    @property
    def busy(self) -> bool:
        return self.punch.active or self.down or self.stun > 0.0

    def forward(self) -> np.ndarray:
        return m3.vec3(math.sin(self.facing), 0.0, math.cos(self.facing))

    def right(self) -> np.ndarray:
        return m3.vec3(math.cos(self.facing), 0.0, -math.sin(self.facing))

    def head_pos(self) -> np.ndarray:
        h = self.HEIGHT - 0.16 - self.duck * 0.42
        return self.pos + m3.vec3(0, h, 0)

    def body_pos(self) -> np.ndarray:
        return self.pos + m3.vec3(0, 1.06 - self.duck * 0.30, 0)

    # ------------------------------------------------------------------
    def try_punch(self, key: str) -> bool:
        if self.down or self.out or self.stun > 0.05 or self.punch.active:
            return False
        p = PUNCHES[key]
        cost = p.stamina * (1.6 if self.stamina < 25 else 1.0)
        if self.stamina < cost * 0.5:
            return False
        spd = self.stats.speed * (0.72 + 0.28 * (self.stamina / self.stats.stamina_max))
        total = (p.wind + p.strike + p.recover) / max(0.35, spd)
        self.punch = PunchState(key, 0.0, total, False, p.hand)
        self.stamina = max(0.0, self.stamina - cost)
        self.stats_thrown += 1
        self.block = False
        return True

    def punch_phase(self):
        """Return (phase, u) where phase in {wind, strike, recover}."""
        if not self.punch.active:
            return "idle", 0.0
        p = PUNCHES[self.punch.key]
        span = p.wind + p.strike + p.recover
        t = self.punch.t / max(self.punch.total, 1e-6) * span
        if t < p.wind:
            return "wind", t / p.wind
        if t < p.wind + p.strike:
            return "strike", (t - p.wind) / p.strike
        return "recover", (t - p.wind - p.strike) / max(p.recover, 1e-6)

    def glove_world(self, hand: str) -> np.ndarray:
        mat = self._matrices.get(f"glove_{hand}")
        if mat is None:
            return self.body_pos()
        return mat[:3, 3].copy()

    # ------------------------------------------------------------------
    def take_hit(self, damage: float, stun: float, from_dir, blocked: bool,
                 to_body: bool):
        if self.out:
            return
        self._last_hit_dir = m3.normalize(np.asarray(from_dir, np.float32))
        if blocked:
            self.stamina = max(0.0, self.stamina - damage * 0.32)
            self.guard_break = min(1.0, self.guard_break + damage * 0.017)
            self.stun = max(self.stun, stun * 0.22)
            self._recoil = min(0.5, self._recoil + 0.16)
            self.stats_blocked += 1
        else:
            dmg = damage / max(0.4, self.stats.chin)
            if to_body:
                self.stamina = max(0.0, self.stamina - dmg * 1.35)
                dmg *= 0.62
            self.health = max(0.0, self.health - dmg)
            self.stun = max(self.stun, stun)
            self.hurt_flash = 1.0
            self._recoil = min(1.0, self._recoil + 0.45)
            self.punch = PunchState()
        self._recoil_dir = self._last_hit_dir
        self.vel = self.vel + self._last_hit_dir * (1.9 if not blocked else 0.7)

        if not blocked and self.health <= 0.0:
            self.go_down()

    def go_down(self):
        if self.down:
            return
        self.down = True
        self.down_timer = 0.0
        self.knockdowns += 1
        self.punch = PunchState()
        self.stun = 0.0

    def revive(self, health: float = 45.0):
        self.down = False
        self.down_timer = 0.0
        self.get_up_t = 1.0
        self.health = max(self.health, health)
        self.stamina = max(self.stamina, 40.0)
        self.stun = 0.0

    def reset_round(self, pos, facing):
        self.pos = np.asarray(pos, np.float32).copy()
        self.vel = m3.vec3()
        self.facing = facing
        self.stun = 0.0
        self.down = False
        self.punch = PunchState()
        self.stamina = min(self.stats.stamina_max,
                           self.stamina + self.stats.stamina_max * 0.42)
        self.health = min(100.0, self.health + 12.0)
        self.guard_break = max(0.0, self.guard_break - 0.5)

    # ------------------------------------------------------------------
    def update(self, dt: float, opponent: "Fighter", arena, move=(0.0, 0.0),
               want_block=False, duck=False, allow_input=True):
        self._t += dt

        if self.out:
            self._animate(dt)
            return

        if self.down:
            self.down_timer += dt
            self.vel *= math.exp(-6.0 * dt)
            self.pos = self.pos + self.vel * dt
            self.pos, _ = arena.clamp_to_ring(self.pos, 0.30)
            self._animate(dt)
            return

        self.get_up_t = max(0.0, self.get_up_t - dt)
        self.stun = max(0.0, self.stun - dt)
        self.hurt_flash = max(0.0, self.hurt_flash - dt * 2.4)
        self._recoil = max(0.0, self._recoil - dt * 3.2)
        self.guard_break = max(0.0, self.guard_break - dt * 0.12)
        self.dodge_cool = max(0.0, self.dodge_cool - dt)
        if self.combo_timer > 0.0:
            self.combo_timer -= dt
            if self.combo_timer <= 0.0:
                self.combo = 0

        stunned = self.stun > 0.0 or self.get_up_t > 0.0
        can_act = allow_input and not stunned

        # --- guard / stamina -------------------------------------------
        self.block = bool(want_block) and can_act and not self.punch.active
        self.duck_target = 1.0 if (duck and can_act and not self.punch.active) else 0.0
        self.duck = m3.damp(self.duck, self.duck_target, 14.0, dt)

        regen = 15.5 if self.block else (11.0 if not self.punch.active else 3.0)
        if self.down or stunned:
            regen = 6.0
        self.stamina = min(self.stats.stamina_max, self.stamina + regen * dt)

        # --- movement ---------------------------------------------------
        mx, mz = float(move[0]), float(move[1])
        mag = math.hypot(mx, mz)
        if mag > 1.0:
            mx, mz = mx / mag, mz / mag
            mag = 1.0
        speed = 3.05 * self.stats.speed
        if self.block:
            speed *= 0.52
        if self.punch.active:
            speed *= 0.30
        if self.stamina < 22:
            speed *= 0.72
        if stunned:
            speed *= 0.25
        wish = (self.right() * mx + self.forward() * mz) * speed
        if not can_act:
            wish = m3.vec3()
        accel = 15.0 if mag > 0.01 else 11.0
        self.vel = m3.vec3(*(m3.damp(self.vel, wish, accel, dt)))
        self.pos = self.pos + self.vel * dt
        self.pos, hit_ropes = arena.clamp_to_ring(self.pos, 0.34)
        if hit_ropes:
            self.vel[0] *= 0.2
            self.vel[2] *= 0.2

        # --- keep distance from opponent (no clipping through each other)
        d = self.pos - opponent.pos
        d[1] = 0.0
        dist = m3.length(d)
        min_d = 0.62
        if dist < min_d and dist > 1e-5:
            push = d / dist * (min_d - dist) * 0.5
            self.pos = self.pos + push
            opponent.pos = opponent.pos - push
            self.pos, _ = arena.clamp_to_ring(self.pos, 0.34)
            opponent.pos, _ = arena.clamp_to_ring(opponent.pos, 0.34)

        # --- aim ------------------------------------------------------
        if self.punch.active:
            p_def = PUNCHES[self.punch.key]
            self.aim_point = (opponent.body_pos() if p_def.target == "body"
                              else opponent.head_pos())
        else:
            self.aim_point = self.pos + self.forward() * 1.0 + m3.vec3(0, 1.55, 0)

        # --- face the opponent ------------------------------------------
        to = opponent.pos - self.pos
        want = math.atan2(float(to[0]), float(to[2]))
        rate = 9.0 * dt if not stunned else 3.0 * dt
        self.facing = m3.approach_angle(self.facing, want, rate * 1.6)

        # --- lean / bob --------------------------------------------------
        self.lean_target = mx * 0.12
        self.lean = m3.damp(self.lean, self.lean_target, 8.0, dt)
        self._step += m3.length(self.vel) * dt * 2.4
        self.bob = math.sin(self._t * 3.4) * 0.018 + math.sin(self._step * 6.0) * 0.02

        # --- punch timing -------------------------------------------------
        if self.punch.active:
            self.punch.t += dt
            if self.punch.t >= self.punch.total:
                self.punch = PunchState()

        self._animate(dt)

    # ------------------------------------------------------------------
    def _animate(self, dt: float):
        """Compute all joint matrices for this frame."""
        j = self.j
        phase, u = self.punch_phase()
        p = PUNCHES[self.punch.key] if self.punch.active else None

        # extension curve 0..1
        ext = 0.0
        if p is not None:
            if phase == "wind":
                ext = -0.22 * math.sin(u * math.pi * 0.5)
            elif phase == "strike":
                ext = m3.ease_out(u)
            else:
                ext = 1.0 - m3.smoothstep(u)

        guard = 1.0 if not self.punch.active else 0.55
        blk = 1.0 if self.block else 0.0
        stunned = self.stun > 0.0

        # torso
        knock = self._recoil
        j["root_y"] = self.pos[1] + self.bob - self.duck * 0.30
        j["torso_pitch"] = (-0.10 - self.duck * 0.34 - blk * 0.10
                            + knock * 0.28 * float(self._recoil_dir @ self.forward()))
        j["torso_roll"] = self.lean + knock * 0.22 * float(self._recoil_dir @ self.right())
        j["torso_yaw"] = -0.34 + (ext * 0.34 if (p and p.hand == "rear") else 0.0) \
                         - (ext * 0.10 if (p and p.hand == "lead") else 0.0)
        # drive the torso forward behind the shot - this is what gives a
        # boxer the extra ~0.35 m that turns a short arm into real reach
        push = 0.0
        if p is not None:
            push = max(0.0, ext) * (0.38 if p.hand == "rear" else 0.30)
            push *= self.stats.reach
        j["torso_push"] = push
        j["head_pitch"] = 0.06 + self.duck * 0.18 - knock * 0.5
        j["head_yaw"] = -j["torso_yaw"] * 0.4
        if stunned:
            w = math.sin(self._t * 17.0) * self.stun * 0.30
            j["torso_roll"] += w
            j["head_pitch"] += abs(w) * 0.4

        # arms: (shoulder_pitch, shoulder_yaw, elbow, forearm_roll)
        # Arm chain: the limb hangs down -Y from the shoulder, so a shoulder
        # pitch of -pi/2 points it straight forward (+Z) and elbow 0 means
        # fully extended.  Guard = arms folded up in front of the chin.
        for hand in ("lead", "rear"):
            side = -1.0 if hand == "lead" else 1.0     # lead = left = -X
            # high guard: gloves at cheek level but held slightly wide, so the
            # head stays readable from the broadcast camera
            g_pitch = -0.92 - blk * 0.18
            g_yaw = side * (0.46 + blk * 0.10)
            g_roll = -side * (0.40 + blk * 0.14)
            g_elbow = -2.15 - blk * 0.22
            if p is not None and p.hand == hand:
                if p.upward > 0.0:
                    # uppercut: comes up from below, elbow stays bent
                    pitch = m3.lerp(g_pitch, -0.62, ext)
                    yaw = m3.lerp(g_yaw, -side * 0.24, ext)
                    roll = m3.lerp(g_roll, side * 0.10, ext)
                    elbow = m3.lerp(g_elbow, -1.02, ext)
                elif p.hook > 0.0:
                    # hook: arm swings across at shoulder height, or dropped
                    # to rib height for a body hook (which otherwise sails
                    # right over the target)
                    tp = -1.46 if p.target == "head" else -0.98
                    pitch = m3.lerp(g_pitch, tp, ext)
                    yaw = m3.lerp(g_yaw, -side * 0.62, ext)
                    roll = m3.lerp(g_roll, side * 0.30, ext)
                    elbow = m3.lerp(g_elbow, -0.78, ext)
                else:
                    # Straight shot: the shoulder rotates *inward* past centre
                    # so the glove travels down the centre line.  Without this
                    # the fist finishes ~0.45 m off-axis (the shoulder is
                    # offset from the spine) and straight punches sail wide.
                    tp = -1.60 if p.target == "head" else -1.24
                    pitch = m3.lerp(g_pitch, tp, ext)
                    yaw = m3.lerp(g_yaw, -side * 0.30, ext)
                    roll = m3.lerp(g_roll, side * 0.16, ext)
                    elbow = m3.lerp(g_elbow, -0.06, ext)
            else:
                # off hand stays home to guard
                pitch, yaw, roll, elbow = g_pitch, g_yaw, g_roll, g_elbow
                if self.punch.active:
                    pitch -= 0.08 * max(0.0, ext)
            j[f"sh_pitch_{hand}"] = pitch
            j[f"sh_yaw_{hand}"] = yaw
            j[f"sh_roll_{hand}"] = roll
            j[f"elbow_{hand}"] = elbow

        # legs: simple stride based on velocity
        stride = math.sin(self._step * 6.0) * min(1.0, m3.length(self.vel) / 2.4)
        j["hip_lead"] = 0.22 + stride * 0.34 - self.duck * 0.55
        j["hip_rear"] = -0.26 - stride * 0.34 - self.duck * 0.55
        j["knee_lead"] = -0.28 - abs(stride) * 0.22 + self.duck * 0.85
        j["knee_rear"] = -0.34 - abs(stride) * 0.22 + self.duck * 0.85

        # knockdown pose
        if self.down:
            t = min(1.0, self.down_timer / 0.55)
            j["fall"] = m3.ease_out(t)
        elif self.get_up_t > 0.0:
            j["fall"] = m3.smoothstep(self.get_up_t / 1.0) * 0.85
        else:
            j["fall"] = 0.0

        self._build_matrices()
        self._aim_punching_hand()

    # ------------------------------------------------------------------
    def _aim_punching_hand(self):
        """Steer the punching glove onto the aim point.

        The shoulder sits ~0.3 m off the spine and the stance is bladed, so a
        pose built purely from hand-authored joint angles finishes up to half a
        metre wide of the target - straight punches simply sailed past the
        head.  Rather than hand-tune every angle (which silently breaks again
        whenever the rig changes), measure where the glove actually ended up
        and rotate the shoulder by the leftover yaw error.  Costs one extra
        pose build per frame, and only while a punch is in flight.
        """
        j = self.j
        if not self.punch.active:
            if j.get("aim_lead") or j.get("aim_rear"):
                j["aim_lead"] = 0.0
                j["aim_rear"] = 0.0
                self._build_matrices()
            return
        phase, _u = self.punch_phase()
        if phase == "wind":
            return
        hand = PUNCHES[self.punch.key].hand
        other = "rear" if hand == "lead" else "lead"
        M = self._matrices
        shoulder = M[f"upper_{hand}"][:3, 3]
        glove = M[f"glove_{hand}"][:3, 3]
        cur = glove - shoulder
        want = np.asarray(self.aim_point, np.float32) - shoulder
        # yaw only - pitch is what selects head vs body height, and is authored
        err = m3.angle_wrap(math.atan2(float(want[0]), float(want[2])) -
                            math.atan2(float(cur[0]), float(cur[2])))
        err = m3.clamp(err, -1.2, 1.2)
        j[f"aim_{hand}"] = j.get(f"aim_{hand}", 0.0) + err
        j[f"aim_{other}"] = 0.0
        self._build_matrices()

    # ------------------------------------------------------------------
    def _build_matrices(self):
        j = self.j
        M = self._matrices
        fall = j.get("fall", 0.0)

        root = m3.compose(
            m3.translate(float(self.pos[0]), j["root_y"], float(self.pos[2])),
            m3.rot_y(self.facing),
        )
        if fall > 0.001:
            axis = m3.rot_x(-fall * (math.pi / 2 - 0.12))
            root = root @ m3.translate(0, -fall * 0.55, -fall * 0.30) @ axis
        M["root"] = root

        pelvis = root @ m3.translate(0, 0.98, 0)
        M["pelvis"] = pelvis
        M["hips"] = pelvis

        # weight transfer: the whole torso drives forward behind the punch,
        # which is what actually gives a boxer their reach.
        torso = pelvis @ m3.rot_y(j["torso_yaw"]) @ m3.rot_x(j["torso_pitch"]) \
            @ m3.rot_z(j["torso_roll"]) @ m3.translate(0, 0.02, j.get("torso_push", 0.0))
        M["torso"] = torso
        M["abdomen"] = torso
        M["chest"] = torso @ m3.translate(0, 0.06, 0)

        neck = M["chest"] @ m3.translate(0, 0.50, 0)
        M["neck"] = neck
        M["head"] = neck @ m3.translate(0, 0.10, 0) @ m3.rot_y(j["head_yaw"]) \
            @ m3.rot_x(j["head_pitch"])

        for hand in ("lead", "rear"):
            side = -1.0 if hand == "lead" else 1.0
            aim = j.get(f"aim_{hand}", 0.0)
            sh = M["chest"] @ m3.translate(side * 0.30, 0.40, 0.0) \
                @ m3.rot_y(j[f"sh_yaw_{hand}"] + aim) @ m3.rot_x(j[f"sh_pitch_{hand}"]) \
                @ m3.rot_z(j.get(f"sh_roll_{hand}", 0.0))
            M[f"upper_{hand}"] = sh
            el = sh @ m3.translate(0, -self.UPPER_ARM, 0) @ m3.rot_x(j[f"elbow_{hand}"])
            M[f"fore_{hand}"] = el
            M[f"glove_{hand}"] = el @ m3.translate(0, -self.FOREARM, 0)

        for leg in ("lead", "rear"):
            side = -1.0 if leg == "lead" else 1.0
            hp = pelvis @ m3.translate(side * 0.16, -0.16, 0) @ m3.rot_x(j[f"hip_{leg}"])
            M[f"thigh_{leg}"] = hp
            kn = hp @ m3.translate(0, -0.40, 0) @ m3.rot_x(j[f"knee_{leg}"])
            M[f"shin_{leg}"] = kn
            M[f"foot_{leg}"] = kn @ m3.translate(0, -0.40, 0)

    # ------------------------------------------------------------------
    def submit(self, renderer):
        M = self._matrices
        if not M:
            return
        me = self.meshes
        tint = 1.0
        if self.hurt_flash > 0.01:
            tint = 1.0 + self.hurt_flash * 0.85
        if self.out:
            tint *= 0.8

        # shadow (flattened, on the canvas)
        sy = 1.052
        sc = 1.0 - min(0.5, max(0.0, self.pos[1] - 1.05))
        shadow_m = m3.compose(m3.translate(float(self.pos[0]), sy, float(self.pos[2])),
                              m3.scale(sc, 1.0, sc))
        L = _R.LAYER_ACTORS
        # the shadow belongs to the ring surface, not the fighter
        renderer.submit(me.shadow, shadow_m, shade=1.0, sort_bias=-0.05,
                        layer=_R.LAYER_RING)

        renderer.submit(me.hips, M["hips"], tint, layer=L)
        renderer.submit(me.abdomen, M["abdomen"], tint, layer=L)
        renderer.submit(me.chest, M["chest"], tint, layer=L)
        renderer.submit(me.neck, M["neck"], tint, layer=L)
        renderer.submit(me.head, M["head"], tint, layer=L)
        for hand in ("lead", "rear"):
            renderer.submit(me.upper_arm, M[f"upper_{hand}"], tint, layer=L)
            renderer.submit(me.forearm, M[f"fore_{hand}"], tint, layer=L)
            renderer.submit(me.glove, M[f"glove_{hand}"], tint, layer=L)
        for leg in ("lead", "rear"):
            renderer.submit(me.thigh, M[f"thigh_{leg}"], tint, layer=L)
            renderer.submit(me.shin, M[f"shin_{leg}"], tint, layer=L)
            renderer.submit(me.foot, M[f"foot_{leg}"], tint, layer=L)
