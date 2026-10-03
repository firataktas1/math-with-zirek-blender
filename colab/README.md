# Free local video model test (Colab T4)

Open in Colab: https://colab.research.google.com/github/firataktas1/math-with-zirek-blender/blob/main/colab/zirek_video_testi.ipynb

The notebook animates a 5-second paper cut-out moment from Math with Zirek Video 1 (3:27, Zirek and the student at the gate) with open models on Colab's free T4 GPU. No paid API and no access token are used.

- **Models:** LTX-Video 0.9.8 2B distilled (`Lightricks/LTX-Video`, text encoder and scheduler from `Lightricks/LTX-Video-0.9.5`). If every LTX attempt fails, the notebook falls back to Wan 2.1 1.3B (`Wan-AI/Wan2.1-VACE-1.3B-diffusers`, `Wan-AI/Wan2.1-T2V-1.3B-Diffusers`).
- **Attempts:**
  - image-to-video from the first frame;
  - video-to-video, light (sigma 0.42);
  - video-to-video, strong (sigma 0.725).
- **Settings ladder:** each attempt steps down a resolution ladder when memory or time runs out: 1280x704, 960x544, 768x448, then LTX 0.9.5.
- **Files:**
  - `zirek_test.py`: the driver. It runs each attempt in its own process and writes `sonuc/rapor.json`. Run it with `ZIREK_SMOKE=1` for a CPU smoke test that uses tiny random models.
  - `defter_olustur.py`: generates `zirek_video_testi.ipynb`.
  - `girdi/`: the input clip, 121 frames at 1280x720 and 24 fps, plus its first frame.
