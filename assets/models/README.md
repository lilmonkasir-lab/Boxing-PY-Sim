# Drop the Sketchfab ring here

The sim runs out of the box with a procedural ring, so this folder can stay empty.

To use the real model:

1. Download **Boxing Ring** by Kopag 3D (free, Standard licence):
   https://sketchfab.com/3d-models/boxing-ring-861f09ce71014e4baebeb79b2f99b1d2
   Choose the **OBJ** download (Sketchfab requires you to be signed in).
2. Unzip it into this folder, so you end up with something like:

       assets/models/boxing_ring/boxing_ring.obj
       assets/models/boxing_ring/boxing_ring.mtl
       assets/models/boxing_ring/textures/...

3. Run `python main.py`. It will print

       [arena] using downloaded model: assets/models/.../boxing_ring.obj

The loader recentres, rescales and decimates the mesh to ~5k triangles
automatically. Any other `.obj` works too - a filename containing "ring" wins
if several are present.

Model files are gitignored: please download your own copy rather than
committing Kopag 3D's assets to this repo.
