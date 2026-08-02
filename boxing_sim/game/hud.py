"""Broadcast-style HUD: health/stamina bars, round clock, scorecards, prompts."""
from __future__ import annotations

import math

import pygame

WHITE = (245, 246, 250)
DIM = (150, 155, 172)
RED = (214, 52, 62)
BLUE = (58, 108, 214)
GOLD = (245, 200, 96)
BG = (14, 15, 24)


def _bar(surface, rect, frac, color, back=(34, 36, 50), border=(8, 9, 16),
         flip=False, glow=0.0):
    x, y, w, h = rect
    pygame.draw.rect(surface, border, (x - 2, y - 2, w + 4, h + 4), border_radius=4)
    pygame.draw.rect(surface, back, (x, y, w, h), border_radius=3)
    fw = int(w * max(0.0, min(1.0, frac)))
    if fw > 0:
        rx = x + w - fw if flip else x
        pygame.draw.rect(surface, color, (rx, y, fw, h), border_radius=3)
        # gloss
        gl = pygame.Surface((fw, max(1, h // 2)), pygame.SRCALPHA)
        gl.fill((255, 255, 255, 34))
        surface.blit(gl, (rx, y))
    if glow > 0.01:
        s = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
        a = int(120 * glow)
        pygame.draw.rect(s, (255, 90, 90, a), (0, 0, w + 8, h + 8), border_radius=6, width=3)
        surface.blit(s, (x - 4, y - 4))


class HUD:
    def __init__(self, width, height):
        self.w = width
        self.h = height
        pygame.font.init()
        self.f_big = pygame.font.SysFont("dejavusans,arial", 44, bold=True)
        self.f_mid = pygame.font.SysFont("dejavusans,arial", 24, bold=True)
        self.f_small = pygame.font.SysFont("dejavusans,arial", 17, bold=True)
        self.f_tiny = pygame.font.SysFont("dejavusans,arial", 14)
        self.f_float = pygame.font.SysFont("dejavusans,arial", 30, bold=True)
        self.announce = ""
        self.announce_t = 0.0
        self.announce_sub = ""
        self.toast = []

    def resize(self, w, h):
        self.w, self.h = w, h

    # ------------------------------------------------------------------
    def say(self, text, sub="", t=2.0):
        self.announce = text
        self.announce_sub = sub
        self.announce_t = t

    def add_toast(self, text, color=WHITE, life=1.6):
        self.toast.append([text, color, life, life])

    def update(self, dt):
        self.announce_t = max(0.0, self.announce_t - dt)
        for t in self.toast:
            t[2] -= dt
        self.toast = [t for t in self.toast if t[2] > 0]

    # ------------------------------------------------------------------
    def draw(self, surface, match):
        w, h = self.w, self.h
        p, o = match.player, match.opponent

        # ---- top banner ------------------------------------------------
        band = pygame.Surface((w, 92), pygame.SRCALPHA)
        band.fill((10, 11, 20, 190))
        surface.blit(band, (0, 0))
        pygame.draw.line(surface, (60, 64, 90), (0, 92), (w, 92), 2)

        bar_w = int(w * 0.31)
        # player (left)
        _bar(surface, (24, 40, bar_w, 20), p.health / 100.0, RED,
             glow=1.0 if p.health < 25 else 0.0)
        _bar(surface, (24, 64, bar_w, 9), p.stamina / p.stats.stamina_max, (86, 196, 120))
        nm = self.f_small.render(p.stats.name.upper(), True, WHITE)
        surface.blit(nm, (24, 18))
        # opponent (right)
        ox = w - 24 - bar_w
        _bar(surface, (ox, 40, bar_w, 20), o.health / 100.0, BLUE, flip=True,
             glow=1.0 if o.health < 25 else 0.0)
        _bar(surface, (ox, 64, bar_w, 9), o.stamina / o.stats.stamina_max,
             (86, 196, 120), flip=True)
        nm = self.f_small.render(o.stats.name.upper(), True, WHITE)
        surface.blit(nm, (w - 24 - nm.get_width(), 18))

        # ---- round clock -------------------------------------------------
        secs = max(0.0, match.round_time)
        clock = f"{int(secs // 60)}:{int(secs % 60):02d}"
        col = GOLD if secs > 10 or match.state != "fight" else (250, 90, 90)
        ct = self.f_big.render(clock, True, col)
        surface.blit(ct, (w // 2 - ct.get_width() // 2, 12))
        rt = self.f_small.render(f"ROUND {match.round_no}/{match.total_rounds}", True, DIM)
        surface.blit(rt, (w // 2 - rt.get_width() // 2, 60))

        # knockdown pips
        for i in range(p.knockdowns):
            pygame.draw.circle(surface, RED, (30 + i * 16, 68), 4)
        for i in range(o.knockdowns):
            pygame.draw.circle(surface, BLUE, (w - 30 - i * 16, 68), 4)

        # ---- momentum meters -------------------------------------------
        # sits under the health bars: fills with clean work, empties when hurt
        for f, x, flip in ((p, 24, False), (o, w - 24 - bar_w, True)):
            mv = f.momentum
            col = (255, 208, 96) if not mv.in_zone else (255, 120, 220)
            frac = 1.0 if mv.in_zone else mv.value
            _bar(surface, (x, 76, bar_w, 5), frac, col, back=(26, 27, 38),
                 flip=flip, glow=0.8 if mv.in_zone else 0.0)

        # ---- stance + damage readout ------------------------------------
        st = self.f_tiny.render(p.stance.name, True, (150, 168, 210))
        surface.blit(st, (24, 86))
        marks = []
        if p.condition.cut > 0.05:
            marks.append(("CUT", (235, 70, 70)))
        if p.condition.swelling > 0.35:
            marks.append(("SWELLING", (235, 160, 70)))
        mx = 24 + st.get_width() + 12
        for text, mc in marks:
            t = self.f_tiny.render(text, True, mc)
            surface.blit(t, (mx, 86))
            mx += t.get_width() + 10

        # ---- combo counter --------------------------------------------------
        if p.combo > 1:
            from .skills import combo_label
            name = combo_label(p.combo)
            label = f"{p.combo} HIT {name}".strip() if name else f"{p.combo} HIT COMBO"
            c = self.f_mid.render(label, True, GOLD)
            surface.blit(c, (w // 2 - c.get_width() // 2, 104))
        if p.momentum.in_zone:
            z = self.f_small.render("IN THE ZONE", True, (255, 120, 220))
            surface.blit(z, (w // 2 - z.get_width() // 2, 132))

        # ---- stats strip ----------------------------------------------------
        acc_p = (p.stats_landed / p.stats_thrown * 100) if p.stats_thrown else 0.0
        acc_o = (o.stats_landed / o.stats_thrown * 100) if o.stats_thrown else 0.0
        s1 = self.f_tiny.render(f"landed {p.stats_landed}/{p.stats_thrown}  ({acc_p:.0f}%)",
                                True, DIM)
        surface.blit(s1, (24, 100))
        s2 = self.f_tiny.render(f"landed {o.stats_landed}/{o.stats_thrown}  ({acc_o:.0f}%)",
                                True, DIM)
        surface.blit(s2, (w - 24 - s2.get_width(), 100))

        # ---- toasts -----------------------------------------------------------
        y = 150
        for text, color, life, maxlife in self.toast[-5:]:
            s = self.f_small.render(text, True, color)
            s.set_alpha(int(255 * min(1.0, life / maxlife * 2.4)))
            surface.blit(s, (24, y))
            y += 22

        # ---- announcement ------------------------------------------------------
        if self.announce_t > 0.0 and self.announce:
            k = min(1.0, self.announce_t * 2.2)
            scale = 1.0 + 0.12 * (1.0 - min(1.0, self.announce_t))
            txt = self.f_big.render(self.announce, True, GOLD)
            txt = pygame.transform.smoothscale(
                txt, (int(txt.get_width() * scale), int(txt.get_height() * scale)))
            txt.set_alpha(int(255 * k))
            sh = pygame.Surface((txt.get_width() + 40, txt.get_height() + 20), pygame.SRCALPHA)
            sh.fill((8, 8, 16, int(150 * k)))
            surface.blit(sh, (w // 2 - sh.get_width() // 2, h // 2 - 90))
            surface.blit(txt, (w // 2 - txt.get_width() // 2, h // 2 - 80))
            if self.announce_sub:
                sub = self.f_mid.render(self.announce_sub, True, WHITE)
                sub.set_alpha(int(255 * k))
                surface.blit(sub, (w // 2 - sub.get_width() // 2, h // 2 - 26))

        # ---- controls hint -------------------------------------------------------
        hint = ("WASD  J/K jab-cross  U/I hooks  O upper  H/L body   "
                "SPACE guard  F PARRY  SHIFT slip  Z/X stance  Q switch  C cam")
        s = self.f_tiny.render(hint, True, (120, 126, 146))
        bg = pygame.Surface((s.get_width() + 20, s.get_height() + 8), pygame.SRCALPHA)
        bg.fill((8, 9, 16, 150))
        surface.blit(bg, (w // 2 - bg.get_width() // 2, h - 34))
        surface.blit(s, (w // 2 - s.get_width() // 2, h - 30))

    # ------------------------------------------------------------------
    def draw_count(self, surface, match):
        """Referee's count during a knockdown."""
        n = int(match.count) + 1
        n = min(10, n)
        w, h = self.w, self.h
        pulse = 1.0 + 0.15 * math.sin(match.count * math.pi * 2)
        t = self.f_big.render(str(n), True, (255, 80, 80))
        t = pygame.transform.smoothscale(t, (int(t.get_width() * 3.0 * pulse),
                                             int(t.get_height() * 3.0 * pulse)))
        surface.blit(t, (w // 2 - t.get_width() // 2, h // 2 - t.get_height() // 2))
        who = match.down_fighter
        if who is match.player:
            msg = "MASH  A / D  TO GET UP!"
            col = GOLD
            mt = self.f_mid.render(msg, True, col)
            surface.blit(mt, (w // 2 - mt.get_width() // 2, h // 2 + 110))
            # get-up meter
            _bar(surface, (w // 2 - 160, h // 2 + 150, 320, 16),
                 match.getup_progress, (110, 220, 130))

    # ------------------------------------------------------------------
    def draw_scorecard(self, surface, match):
        w, h = self.w, self.h
        panel = pygame.Surface((int(w * 0.62), int(h * 0.62)), pygame.SRCALPHA)
        panel.fill((10, 12, 22, 235))
        pygame.draw.rect(panel, GOLD, panel.get_rect(), width=2, border_radius=8)
        px = w // 2 - panel.get_width() // 2
        py = h // 2 - panel.get_height() // 2

        title = self.f_big.render(match.result_title, True, GOLD)
        panel.blit(title, (panel.get_width() // 2 - title.get_width() // 2, 26))
        sub = self.f_mid.render(match.result_sub, True, WHITE)
        panel.blit(sub, (panel.get_width() // 2 - sub.get_width() // 2, 84))

        p, o = match.player, match.opponent
        rows = [
            ("Punches landed", f"{p.stats_landed}", f"{o.stats_landed}"),
            ("Punches thrown", f"{p.stats_thrown}", f"{o.stats_thrown}"),
            ("Accuracy", f"{(p.stats_landed/p.stats_thrown*100 if p.stats_thrown else 0):.0f}%",
             f"{(o.stats_landed/o.stats_thrown*100 if o.stats_thrown else 0):.0f}%"),
            ("Blocks", f"{p.stats_blocked}", f"{o.stats_blocked}"),
            ("Parries", f"{p.parries_landed}", f"{o.parries_landed}"),
            ("Counters landed", f"{p.counters_landed}", f"{o.counters_landed}"),
            ("Knockdowns scored", f"{o.knockdowns}", f"{p.knockdowns}"),
            ("Damage dealt", f"{p.damage_dealt:.0f}", f"{o.damage_dealt:.0f}"),
        ]
        y = 140
        hp = self.f_small.render(p.stats.name, True, RED)
        ho = self.f_small.render(o.stats.name, True, BLUE)
        panel.blit(hp, (panel.get_width() - 260 - hp.get_width() // 2, y - 26))
        panel.blit(ho, (panel.get_width() - 90 - ho.get_width() // 2, y - 26))
        for label, a, b in rows:
            l = self.f_small.render(label, True, DIM)
            panel.blit(l, (40, y))
            va = self.f_small.render(a, True, WHITE)
            vb = self.f_small.render(b, True, WHITE)
            panel.blit(va, (panel.get_width() - 260 - va.get_width() // 2, y))
            panel.blit(vb, (panel.get_width() - 90 - vb.get_width() // 2, y))
            y += 30

        cards = self.f_small.render(
            f"Judges: {match.score_player} - {match.score_opponent}", True, GOLD)
        panel.blit(cards, (panel.get_width() // 2 - cards.get_width() // 2, y + 14))
        tip = self.f_small.render("ENTER - rematch      ESC - quit", True, WHITE)
        panel.blit(tip, (panel.get_width() // 2 - tip.get_width() // 2,
                         panel.get_height() - 44))
        surface.blit(panel, (px, py))
