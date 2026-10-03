"""Math with Zirek · Whisper large-v3 (int8, CPU) as a second speech-to-text judge.
For every <dir>/NNN.mp3 listed in <dir>/istek.json: a plain transcript ("duz") and one with initial_prompt = the script line ("ipucu").
Usage: python yargic.py <dir> <lang> [--yalniz 010,025]"""
import json, sys
from pathlib import Path
from faster_whisper import WhisperModel
d = Path(sys.argv[1]); dil = sys.argv[2]
yalniz = set(sys.argv[sys.argv.index("--yalniz") + 1].split(",")) if "--yalniz" in sys.argv else None
ist = json.loads((d / "istek.json").read_text(encoding="utf-8"))
m = WhisperModel("large-v3", device="cpu", compute_type="int8")
def yaz(p, prompt=None):
    seg, _ = m.transcribe(str(p), language=dil, beam_size=5, temperature=0.0, condition_on_previous_text=False,
                          vad_filter=False, initial_prompt=prompt)
    return " ".join(s.text.strip() for s in seg).strip()
out = {}
for it in ist:
    if yalniz and it["ad"] not in yalniz: continue
    p = d / f"{it['ad']}.mp3"
    if not p.exists(): continue
    out[it["ad"]] = {"duz": yaz(p), "ipucu": yaz(p, it["metin"])}
    print(it["ad"], "|", out[it["ad"]]["duz"], flush=True)
(d / "whisper.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
