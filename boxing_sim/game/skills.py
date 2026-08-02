"""Skill systems that reward timing, reading and ring craft.

Everything here exists to widen the gap between mashing punch keys and boxing
well.  Each mechanic has a tight, learnable timing window and a clear payoff:

* :class:`ParryWindow`  - tap block just before a punch lands to deflect it,
  which costs the attacker their balance instead of your health.
* :class:`CounterWindow` - land inside the opponent's recovery frames for a
  damage bonus.  Rewards patience over volume.
* :class:`Stance`       - orthodox/southpaw plus a bladed/square footwork
  choice, trading reach against power and mobility.
* :class:`Momentum`     - crowd/confidence meter that builds on clean work and
  drains when you get hit, feeding a temporary "in the zone" state.
* :class:`Conditioning` - per-round fatigue, cuts and swelling that accumulate
  across a fight, so a long bout plays differently from round one.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# parrying
# ---------------------------------------------------------------------------
@dataclass
class ParryWindow:
    """A short window opened by *tapping* guard, distinct from holding it.

    Holding block is safe but passive: it bleeds stamina and invites body
    work.  A parry has to be timed against the incoming punch, and pays out
    with a big opening if you get it right.
    """

    DURATION: float = 0.18        # how long a tap stays "hot"
    COOLDOWN: float = 0.42        # stops mashing from covering everything

    timer: float = 0.0
    cooldown: float = 0.0
    consumed: bool = False

    @property
    def active(self) -> bool:
        return self.timer > 0.0 and not self.consumed

    @property
    def ready(self) -> bool:
        return self.cooldown <= 0.0

    def trigger(self) -> bool:
        if not self.ready:
            return False
        self.timer = self.DURATION
        self.cooldown = self.COOLDOWN
        self.consumed = False
        return True

    def quality(self) -> float:
        """1.0 for a frame-perfect parry, falling off across the window."""
        if not self.active:
            return 0.0
        elapsed = self.DURATION - self.timer
        # best in the first third of the window
        return max(0.25, 1.0 - (elapsed / self.DURATION) * 0.75)

    def consume(self) -> None:
        self.consumed = True
        self.timer = 0.0

    def update(self, dt: float) -> None:
        self.timer = max(0.0, self.timer - dt)
        self.cooldown = max(0.0, self.cooldown - dt)


# ---------------------------------------------------------------------------
# counter punching
# ---------------------------------------------------------------------------
class CounterWindow:
    """Tracks whether a fighter is currently vulnerable to a counter.

    A boxer is open while they are recovering from their own punch.  Landing
    in that window is a *counter* and is scored and damaged accordingly.
    """

    #: recovery fraction still counted as counterable
    WINDOW = 0.62
    #: damage multiplier at the very start of the window, tapering to 1.0
    MAX_BONUS = 1.85

    @staticmethod
    def bonus_against(defender) -> float:
        """Damage multiplier for hitting `defender` right now."""
        if not defender.punch.active:
            return 1.0
        phase, u = defender.punch_phase()
        if phase == "strike":
            # trading in the middle of their shot: modest bonus
            return 1.25
        if phase != "recover" or u > CounterWindow.WINDOW:
            return 1.0
        t = 1.0 - (u / CounterWindow.WINDOW)
        return 1.0 + (CounterWindow.MAX_BONUS - 1.0) * t

    @staticmethod
    def is_counter(defender) -> bool:
        return CounterWindow.bonus_against(defender) > 1.3


# ---------------------------------------------------------------------------
# stance and footwork
# ---------------------------------------------------------------------------
@dataclass
class Stance:
    """Orthodox/southpaw plus how square the fighter stands.

    `bladed` runs 0..1.  Bladed (1.0) is the classic side-on stance: longer
    lead hand, harder to hit, but less power through the hips.  Square (0.0)
    is a pressure stance: shorter, more exposed, but heavier and faster to
    move behind.
    """

    southpaw: bool = False
    bladed: float = 0.65

    def toggle_side(self) -> None:
        self.southpaw = not self.southpaw

    def nudge(self, delta: float) -> None:
        self.bladed = max(0.0, min(1.0, self.bladed + delta))

    # -- derived modifiers ------------------------------------------------
    @property
    def reach_mult(self) -> float:
        return 0.92 + 0.16 * self.bladed        # 0.92 square .. 1.08 bladed

    @property
    def power_mult(self) -> float:
        return 1.14 - 0.22 * self.bladed        # square hits harder

    @property
    def evasion(self) -> float:
        return 0.06 * self.bladed               # smaller target side-on

    @property
    def move_speed_mult(self) -> float:
        return 1.10 - 0.14 * self.bladed        # square moves better

    @property
    def name(self) -> str:
        side = "southpaw" if self.southpaw else "orthodox"
        shape = "bladed" if self.bladed > 0.6 else (
            "square" if self.bladed < 0.35 else "neutral")
        return f"{side} / {shape}"


# ---------------------------------------------------------------------------
# momentum
# ---------------------------------------------------------------------------
@dataclass
class Momentum:
    """Confidence / crowd swell.  Fills with clean work, empties when hurt.

    At full it triggers a short "in the zone" burst: faster hands and extra
    power.  It is deliberately easy to lose, so it rewards not getting greedy.
    """

    value: float = 0.0            # 0..1
    zone: float = 0.0             # seconds of active burst remaining
    ZONE_TIME: float = 5.0

    def add(self, amount: float) -> bool:
        """Returns True if this push tipped the fighter into the zone."""
        if self.zone > 0.0:
            return False
        self.value = min(1.0, self.value + amount)
        if self.value >= 1.0:
            self.value = 0.0
            self.zone = self.ZONE_TIME
            return True
        return False

    def drain(self, amount: float) -> None:
        self.value = max(0.0, self.value - amount)
        if amount > 0.25:
            self.zone = 0.0

    @property
    def in_zone(self) -> bool:
        return self.zone > 0.0

    @property
    def power_mult(self) -> float:
        return 1.28 if self.in_zone else 1.0

    @property
    def speed_mult(self) -> float:
        return 1.20 if self.in_zone else 1.0

    def update(self, dt: float) -> None:
        self.zone = max(0.0, self.zone - dt)
        # confidence ebbs slowly if nothing is happening
        if not self.in_zone:
            self.value = max(0.0, self.value - dt * 0.035)


# ---------------------------------------------------------------------------
# damage accumulation
# ---------------------------------------------------------------------------
@dataclass
class Conditioning:
    """Lasting damage: cuts, swelling and deep fatigue.

    Unlike health (which recovers between rounds) these persist for the whole
    fight, so damage taken in round one still matters in round ten.
    """

    cut: float = 0.0              # 0..1  bleeding, blurs vision
    swelling: float = 0.0         # 0..1  eye closing, narrows evasion
    deep_fatigue: float = 0.0     # 0..1  permanent stamina ceiling loss

    def take(self, damage: float, to_head: bool, rng) -> str | None:
        """Apply lasting damage.  Returns an event name if something opened."""
        event = None
        if to_head:
            if damage > 13.0 and rng.random() < 0.16 + damage * 0.006:
                was = self.cut
                self.cut = min(1.0, self.cut + 0.28)
                if was < 0.05:
                    event = "cut"
            if damage > 9.0 and rng.random() < 0.22:
                was = self.swelling
                self.swelling = min(1.0, self.swelling + 0.16)
                if was < 0.4 <= self.swelling:
                    event = event or "swelling"
        self.deep_fatigue = min(0.8, self.deep_fatigue + damage * 0.0022)
        return event

    @property
    def stamina_ceiling(self) -> float:
        """Fraction of max stamina still reachable."""
        return 1.0 - self.deep_fatigue * 0.45

    @property
    def evasion_penalty(self) -> float:
        return self.swelling * 0.5

    def round_recovery(self) -> None:
        """The corner works on you between rounds."""
        self.cut = max(0.0, self.cut - 0.35)
        self.swelling = max(0.0, self.swelling - 0.12)


# ---------------------------------------------------------------------------
# combo scoring
# ---------------------------------------------------------------------------
COMBO_NAMES = {
    2: "DOUBLE",
    3: "TRIPLE",
    4: "FOUR PUNCH",
    5: "FIVE PUNCH",
    6: "SIX PUNCH",
    7: "BLISTERING",
    8: "MERCILESS",
}


def combo_label(n: int) -> str:
    if n >= 9:
        return "UNANSWERED"
    return COMBO_NAMES.get(n, "")


def combo_multiplier(n: int) -> float:
    """Damage scaling for sustained pressure, capped so it cannot run away."""
    return min(1.45, 1.0 + max(0, n - 1) * 0.055)
