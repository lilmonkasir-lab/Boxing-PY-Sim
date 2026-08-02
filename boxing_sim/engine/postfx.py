"""Screen-space post-processing: bloom and vignette.

Both run on the low-resolution render buffer *before* it is scaled up to the
window, so their cost barely moves with window size.  Together they do most of
the work of making a flat-shaded scene look like a televised arena: bloom
blooms the overhead lamps and the bright canvas pool, and the vignette pulls
the eye off the corners and onto the fighters.
"""
from __future__ import annotations

import pygame


class PostFX:
    #: per-quality budget.  The vignette is nearly free (one multiply blit)
    #: and does most of the framing work, so it survives down to "medium";
    #: bloom costs a scale-up over the whole buffer and is dropped first.
    PRESETS = {
        "low":    dict(bloom=0.0,  vignette=0.0),
        "medium": dict(bloom=0.0,  vignette=0.55),
        "high":   dict(bloom=0.55, vignette=0.60),
    }

    def __init__(self, size, quality: str = "high"):
        self.enabled = True
        self.bloom_strength = 0.55
        self.bloom_threshold = 186
        self.vignette_strength = 0.60
        self._vignette = None
        self.size = size
        self.set_quality(quality)
        self.resize(size)

    # ------------------------------------------------------------------
    def set_quality(self, quality: str) -> None:
        preset = self.PRESETS.get(quality, self.PRESETS["high"])
        self.bloom_strength = preset["bloom"]
        self.vignette_strength = preset["vignette"]
        self.enabled = (self.bloom_strength > 0.0) or (self.vignette_strength > 0.0)
        if self._vignette is not None:
            self._vignette = self._make_vignette(self.size)

    # ------------------------------------------------------------------
    def resize(self, size):
        self.size = size
        w, h = size
        self._small = (max(1, w // 8), max(1, h // 8))
        self._buf_small = pygame.Surface(self._small).convert()
        self._vignette = self._make_vignette(size)

    def _make_vignette(self, size):
        """Radial darkening as an opaque BLEND_RGB_MULT mask.

        An SRCALPHA mask blitted over the frame measured 3.9 ms - more than the
        whole bloom pass - because pygame has to alpha-blend every pixel.  A
        multiply blend of an opaque surface is a much cheaper path, and the
        strength can be folded into the mask itself when it is built.
        """
        strength = self.vignette_strength
        sw, sh = 96, 54
        surf = pygame.Surface((sw, sh)).convert()
        cx, cy = (sw - 1) / 2.0, (sh - 1) / 2.0
        maxd = (cx * cx + cy * cy) ** 0.5
        for y in range(sh):
            row = []
            for x in range(sw):
                d = (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / maxd
                dark = max(0.0, min(1.0, (d - 0.42) / 0.58)) ** 1.7 * strength
                v = int(255 * (1.0 - dark))
                row.append(v)
            for x, v in enumerate(row):
                surf.set_at((x, y), (v, v, v))
        return pygame.transform.smoothscale(surf, size)

    # ------------------------------------------------------------------
    def apply(self, surface):
        if not self.enabled:
            return
        if surface.get_size() != self.size:
            self.resize(surface.get_size())

        if self.bloom_strength > 0.01:
            # Isolate highlights, blur by down/up scaling, add back.
            # Scratch surfaces are reused: allocating two per frame showed up
            # as the second-largest cost in the frame profile.
            thr = self.bloom_threshold
            pygame.transform.scale(surface, self._small, self._buf_small)
            self._buf_small.fill((thr, thr, thr), special_flags=pygame.BLEND_RGB_SUB)
            # one smoothscale back up doubles as the blur
            glow = pygame.transform.smoothscale(self._buf_small, self.size)
            glow.set_alpha(int(255 * self.bloom_strength))
            surface.blit(glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        if self.vignette_strength > 0.01 and self._vignette is not None:
            surface.blit(self._vignette, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
