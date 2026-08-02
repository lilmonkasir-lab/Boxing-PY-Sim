"""Boxing PY Sim - application shell, camera direction and the main loop."""
from __future__ import annotations

import argparse
import math
import os
import sys

import numpy as np
import pygame

from .engine import math3d as m3
from .engine.camera import Camera
from .engine.postfx import PostFX
from .engine.renderer import Renderer
from .game.arena import RING_HALF, build_arena
from .game.audio import Audio
from .game.combat import distance_between
from .game.effects import FloatingText, Particles
from .game.fighter import FighterStats
from .game.hud import HUD
from .game.match import Match

PUNCH_KEYS = {
    pygame.K_j: "jab",
    pygame.K_k: "cross",
    pygame.K_u: "lead_hook",
    pygame.K_i: "rear_hook",
    pygame.K_o: "uppercut",
    pygame.K_h: "body_jab",
    pygame.K_l: "body_hook",
}

CAMERA_MODES = ["broadcast", "close", "corner", "cinematic", "overhead"]


class Game:
    def __init__(self, width=1280, height=720, rounds=3, difficulty="Contender",
                 round_length=120.0, fullscreen=False, no_audio=False,
                 no_crowd=False, quality="high", seed=None):
        pygame.init()
        flags = pygame.DOUBLEBUF | pygame.RESIZABLE
        if fullscreen:
            flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption("Boxing PY Sim - pure-python 3D")
        self.clock = pygame.time.Clock()
        self.width, self.height = self.screen.get_size()

        self.quality = quality
        self.render_scale = {"low": 0.5, "medium": 0.7, "high": 1.0}.get(quality, 1.0)
        self._make_buffer()

        self.camera = Camera(self.buf.get_width(), self.buf.get_height(), 56.0)
        self.renderer = Renderer(self.buf, self.camera)
        self.postfx = PostFX(self.buf.get_size(), quality)
        self.hud = HUD(self.width, self.height)
        self.audio = Audio(enabled=not no_audio)
        self.particles = Particles()
        self.floaters = FloatingText()

        self.arena = build_arena(crowd=not no_crowd and quality != "low")
        if self.arena.external_path:
            print(f"[arena] using downloaded model: {self.arena.external_path}")
        else:
            print("[arena] using built-in procedural ring "
                  "(drop an .obj in assets/models/ to use the Sketchfab one)")

        self.rounds = rounds
        self.difficulty = difficulty
        self.round_length = round_length
        self.seed = seed
        self.match = self._new_match()

        self.cam_mode = 0
        self.cam_eye = self.camera.eye.copy()
        self.cam_tgt = self.camera.target.copy()
        self.cam_side = m3.vec3(0.0, 0.0, 1.0)
        self.free_cam = False
        self.free_yaw = 0.0
        self.free_pitch = -0.2
        self.free_dist = 11.0
        self.paused = False
        self.show_debug = False
        self.mash_edge = False
        self._mash_prev = False
        self._parry_prev = False
        self._stance_edge = False
        self.running = True
        self.time = 0.0
        self.hitstop = 0.0

        self.audio.start_crowd()

    # ------------------------------------------------------------------
    def _make_buffer(self):
        bw = max(320, int(self.width * self.render_scale))
        bh = max(180, int(self.height * self.render_scale))
        self.buf = pygame.Surface((bw, bh)).convert()

    def _new_match(self):
        p = FighterStats(name="You", power=1.0, speed=1.05, chin=1.0,
                         trunks=(198, 38, 50), glove=(212, 40, 48),
                         skin=(212, 168, 132))
        opp_pool = {
            "Amateur": FighterStats(name="Rookie Reyes", power=0.85, speed=0.95, chin=0.9,
                                    trunks=(46, 82, 186), glove=(52, 96, 206),
                                    skin=(150, 104, 74)),
            "Contender": FighterStats(name="Dmitri Volkov", power=1.05, speed=1.0, chin=1.05,
                                      trunks=(46, 82, 186), glove=(52, 96, 206),
                                      skin=(224, 186, 156)),
            "Champion": FighterStats(name="Marcus 'Hammer' King", power=1.22, speed=1.1,
                                     chin=1.2, trunks=(30, 30, 40), glove=(220, 190, 70),
                                     skin=(112, 76, 54)),
            "Legend": FighterStats(name="El Fantasma", power=1.35, speed=1.22, chin=1.3,
                                   trunks=(14, 14, 20), glove=(228, 228, 232),
                                   skin=(168, 122, 88)),
        }
        o = opp_pool.get(self.difficulty, opp_pool["Contender"])
        return Match(self.arena, p, o, rounds=self.rounds,
                     difficulty=self.difficulty, round_length=self.round_length,
                     seed=self.seed)

    # ------------------------------------------------------------------
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.VIDEORESIZE:
                self.width, self.height = e.w, e.h
                self.screen = pygame.display.set_mode((e.w, e.h),
                                                      pygame.DOUBLEBUF | pygame.RESIZABLE)
                self._make_buffer()
                self.camera.resize(self.buf.get_width(), self.buf.get_height())
                self.renderer.resize(self.buf)
                self.postfx.resize(self.buf.get_size())
                self.hud.resize(e.w, e.h)
            elif e.type == pygame.KEYDOWN:
                self._keydown(e)
            elif e.type == pygame.MOUSEWHEEL and self.free_cam:
                self.free_dist = m3.clamp(self.free_dist - e.y * 0.8, 3.0, 30.0)

    def _keydown(self, e):
        k = e.key
        if k == pygame.K_ESCAPE:
            self.running = False
        elif k == pygame.K_q:
            self._stance_edge = True
        elif k == pygame.K_p:
            self.paused = not self.paused
        elif k == pygame.K_c:
            self.cam_mode = (self.cam_mode + 1) % len(CAMERA_MODES)
            self.hud.add_toast(f"camera: {CAMERA_MODES[self.cam_mode]}", life=1.2)
        elif k == pygame.K_v:
            self.free_cam = not self.free_cam
            self.hud.add_toast(f"free cam {'on' if self.free_cam else 'off'}", life=1.2)
        elif k == pygame.K_m:
            on = self.audio.toggle()
            self.hud.add_toast(f"sound {'on' if on else 'off'}", life=1.2)
        elif k == pygame.K_F1:
            self.show_debug = not self.show_debug
        elif k == pygame.K_F2:
            order = ["low", "medium", "high"]
            self.quality = order[(order.index(self.quality) + 1) % 3]
            self.render_scale = {"low": 0.5, "medium": 0.7, "high": 1.0}[self.quality]
            self._make_buffer()
            self.camera.resize(self.buf.get_width(), self.buf.get_height())
            self.renderer.resize(self.buf)
            self.postfx.set_quality(self.quality)
            self.postfx.resize(self.buf.get_size())
            self.hud.add_toast(f"quality: {self.quality}", life=1.2)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.match.state == "over":
            self.match = self._new_match()
            self.hud.say("NEW BOUT", "seconds out")

    # ------------------------------------------------------------------
    def gather_input(self):
        keys = pygame.key.get_pressed()
        mx = (1.0 if keys[pygame.K_d] else 0.0) - (1.0 if keys[pygame.K_a] else 0.0)
        mz = (1.0 if keys[pygame.K_w] else 0.0) - (1.0 if keys[pygame.K_s] else 0.0)
        block = keys[pygame.K_SPACE]
        duck = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        # parry is an edge-triggered tap, not a hold - that is the whole point
        parry_key = keys[pygame.K_f]
        parry = parry_key and not self._parry_prev
        self._parry_prev = parry_key
        nudge = 0.0
        if keys[pygame.K_z]:
            nudge = -1.6 * (1 / 60.0)
        elif keys[pygame.K_x]:
            nudge = 1.6 * (1 / 60.0)
        punches = []
        for key, name in PUNCH_KEYS.items():
            if keys[key]:
                punches.append(name)
                break
        # get-up mashing: alternate A/D
        mash = False
        cur = bool(keys[pygame.K_a]) != bool(keys[pygame.K_d])
        if cur and not self._mash_prev:
            mash = True
        self._mash_prev = cur
        stance_toggle = self._stance_edge
        self._stance_edge = False
        return dict(move=(mx, mz), block=block, duck=duck, punches=punches,
                    mash=mash, parry=parry, stance_toggle=stance_toggle,
                    stance_nudge=nudge)

    # ------------------------------------------------------------------
    def update_camera(self, dt):
        m = self.match
        p, o = m.player, m.opponent
        mid = (p.pos + o.pos) * 0.5 + m3.vec3(0, 1.30, 0)
        d = o.pos - p.pos
        d[1] = 0.0
        dist = max(0.8, m3.length(d))
        axis = m3.normalize(d) if dist > 1e-4 else m3.vec3(1, 0, 0)
        # Camera sits perpendicular to the fighting axis (classic broadcast
        # side-on).  The axis flips whenever the boxers swap sides, so the
        # perpendicular is latched against the previous frame's direction -
        # otherwise the camera lerps straight through the middle of the ring
        # every time they circle each other.
        side = m3.vec3(-axis[2], 0.0, axis[0])
        if float(side @ self.cam_side) < 0.0:
            side = -side
        self.cam_side = m3.normalize(m3.damp(self.cam_side, side, 2.5, dt))
        side = self.cam_side

        if self.free_cam:
            keys = pygame.key.get_pressed()
            self.free_yaw += ((keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * 1.6 * dt)
            self.free_pitch = m3.clamp(
                self.free_pitch + (keys[pygame.K_UP] - keys[pygame.K_DOWN]) * 1.0 * dt,
                -1.3, 1.3)
            eye = mid + m3.vec3(
                math.sin(self.free_yaw) * math.cos(self.free_pitch),
                math.sin(self.free_pitch) + 0.35,
                math.cos(self.free_yaw) * math.cos(self.free_pitch)) * self.free_dist
            tgt = mid
            fov = 56.0
        else:
            mode = CAMERA_MODES[self.cam_mode]
            if mode == "broadcast":
                # ringside height, pulled back enough to frame both boxers
                back = 6.6 + dist * 0.55
                eye = mid + side * back + m3.vec3(0, 1.25, 0)
                tgt = mid + m3.vec3(0, -0.32, 0)
                fov = 52.0
            elif mode == "close":
                back = 4.0 + dist * 0.40
                eye = mid + side * back + m3.vec3(0, 0.75, 0)
                tgt = mid + m3.vec3(0, -0.20, 0)
                fov = 56.0
            elif mode == "corner":
                c = m3.vec3(RING_HALF + 2.4, 4.0, RING_HALF + 2.4)
                eye = c
                tgt = mid
                fov = 48.0
            elif mode == "overhead":
                eye = mid + m3.vec3(0.4, 8.2, 0.4)
                tgt = mid + m3.vec3(0, -0.5, 0)
                fov = 62.0
            else:  # cinematic - slow orbit
                a = self.time * 0.16
                r = 8.4 + math.sin(self.time * 0.23) * 1.4
                eye = mid + m3.vec3(math.sin(a) * r, 1.7 + math.sin(a * 0.7) * 0.8,
                                    math.cos(a) * r)
                tgt = mid + m3.vec3(0, -0.1, 0)
                fov = 52.0

            # knockdown / finish drama: push in on the action
            if m.state == "knockdown" and m.down_fighter is not None:
                focus = m.down_fighter.pos + m3.vec3(0, 0.9, 0)
                k = m3.smoothstep(min(1.0, m.state_t / 0.8))
                tgt = m3.lerp(tgt, focus, k * 0.85)
                eye = m3.lerp(eye, focus + side * 3.4 + m3.vec3(0, 1.5, 0), k * 0.8)
                fov = m3.lerp(fov, 46.0, k)
            elif m.state == "over":
                k = m3.smoothstep(min(1.0, m.state_t / 1.2))
                fov = m3.lerp(fov, 44.0, k)

        rate = 6.5 if m.state == "fight" else 3.2
        self.cam_eye = m3.damp(self.cam_eye, eye, rate, dt)
        self.cam_tgt = m3.damp(self.cam_tgt, tgt, rate * 1.25, dt)
        # never let the camera drop below the apron or clip the canvas
        self.cam_eye[1] = max(self.cam_eye[1], 1.9)
        self.camera.eye = self.cam_eye
        self.camera.target = self.cam_tgt
        cur_fov = math.degrees(self.camera.fov)
        self.camera.set_fov(m3.damp(cur_fov, fov, 4.0, dt))
        self.camera.update(dt)

    # ------------------------------------------------------------------
    def process_events(self, events):
        for ev in events:
            kind = ev["kind"]
            if kind == "hit":
                pt = ev["point"]
                big = ev["critical"] or ev["damage"] > 12.0
                self.particles.burst_impact(pt, big)
                d = ev["defender"]
                self.particles.burst_sweat(d.head_pos(), m3.normalize(
                    d.pos - ev["attacker"].pos) + m3.vec3(0, 0.6, 0))
                self.camera.add_shake(0.28 if big else 0.14)
                self.hitstop = 0.075 if big else 0.035
                self.audio.play("hit_heavy" if big else "hit_light",
                                0.6 + 0.4 * min(1.0, ev["damage"] / 18.0))
                col = (255, 215, 110) if big else (255, 255, 255)
                label = f"{int(ev['damage'])}"
                if ev.get("counter"):
                    col = (255, 140, 210)
                    label = "COUNTER " + label
                elif ev["critical"]:
                    label += "!"
                self.floaters.add(pt + m3.vec3(0, 0.25, 0), label, col,
                                  size=1.3 if big else 1.0)
                if big:
                    self.audio.play("roar", 0.35)
            elif kind == "block":
                self.particles.burst_block(ev["point"])
                self.audio.play("block", 0.5)
                self.camera.add_shake(0.05)
                self.floaters.add(ev["point"], "BLOCK", (150, 200, 255), size=0.75, life=0.55)
            elif kind == "parry":
                pt = ev["point"]
                self.particles.spawn(pt, 14, 4.6, (190, 226, 255), 5.0, 0.34, 5.0)
                self.audio.play("block", 0.85)
                self.camera.add_shake(0.14)
                self.hitstop = 0.06
                self.floaters.add(pt + m3.vec3(0, 0.25, 0), "PARRY!",
                                  (150, 220, 255), size=1.25, life=0.85)
                self.hud.add_toast("Parry - opening!", (150, 220, 255), 1.2)
            elif kind == "zone":
                f = ev["fighter"]
                self.hud.say("IN THE ZONE", f.stats.name, 1.4)
                self.audio.play("roar", 0.8)
            elif kind == "cut":
                f = ev["fighter"]
                msg = "You are cut!" if f.is_player else f"{f.stats.name} is cut!"
                self.hud.add_toast(msg, (230, 70, 70), 2.2)
            elif kind == "swelling":
                f = ev["fighter"]
                msg = ("Your eye is closing" if f.is_player
                       else f"{f.stats.name}'s eye is closing")
                self.hud.add_toast(msg, (230, 150, 70), 2.2)
            elif kind == "stance":
                self.hud.add_toast(ev["text"], (200, 210, 240), 1.2)
            elif kind == "slip":
                self.floaters.add(ev["point"] + m3.vec3(0, 0.3, 0), "SLIP",
                                  (170, 255, 190), size=0.8, life=0.6)
            elif kind == "whiff":
                self.audio.play("whiff", 0.35)
            elif kind == "knockdown":
                self.audio.play("thud", 0.9)
                self.audio.play("roar", 0.9)
                self.camera.add_shake(0.7)
                self.hud.say("DOWN!", ev["fighter"].stats.name, 1.8)
            elif kind == "getup":
                self.hud.add_toast(f"{ev['fighter'].stats.name} beats the count!",
                                   (255, 220, 120))
            elif kind == "bell":
                self.audio.play("bell", 0.8)
            elif kind == "announce":
                self.hud.say(ev["text"], ev.get("sub", ""), 2.2)
            elif kind == "finish":
                self.audio.play("roar", 1.0)

    # ------------------------------------------------------------------
    def update(self, dt):
        self.time += dt
        if self.paused:
            return
        if self.hitstop > 0.0:
            self.hitstop = max(0.0, self.hitstop - dt)
            dt *= 0.12
        if self.match.slow_mo > 0.0:
            dt *= 0.42

        pin = self.gather_input()
        self.match.update(dt, pin)
        self.process_events(self.match.drain_events())
        self.particles.update(dt)
        self.floaters.update(dt)
        self.hud.update(dt)
        self.update_camera(dt)

        # crowd reacts to the action
        m = self.match
        heat = 0.25
        if m.state == "fight":
            heat = 0.3 + 0.4 * (1.0 - min(1.0, distance_between(m.player, m.opponent) / 3.0))
            heat += 0.15 * min(1.0, m.player.combo / 4.0)
        elif m.state == "knockdown":
            heat = 0.85
        self.audio.crowd_level(0.18 + heat * 0.5)

    # ------------------------------------------------------------------
    def draw(self):
        buf = self.buf
        # sky / hall gradient
        buf.fill((16, 15, 26))
        top = pygame.Surface((1, 8))
        for i in range(8):
            c = int(10 + i * 3)
            top.set_at((0, i), (c, c, c + 8))
        buf.blit(pygame.transform.scale(top, (buf.get_width(), int(buf.get_height() * 0.55))),
                 (0, 0))

        r = self.renderer
        r.begin()
        m = self.match
        mid = (m.player.pos + m.opponent.pos) * 0.5 + m3.vec3(0, 1.1, 0)
        self.arena.update_occlusion(self.camera, mid)
        self.arena.submit(r, draw_crowd=self.arena.crowd is not None)
        m.player.submit(r)
        m.opponent.submit(r)
        self.arena.submit_ropes(r, self.camera, mid)
        r.render()
        self.particles.draw(r, buf)
        # bloom/vignette belong to the 3D image, so they run before the HUD
        self.postfx.apply(buf)
        self.floaters.draw(r, buf, self.hud.f_float)

        # blit the render buffer up to the window
        if buf.get_size() != (self.width, self.height):
            pygame.transform.scale(buf, (self.width, self.height), self.screen)
        else:
            self.screen.blit(buf, (0, 0))

        # ---- 2D overlays -------------------------------------------------
        p = m.player
        if p.hurt_flash > 0.02:
            s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            s.fill((190, 30, 30, int(70 * p.hurt_flash)))
            self.screen.blit(s, (0, 0))
        if p.health < 30 and m.state == "fight":
            pulse = 0.5 + 0.5 * math.sin(self.time * 5.0)
            s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.rect(s, (200, 30, 40, int(45 * pulse)), s.get_rect(), width=26)
            self.screen.blit(s, (0, 0))

        self.hud.draw(self.screen, m)
        if m.state == "knockdown":
            self.hud.draw_count(self.screen, m)
        elif m.state == "over" and m.state_t > 1.0:
            self.hud.draw_scorecard(self.screen, m)
        elif m.state == "rest":
            t = self.hud.f_mid.render(f"REST - next round in {int(m.round_time)+1}",
                                      True, (245, 200, 96))
            self.screen.blit(t, (self.width // 2 - t.get_width() // 2, self.height - 90))

        if self.paused:
            s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            s.fill((6, 6, 12, 170))
            self.screen.blit(s, (0, 0))
            t = self.hud.f_big.render("PAUSED", True, (245, 200, 96))
            self.screen.blit(t, (self.width // 2 - t.get_width() // 2, self.height // 2 - 30))

        if self.show_debug:
            lines = [
                f"fps {self.clock.get_fps():5.1f}   tris {self.renderer.tris_drawn}",
                f"quality {self.quality}  buf {self.buf.get_width()}x{self.buf.get_height()}",
                f"state {m.state}  t={m.state_t:.2f}  round {m.round_no}",
                f"dist {distance_between(m.player, m.opponent):.2f}  ai {m.ai.state}",
            ]
            for i, ln in enumerate(lines):
                s = self.hud.f_tiny.render(ln, True, (140, 255, 170))
                self.screen.blit(s, (12, 100 + i * 16))

        pygame.display.flip()

    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = min(0.05, self.clock.tick(60) / 1000.0)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Boxing PY Sim - a pure-python 3D boxing simulator")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--round-length", type=float, default=120.0,
                    help="round length in seconds")
    ap.add_argument("--difficulty", default="Contender",
                    choices=["Amateur", "Contender", "Champion", "Legend"])
    ap.add_argument("--quality", default="high", choices=["low", "medium", "high"])
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--no-crowd", action="store_true")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args(argv)

    game = Game(width=args.width, height=args.height, rounds=args.rounds,
                difficulty=args.difficulty, round_length=args.round_length,
                fullscreen=args.fullscreen, no_audio=args.no_audio,
                no_crowd=args.no_crowd, quality=args.quality, seed=args.seed)
    game.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
