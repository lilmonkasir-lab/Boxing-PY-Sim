# 3D models

## What ships here

| File | Contents |
| --- | --- |
| `boxing_ring.obj` / `.mtl` | The full ring: canvas, skirt, red trim, 4 corner posts with turnbuckle pads, 4 rope runs. 1,690 triangles, 11 m across, sits on `y=0`. |
| `boxer.obj` / `.mtl` | A fighter in guard stance. 1,116 triangles, 2.0 m tall. |

Plain Wavefront OBJ with per-material colours, so they open directly in
Blender, MeshLab, Windows 3D Viewer, macOS Preview or any other 3D tool.

Regenerate them from the sim's live geometry after changing anything:

    python3 tools/export_models.py

### Why the game does not load these

They are exported *from* the procedural ring the game builds at runtime, and
are tagged as such in their header comment. Loading one back would replace the
live ring with a frozen copy of itself and disable the rope and corner-post
occlusion culling (the code that hides whichever rope run and post sit between
the camera and the fighters). So the loader skips any file it generated.

They are here to be inspected, edited and reused - not to feed the renderer.

## Using the Sketchfab ring instead

A genuine third-party model *does* override the built-in ring.

1. Download **Boxing Ring** by Kopag 3D (free, Standard licence):
   https://sketchfab.com/3d-models/boxing-ring-861f09ce71014e4baebeb79b2f99b1d2
   Choose the **OBJ** download (Sketchfab requires you to be signed in).
2. Unzip it into this folder, e.g.

       assets/models/kopag_boxing_ring/boxing_ring.obj
       assets/models/kopag_boxing_ring/boxing_ring.mtl
       assets/models/kopag_boxing_ring/textures/...

3. Run `python3 play.py`. It will print

       [arena] using downloaded model: assets/models/.../boxing_ring.obj

The loader recentres it, scales it onto the ring footprint, resolves colours
from the `.mtl` (or the average colour of each diffuse texture), and decimates
it to ~5,000 triangles - the original is 161k, which no pure-python rasteriser
will render at speed. Any `.obj` works; a filename containing "ring" wins if
several are present.

Downloaded files land in their own subfolder and are gitignored: please fetch
your own copy rather than committing Kopag 3D's assets to this repo.
