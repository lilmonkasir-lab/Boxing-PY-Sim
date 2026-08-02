"""Match / round state machine: bells, knockdowns, counts, judging."""
from __future__ import annotations

import math
import random

from ..engine import math3d as m3
from .ai import BoxerAI
from .combat import distance_between, resolve_punch
from .fighter import Fighter, FighterStats


class Match:
    ROUND_LENGTH = 120.0
    REST_LENGTH = 8.0

    def __init__(self, arena, player_stats: FighterStats, opp_stats: FighterStats,
                 rounds=3, difficulty="Contender", round_length=None, seed=None):
        self.arena = arena
        self.rng = random.Random(seed)
        self.total_rounds = rounds
        self.round_length = round_length or self.ROUND_LENGTH

        self.player = Fighter(player_stats, arena.corner_pos(True), 0.0, True)
        self.opponent = Fighter(opp_stats, arena.corner_pos(False), math.pi, False)
        self.ai = BoxerAI(self.opponent, difficulty, seed)

        self.round_no = 1
        self.round_time = self.round_length
        self.state = "intro"     # intro | fight | knockdown | rest | over
        self.state_t = 0.0
        self.count = 0.0
        self.down_fighter = None
        self.getup_progress = 0.0
        self.getup_decay = 0.55
        self.score_player = 0
        self.score_opponent = 0
        self._round_start_p = 0.0
        self._round_start_o = 0.0
        self._round_start_kd_p = 0
        self._round_start_kd_o = 0
        self.result_title = ""
        self.result_sub = ""
        self.events = []          # consumed by the app for fx/audio
        self.slow_mo = 0.0
        self.finish_cam = 0.0

        self._snapshot_round()
        self._place_fighters()

    # ------------------------------------------------------------------
    def _place_fighters(self):
        self.player.reset_round(m3.vec3(-1.6, self.arena.canvas_y, -1.6), 0.0)
        self.opponent.reset_round(m3.vec3(1.6, self.arena.canvas_y, 1.6), math.pi)
        to = self.opponent.pos - self.player.pos
        self.player.facing = math.atan2(float(to[0]), float(to[2]))
        self.opponent.facing = self.player.facing + math.pi

    def emit(self, kind, **kw):
        self.events.append(dict(kind=kind, **kw))

    def drain_events(self):
        e = self.events
        self.events = []
        return e

    # ------------------------------------------------------------------
    @property
    def fighting(self) -> bool:
        return self.state == "fight"

    def update(self, dt: float, player_input):
        self.state_t += dt
        if self.slow_mo > 0.0:
            self.slow_mo = max(0.0, self.slow_mo - dt)
        if self.finish_cam > 0.0:
            self.finish_cam = max(0.0, self.finish_cam - dt)

        handler = getattr(self, f"_state_{self.state}")
        handler(dt, player_input)

    # ------------------------------------------------------------------
    def _state_intro(self, dt, pin):
        self._sim_fighters(dt, pin, allow=False)
        if self.state_t > 2.4:
            self.state = "fight"
            self.state_t = 0.0
            self.emit("bell")
            self.emit("announce", text=f"ROUND {self.round_no}", sub="BOX!")

    def _state_fight(self, dt, pin):
        self.round_time -= dt
        self._sim_fighters(dt, pin, allow=True)
        self._resolve_combat()

        if self.player.down or self.opponent.down:
            self.down_fighter = self.player if self.player.down else self.opponent
            self.state = "knockdown"
            self.state_t = 0.0
            self.count = 0.0
            self.getup_progress = 0.25 if self.down_fighter is self.player else 0.0
            self.slow_mo = 0.9
            self.finish_cam = 3.0
            self.emit("knockdown", fighter=self.down_fighter)
            return

        if self.round_time <= 0.0:
            self.round_time = 0.0
            self._end_round()

    def _state_knockdown(self, dt, pin):
        self._sim_fighters(dt, pin, allow=False)
        # standing fighter walks to a neutral corner
        if self.state_t > 1.0:
            self.count += dt * 0.85
        d = self.down_fighter
        if d is self.player:
            self.getup_progress = max(0.0, self.getup_progress - self.getup_decay * dt)
            if pin.get("mash"):
                self.getup_progress = min(1.0, self.getup_progress + 0.135)
        else:
            # AI recovery chance depends on how hurt it is
            target = 0.85 - self.opponent.knockdowns * 0.22
            self.getup_progress = min(1.0, self.getup_progress + dt * 0.30)
            if self.count > 6.0 and self.getup_progress < target:
                self.getup_progress = 0.0 if self.rng.random() < 0.02 else self.getup_progress

        up = self.getup_progress >= 1.0 if d is self.player else \
            (self.count > 5.0 and self.getup_progress > (0.62 - 0.2 * d.knockdowns))

        if up and self.count < 10.0:
            d.revive(38.0 - d.knockdowns * 6.0)
            self.state = "fight"
            self.state_t = 0.0
            self.emit("announce", text="BOX!", sub="")
            self.emit("getup", fighter=d)
            self._separate()
            return

        if self.count >= 10.0 or d.knockdowns >= 3:
            d.out = True
            winner = self.opponent if d is self.player else self.player
            reason = "KNOCKOUT" if d.knockdowns < 3 else "TECHNICAL KNOCKOUT"
            self._finish(winner, reason)

    def _state_rest(self, dt, pin):
        self._sim_fighters(dt, pin, allow=False)
        self.round_time = max(0.0, self.round_time - dt)
        # corner recovery
        for f in (self.player, self.opponent):
            f.health = min(100.0, f.health + dt * 2.4)
            f.stamina = min(f.stats.stamina_max, f.stamina + dt * 7.0)
        if self.round_time <= 0.0:
            self.round_no += 1
            self.round_time = self.round_length
            self.state = "intro"
            self.state_t = 0.0
            self._place_fighters()

    def _state_over(self, dt, pin):
        self._sim_fighters(dt, pin, allow=False)

    # ------------------------------------------------------------------
    def _sim_fighters(self, dt, pin, allow=True):
        p, o = self.player, self.opponent
        move = pin.get("move", (0.0, 0.0)) if allow else (0.0, 0.0)
        block = pin.get("block", False) if allow else False
        duck = pin.get("duck", False) if allow else False
        if allow:
            if pin.get("parry") and p.parry.trigger():
                self.emit("parry_attempt", fighter=p)
            if pin.get("stance_toggle"):
                p.stance.toggle_side()
                self.emit("stance", fighter=p, text=p.stance.name)
            sn = pin.get("stance_nudge", 0.0)
            if sn:
                p.stance.nudge(sn)
            for key in pin.get("punches", ()):
                if p.try_punch(key):
                    self.emit("throw", fighter=p, key=key)

        p.update(dt, o, self.arena, move, block, duck, allow_input=allow)

        self.ai.update(dt if allow else dt * 0.4, p, self.arena)
        if allow:
            before = o.punch.key
            if self.ai.want_parry:
                o.parry.trigger()
            o.update(dt, p, self.arena, self.ai.move, self.ai.want_block,
                     self.ai.want_duck, allow_input=True)
            if o.punch.key and o.punch.key != before and o.punch.t < 1e-4:
                self.emit("throw", fighter=o, key=o.punch.key)
        else:
            o.update(dt, p, self.arena, (0.0, 0.0), False, False, allow_input=False)

    def _resolve_combat(self):
        for att, dfn in ((self.player, self.opponent), (self.opponent, self.player)):
            res = resolve_punch(att, dfn, self.rng)
            if res is None:
                continue
            if res.parried:
                self.emit("parry", point=res.point, attacker=att, defender=dfn)
            elif res.slipped:
                self.emit("slip", point=res.point, defender=dfn)
            elif res.blocked:
                self.emit("block", point=res.point, damage=res.damage,
                          attacker=att, defender=dfn)
            else:
                self.emit("hit", point=res.point, damage=res.damage,
                          critical=res.critical, to_body=res.to_body,
                          attacker=att, defender=dfn, punch=res.punch,
                          counter=res.counter)
                if res.condition_event:
                    self.emit(res.condition_event, fighter=dfn)
                if res.critical:
                    self.slow_mo = max(self.slow_mo, 0.22)
                if att.momentum.in_zone and att.momentum.zone > 4.9:
                    self.emit("zone", fighter=att)

        # whiff detection: punch finished without landing
        for f in (self.player, self.opponent):
            if f.punch.active and not f.punch.landed:
                phase, u = f.punch_phase()
                if phase == "recover" and u < 0.1:
                    f.punch.landed = True   # mark handled
                    f.combo = 0
                    self.emit("whiff", fighter=f)

    def _snapshot_round(self):
        """Remember cumulative totals so a round can be judged in isolation."""
        self._round_start_p = self.player.damage_dealt
        self._round_start_o = self.opponent.damage_dealt
        self._round_start_kd_p = self.player.knockdowns
        self._round_start_kd_o = self.opponent.knockdowns

    def _separate(self):
        p, o = self.player, self.opponent
        d = p.pos - o.pos
        d[1] = 0
        if m3.length(d) < 1e-4:
            d = m3.vec3(1, 0, 0)
        d = m3.normalize(d)
        p.pos = p.pos + d * 0.9
        o.pos = o.pos - d * 0.9
        p.pos, _ = self.arena.clamp_to_ring(p.pos)
        o.pos, _ = self.arena.clamp_to_ring(o.pos)

    # ------------------------------------------------------------------
    def _end_round(self):
        """Score the round on the 10-point-must system.

        Only damage dealt *this round* counts (otherwise whoever won round one
        would automatically win every subsequent round), and each knockdown
        scored costs the fighter who was dropped an extra point.
        """
        pd = self.player.damage_dealt - self._round_start_p
        od = self.opponent.damage_dealt - self._round_start_o
        kd_p = self.player.knockdowns - self._round_start_kd_p      # times player went down
        kd_o = self.opponent.knockdowns - self._round_start_kd_o

        if pd > od * 1.05:
            sp, so = 10, 9
            winner = self.player.stats.name
        elif od > pd * 1.05:
            sp, so = 9, 10
            winner = self.opponent.stats.name
        else:
            sp, so = 10, 10
            winner = "even"
        sp -= kd_p
        so -= kd_o
        if kd_p or kd_o:
            winner = self.player.stats.name if sp > so else (
                self.opponent.stats.name if so > sp else "even")
        self.score_player += sp
        self.score_opponent += so
        self.emit("bell")
        self.emit("announce", text=f"END OF ROUND {self.round_no}",
                  sub=f"round to {winner}")

        if self.round_no >= self.total_rounds:
            self._decision()
        else:
            self.state = "rest"
            self.state_t = 0.0
            self.round_time = self.REST_LENGTH
            self._snapshot_round()

    def _decision(self):
        if self.score_player > self.score_opponent:
            self._finish(self.player, "DECISION")
        elif self.score_opponent > self.score_player:
            self._finish(self.opponent, "DECISION")
        else:
            self._finish(None, "DRAW")

    def _finish(self, winner, reason):
        self.state = "over"
        self.state_t = 0.0
        if winner is None:
            self.result_title = "DRAW"
            self.result_sub = "the judges cannot separate them"
        else:
            self.result_title = f"{winner.stats.name.upper()} WINS"
            self.result_sub = reason
        self.emit("bell")
        self.emit("finish", winner=winner, reason=reason)
