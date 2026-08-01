# Boxing PY Sim

A 3D boxing simulator built **out of pygame** — no OpenGL, no game engine, no
binary assets. The 3D is a software rasteriser written from scratch with numpy,
so it runs anywhere pygame runs.

![gameplay](docs/screenshot.png)

```bash
pip install -r requirements.txt
python main.py
```

---

## Controls

| Key | Action |
| --- | --- |
| `W` `A` `S` `D` | Move / circle |
| `J` | Jab | 
| `K` | Cross |
| `U` / `I` | Lead hook / rear hook |
| `O` | Uppercut |
| `H` / `L` | Body jab / body hook |
| `SPACE` | Block (high guard) |
| `SHIFT` | Slip / duck under a head shot |
| `A`+`D` mash | Beat the count when you're dropped |
| `C` | Cycle camera (broadcast / close / corner / cinematic / overhead) |
| `V` | Free camera (arrows orbit, wheel zooms) |
| `P` · `M` · `F1` · `F2` | Pause · mute · debug overlay · quality |

```bash
python main.py --difficulty Champion --rounds 12 --round-length 180
python main.py --quality low --no-crowd     # slower machines
python main.py --help
```

Difficulties: `Amateur`, `Contender`, `Champion`, `Legend`.

---

## Using the Sketchfab ring model

The sim ships with a **procedural ring** modelled on
[Kopag 3D's "Boxing Ring"](https://sketchfab.com/3d-models/boxing-ring-861f09ce71014e4baebeb79b2f99b1d2)
— raised apron, padded skirt, four corner posts with turnbuckle wraps, four
rope runs. No download required.

To use the real model instead, Sketchfab requires a signed-in download, so it
can't be fetched automatically:

1. Open the [model page](https://sketchfab.com/3d-models/boxing-ring-861f09ce71014e4baebeb79b2f99b1d2)
   and **Download 3D Model → OBJ** (free, Standard licence — credit Kopag 3D).
2. Unzip it into `assets/models/`.
3. Run the game. It auto-detects the `.obj`, prints
   `[arena] using downloaded model: ...`, and swaps it in.

The loader (`boxing_sim/engine/objloader.py`) reads `.obj`/`.mtl`, resolves each
face's colour from its material's `Kd` (or the average colour of its diffuse
texture), recentres and rescales the model onto the ring footprint, and
**decimates it to ~5 000 triangles** by vertex clustering — the original is
161 k triangles, which no pure-python rasteriser will render at speed.

---

## How the 3D works

There is no GPU involved. `boxing_sim/engine/renderer.py` implements a
fixed-function pipeline where every per-triangle stage is a vectorised numpy
operation over the whole scene at once:

```
model → world → view → near-plane clip → perspective divide → backface cull
      → Lambert + rim + distance fog → layer/depth sort → pygame.draw.polygon
```

Three things make it fast enough to be playable at 1280×720:

**Screen-space clipping.** SDL rasterises a polygon's *entire* area, including
the part hanging off-screen. Measured: a small triangle costs 0.002 ms, one
100× the viewport costs **2.5 ms** — a 1000× cliff. Near-plane clipping alone
still leaves huge projected floor quads, so anything crossing the viewport
margin is Sutherland–Hodgman clipped first. This alone took the frame from
23.8 ms to 17.8 ms.

**Draw layers, not just depth.** A pure centroid depth sort breaks when objects
differ wildly in size: a 7 m floor tile's centroid can be nearer than a small
canvas tile visually on top of it, so the floor painted over the ring. The
scene is authored in bands — backdrop → ring → actors → ropes — sorted by layer
first and depth second, which eliminates that whole artefact class.

**Geometry authored for a painter's algorithm.** Large surfaces are built from
per-side panels and grid tiles rather than single boxes, so each centroid sits
where its geometry actually is.

Camera work borrows from TV boxing: the rope run and corner post between the
camera and the fighters are culled, so the action is never hidden behind a
white bar.

---

## The fighters

Each boxer is a real joint hierarchy (torso → chest → shoulders → elbows →
gloves, plus hips and legs), animated procedurally — punches, guard, slips,
stagger and knockdowns all fall out of joint angles rather than canned frames.

Two details matter a lot:

**Reach is measured, not guessed.** `PunchDef.reach` is what the AI trusts when
deciding whether to throw. `tools/calibrate_reach.py` binary-searches the *real*
hit detection against the *real* animated rig and prints the table to paste
into `fighter.py`. A test asserts the declared numbers stay within 6 cm of
reality, so the AI can never drift into punching at thin air.

**Punches aim themselves.** The shoulder sits ~0.3 m off the spine and the
stance is bladed, so hand-authored joint angles finish up to 0.47 m wide of the
target — straight punches sailed clean past the head. Instead of hand-tuning
every angle, `_aim_punching_hand()` measures where the glove actually landed
and rotates the shoulder by the leftover yaw error. Lateral error: 0.59 m → 0.10 m.

Sound is synthesised at startup with numpy (impacts, leather, the bell, crowd
swells), so there are no audio files either.

---

## Layout

```
boxing_sim/
  engine/     math3d · mesh · primitives · camera · renderer · objloader
  game/       arena · fighter · combat · ai · match · hud · effects · audio
  app.py      window, input, camera direction, main loop
tools/
  headless_check.py    scripted bot + screenshots, no display needed
  calibrate_reach.py   regenerate the punch reach table
tests/                 47 tests
```

## Development

```bash
python -m pytest tests -q                              # 47 tests
python tools/headless_check.py --seconds 20 --shots 4  # screenshots, headless
python tools/calibrate_reach.py                        # after rig changes
```

The tests lock down the bugs actually hit while building this: punches that
couldn't reach, AI ranges disagreeing with hit detection, oversized polygons
reaching SDL, layer-vs-depth sorting, and rounds being judged on cumulative
rather than per-round damage.

## Credits

Ring design referenced from **Boxing Ring** by
[Kopag 3D](https://sketchfab.com/kopag) (Sketchfab, Free Standard licence).
Code MIT licensed.
