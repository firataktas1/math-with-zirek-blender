# Builds kurzgesagt/index.html from duz2d/index.html: same story driver (render), new look (defs, builders).
# Run: python yap.py
import re
src = open("../duz2d/index.html", encoding="utf-8").read()
b0 = src.index("        // ---------- builders")
b1 = src.index("        // ---------- per-frame")
builders = open("builders.js", encoding="utf-8").read()
out = src[:b0] + builders + src[b1:]

# page styles / overlays
a = out.index("    <style>")
b = out.index("    </style>") + len("    </style>")
out = out[:a] + """    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #1F1846; }
      #root { width: 100%; height: 100%; position: relative; overflow: hidden; background: #1F1846; }
      .kat { position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; overflow: visible; }
      #vinyet { position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; pointer-events: none; background: radial-gradient(ellipse 80% 75% at 50% 45%, rgba(0,0,0,0) 60%, rgba(20, 10, 50, 0.42) 100%); }
      #isik { position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; pointer-events: none; background: radial-gradient(ellipse 60% 55% at 12% 30%, rgba(255, 170, 110, 0.20) 0%, rgba(255, 170, 110, 0) 70%); }
    </style>""" + out[b:]
out = out.replace('      <div id="tane"></div>\n', '')

# defs
a = out.index("        <defs>")
b = out.index("        </defs>") + len("        </defs>")
out = out[:a] + open("defs.svg", encoding="utf-8").read().rstrip() + out[b:]
out = out.replace('<rect x="-100" y="-100" width="2120" height="1280" fill="url(#gok)" />', '<rect x="-100" y="-100" width="2120" height="1280" fill="url(#gok)" />')
open("index.html", "w", encoding="utf-8").write(out)
print("ok", len(out))
