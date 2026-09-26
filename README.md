# Math with Zirek · Blender scenes

Procedural Blender scene scripts for the Math with Zirek channel, rendered with GitHub Actions. Assets used are CC0 (Poly Haven) and listed next to each scene.

## Scenes
- `blender-deneme/sahne.py`: clay version (Blender 4.5), workflow `blender.yml`.
- `blender-deneme/gercekci/sahne.py`: photoreal version (Blender 5.2). CC0 assets from Poly Haven are downloaded at run time by `indir.py`; the list is in `KAYNAKLAR.txt`.
- `blender-deneme/kagit/sahne.py`: 3D paper cut-out version (Blender 5.2), fully procedural.
- Workflow `sahne.yml`: preview frames, full 300-frame render in 20 parallel jobs, patch a frame range.
