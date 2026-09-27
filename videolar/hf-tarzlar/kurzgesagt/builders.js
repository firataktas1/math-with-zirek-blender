        // ---------- builders (flat geometric: no outlines, gradients, rim light, soft glow)
        const RIM = "#FFC48E";
        function circles(list, fill, dx, dy, extraR) { return list.map(([x, y, r]) => `<circle cx="${f1(x + dx)}" cy="${f1(y + dy)}" r="${f1(r + extraR)}" fill="${fill}"/>`).join(""); }
        function pill(x, y, w, h, fill, rot) { return `<rect x="${f1(x - w / 2)}" y="${f1(y - h / 2)}" width="${f1(w)}" height="${f1(h)}" rx="${f1(h / 2)}" fill="${fill}" transform="rotate(${f1(rot)} ${f1(x)} ${f1(y)})"/>`; }
        function wall(x0, x1, arc, seed) {
          const r = Z.rng(seed); const H = Z.PEN.h;
          let top = "", bot = "";
          for (let x = x0; x <= x1 + 0.1; x += 4) top += `${f1(x)},${f1(arc(x) - H + 4)} `;
          for (let x = x1; x >= x0 - 0.1; x -= 4) bot += `${f1(x)},${f1(arc(x) + 2)} `;
          let s = `<polygon points="${top}${bot}" fill="#3F4680"/>`;
          const pts = []; let L = 0;
          for (let x = x0; x <= x1 + 0.01; x += 1) { const y = arc(x); if (pts.length) L += Math.hypot(1, y - pts[pts.length - 1][1]); pts.push([x, y, L]); }
          const at = (l) => { let lo = 0, hi = pts.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (pts[m][2] < l) lo = m; else hi = m; } const p = pts[lo], q = pts[hi]; return [p[0], p[1], Math.atan2(q[1] - p[1], q[0] - p[0] || 1e-3) * 180 / Math.PI]; };
          const course = (yOff, hh, fills, cap) => {
            let l = cap ? 2 : r() * 14;
            while (l < L - 6) {
              const w = (cap ? 32 : 26) + r() * 14; const lm = Math.min(l + w / 2, L - 8);
              const [x, y, ang] = at(lm); const rot = Math.max(-38, Math.min(38, ang)) * 0.8 + (r() - 0.5) * 5;
              const wf = Math.max(12, w * (0.55 + 0.45 * Math.abs(Math.cos(ang * Math.PI / 180)))) - 4;
              const f = fills[Math.floor(r() * fills.length)];
              s += pill(x, y + yOff, wf, hh, f, rot);
              if (cap) s += pill(x - 2, y + yOff - 3, wf - 8, 3.2, RIM, rot);
              l += w;
            }
          };
          for (let c = 0; c < 3; c++) course(-8 - c * 14, 12.5, ["url(#tas)", "url(#tas2)"], false);
          course(-H + 5, 11, ["url(#tasUst)"], true);
          return s;
        }
        function post(x, yb, h, seed) {
          const r = Z.rng(seed);
          let s = `<ellipse cx="${x + 44}" cy="${yb + 2}" rx="66" ry="10" fill="url(#golge)"/>`;
          s += `<rect x="${x - 26}" y="${yb - h}" width="52" height="${h}" rx="10" fill="#3F4680"/>`;
          let y = yb - 10;
          while (y > yb - h + 10) { const w = 50 + r() * 8, hh = 16 + r() * 3; s += pill(x + (r() - 0.5) * 4, y, w, hh, r() < 0.5 ? "url(#tas)" : "url(#tas2)", (r() - 0.5) * 5); y -= hh + 1.5; }
          s += pill(x, y + 4, 58, 14, "url(#tasUst)", 0) + pill(x - 3, y + 0.5, 44, 3.4, RIM, 0);
          s += `<rect x="${x - 25}" y="${y + 6}" width="4" height="${yb - y - 12}" rx="2" fill="${RIM}" opacity="0.55"/>`;
          return s;
        }
        function pebbleSVG(id, k) {
          const rx = Z.PEB.rx, ry = Z.PEB.ry;
          return `<g id="${id}"><g class="pk">
            <ellipse rx="${rx}" ry="${ry}" fill="url(#cakil)"/>
            <path d="M${-rx} 0 A ${rx} ${ry} 0 0 1 ${-rx * 0.2} ${-ry * 0.98}" stroke="#FFF1C4" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.9"/>
            <ellipse cx="4" cy="${ry * 0.55}" rx="${rx * 0.7}" ry="${ry * 0.3}" fill="#B8551F" opacity="0.35"/></g></g>`;
        }
        // rounded geometric sheep: feet at origin, facing right
        const WOOL = [[-34, -60, 25], [-12, -74, 27], [16, -72, 26], [36, -58, 22], [-16, -48, 26], [14, -46, 26], [-40, -44, 18]];
        function sheepSVG(i) {
          const leg = (cls, x, col) => `<g class="${cls}"><rect x="${x - 5}" y="-40" width="10" height="38" rx="5" fill="${col}"/></g>`;
          return `<g id="sh${i}"><g class="bob">
            ${leg("l0", -30, "#1E1A40")}${leg("l1", 30, "#1E1A40")}
            <g class="kuyruk"><circle cx="-58" cy="-60" r="11" fill="${RIM}"/><circle cx="-56" cy="-58" r="11" fill="#E4DEF6"/></g>
            ${leg("l2", -22, "#2B2552")}${leg("l3", 38, "#2B2552")}
            ${circles(WOOL, RIM, 0, 0, 0)}
            ${circles(WOOL, "url(#yun)", 3, 2.5, 0)}
            <circle cx="-2" cy="-58" r="3" fill="#FFFFFF" opacity="0"/>
            <g class="bas">
              <g class="kulak"><ellipse cx="46" cy="-70" rx="14" ry="6" fill="#1E1A40" transform="rotate(30 46 -70)"/></g>
              <rect x="42" y="-88" width="42" height="36" rx="16" fill="#2B2552" transform="rotate(18 63 -70)"/>
              <path d="M46 -80 A 17 17 0 0 1 64 -89" stroke="${RIM}" stroke-width="3.5" fill="none" stroke-linecap="round" opacity="0.9"/>
              <circle cx="69" cy="-74" r="5.8" fill="#FFFFFF"/><circle cx="70.8" cy="-73.5" r="3" fill="#15122E"/>
              <circle cx="48" cy="-88" r="12" fill="${RIM}"/><circle cx="50" cy="-86" r="12" fill="#F4F0FF"/>
            </g>
          </g></g>`;
        }

        // ---------- sky (L0)
        let s0 = "";
        { const r = Z.rng(5); for (let k = 0; k < 22; k++) { const x = r() * 1920, y = r() * 200, rr = 0.8 + r() * 1.8; s0 += `<circle class="yildiz" data-p="${f1(r() * 6.28)}" cx="${f1(x)}" cy="${f1(y)}" r="${f1(rr)}" fill="#FFF3E0" opacity="0.7"/>`; } }
        s0 += `<circle cx="300" cy="330" r="340" fill="url(#gunesHale)" opacity="0.9"/><circle cx="300" cy="330" r="70" fill="#FFE7A8"/><circle cx="300" cy="330" r="56" fill="#FFF6D6"/>`;
        const cloud = (x, y, sc) => `<g class="bulut" data-x="${x}" data-sc="${sc}" transform="translate(${x} ${y}) scale(${sc})">${pill(0, 0, 300, 26, "#F08A86", 0)}${pill(60, -18, 160, 22, "#F7A08E", 0)}${pill(-2, -9, 280, 5, "#FFC7A0", 0)}</g>`;
        s0 += cloud(760, 170, 1.0) + cloud(1450, 110, 0.8) + cloud(1780, 250, 0.6);
        $("#L0").innerHTML = s0;
        // ---------- far layers (L1)
        let s1 = `<path d="M-400 440 L -60 300 L 180 390 L 420 260 L 700 380 L 940 300 L 1200 390 L 1460 280 L 1760 370 L 2000 300 L 2400 400 L2400 1400 L-400 1400 Z" fill="url(#dag1)" stroke-linejoin="round"/>`;
        s1 += `<path d="M-400 440 L -60 300 L 180 390 M 420 260 L 700 380 M 1460 280 L 1760 370" stroke="${RIM}" stroke-width="3" fill="none" opacity="0.35"/>`;
        s1 += `<path d="M-400 450 C 0 380, 380 370, 720 402 C 1000 430, 1260 360, 1560 350 C 1800 344, 2050 380, 2400 400 L2400 1400 L-400 1400 Z" fill="url(#dag2)"/>`;
        s1 += `<g transform="translate(540 418)"><rect x="-6" y="-58" width="12" height="60" rx="5" fill="#2B2552"/><circle cx="0" cy="-92" r="44" fill="${RIM}"/><circle cx="4" cy="-89" r="44" fill="url(#agac)"/><ellipse cx="44" cy="2" rx="60" ry="7" fill="url(#golge)"/></g>`;
        $("#L1").innerHTML = s1;
        // ---------- mid (L2)
        $("#L2").innerHTML = `<path d="M-400 478 C 200 440, 700 448, 1100 438 C 1500 428, 1900 448, 2400 460 L2400 1400 L-400 1400 Z" fill="url(#tepe)"/><path d="M-400 478 C 200 440, 700 448, 1100 438 C 1500 428, 1900 448, 2400 460" stroke="${RIM}" stroke-width="3" fill="none" opacity="0.4"/>`;
        // ---------- stage (L3)
        const P = Z.PEN;
        let g = `<path d="M-500 500 C 0 480, 600 470, 1100 470 C 1600 468, 2000 478, 2500 490 L2500 1700 L-500 1700 Z" fill="url(#zemin)"/>`;
        g += `<path d="M-500 500 C 0 480, 600 470, 1100 470 C 1600 468, 2000 478, 2500 490" stroke="#8FE0B0" stroke-width="3" fill="none" opacity="0.35"/>`;
        g += `<path d="M-300 720 C 200 700, 500 690, 720 680 C 820 674, 880 652, ${Z.GATE.x} ${Z.GATE.y - 8} L ${Z.GATE.x + 20} ${Z.GATE.y + 8} C 900 690, 820 706, 720 714 C 500 736, 200 760, -300 800 Z" fill="#56B792" opacity="0.55"/>`;
        const blade = (x, y, s) => `<path d="M${x - 7 * s} ${y} L${x - 4 * s} ${y - 16 * s} L${x - 1 * s} ${y} Z M${x} ${y} L${x + 3 * s} ${y - 22 * s} L${x + 6 * s} ${y} Z M${x + 6 * s} ${y} L${x + 11 * s} ${y - 14 * s} L${x + 12 * s} ${y} Z" fill="#23705F"/>`;
        [[120, 640, 1], [300, 860, 1.2], [520, 940, 1.3], [180, 990, 1.4], [640, 612, 0.9], [760, 860, 1.1], [1840, 560, 0.8], [1380, 700, 0.9], [60, 820, 1.2], [1720, 690, 0.9]].forEach(([x, y, s]) => (g += blade(x, y, s)));
        g += `<ellipse cx="${P.cx}" cy="${P.cy}" rx="${P.rx}" ry="${P.ry}" fill="url(#agilZemin)"/>`;
        g += wall(P.cx - P.rx + 2, P.cx + P.rx - 2, Z.backY, 1);
        g += `<g id="gShB"></g><g id="gSheepB"></g>`;
        g += wall(P.cx - P.rx + 2, Z.POSTL.x - 16, Z.frontY, 2) + post(Z.POSTL.x, Z.POSTL.y, Z.POST_H, 3);
        g += `<g id="gShM"></g><g id="gSheepM"></g>`;
        g += wall(Z.POSTR.x + 16, P.cx + P.rx - 2, Z.frontY, 4);
        g += `<ellipse cx="${Z.MOUTH.x + 44}" cy="${Z.MOUTH.y + 100}" rx="100" ry="80" fill="url(#golge)"/>`;
        g += post(Z.POSTR.x, Z.POSTR.y, Z.POST_H, 5);
        const S = Z.STICK;
        g += `<path d="M${S.x0} ${S.y0} L${S.x1} ${S.y1}" stroke="#5A3A5E" stroke-width="10" stroke-linecap="round"/><path d="M${S.x0 + 4} ${S.y0 - 4} L${S.x1 - 4} ${S.y1 - 4}" stroke="${RIM}" stroke-width="2.5" stroke-linecap="round" opacity="0.8"/>`;
        const M = Z.MOUTH;
        const pouchBody = `M${M.x - 44} ${M.y + 28} C ${M.x - 104} ${M.y + 52}, ${M.x - 112} ${M.y + 138}, ${M.x - 52} ${M.y + 154} C ${M.x - 22} ${M.y + 161}, ${M.x + 22} ${M.y + 161}, ${M.x + 52} ${M.y + 154} C ${M.x + 112} ${M.y + 138}, ${M.x + 104} ${M.y + 52}, ${M.x + 44} ${M.y + 28} Z`;
        const frill = `M${M.x - 70} ${M.y} A 70 19 0 0 0 ${M.x + 70} ${M.y} C ${M.x + 66} ${M.y + 12}, ${M.x + 52} ${M.y + 22}, ${M.x + 44} ${M.y + 30} L ${M.x - 44} ${M.y + 30} C ${M.x - 52} ${M.y + 22}, ${M.x - 66} ${M.y + 12}, ${M.x - 70} ${M.y} Z`;
        let peb = ""; for (let k = 0; k < 9; k++) peb += pebbleSVG("pp" + k, k);
        g += `<g id="kese"><path d="M${Z.PEG.x} ${Z.PEG.y} L${M.x - 40} ${M.y - 6} M${Z.PEG.x} ${Z.PEG.y} L${M.x + 40} ${M.y - 6}" stroke="#FFC94A" stroke-width="4" stroke-linecap="round"/>
          <circle cx="${Z.PEG.x}" cy="${Z.PEG.y}" r="6" fill="#FFC94A"/>
          <g id="keseIc">
          <ellipse cx="${M.x}" cy="${M.y}" rx="70" ry="20" fill="#B8304A"/>
          <ellipse cx="${M.x}" cy="${M.y + 3}" rx="57" ry="13" fill="#3A1238"/>
          <g id="kesePeb">${peb}</g>
          <g id="keseGovde">
          <path d="${pouchBody}" fill="${RIM}" transform="translate(-4 -3)"/>
          <path d="${pouchBody}" fill="url(#kese)"/>
          <path d="M${M.x + 30} ${M.y + 44} C ${M.x + 94} ${M.y + 66}, ${M.x + 96} ${M.y + 132}, ${M.x + 46} ${M.y + 152} C ${M.x + 76} ${M.y + 116}, ${M.x + 70} ${M.y + 74}, ${M.x + 30} ${M.y + 44} Z" fill="#8E1F45" opacity="0.45"/>
          <ellipse cx="${M.x - 50}" cy="${M.y + 80}" rx="12" ry="26" fill="#FFB27E" opacity="0.45" transform="rotate(18 ${M.x - 50} ${M.y + 80})"/>
          <path d="${frill}" fill="url(#keseAgiz)"/>
          <path d="M${M.x - 70} ${M.y} A 70 19 0 0 0 ${M.x + 70} ${M.y}" stroke="#FFC7A0" stroke-width="3" fill="none"/>
          <path d="M${M.x - 50} ${M.y + 30} Q ${M.x} ${M.y + 40} ${M.x + 50} ${M.y + 30}" stroke="#FFC94A" stroke-width="7" fill="none" stroke-linecap="round"/>
          <path d="M${M.x - 8} ${M.y + 36} q -14 18 -8 36 M${M.x - 2} ${M.y + 36} q 10 18 22 26" stroke="#FFC94A" stroke-width="4.5" fill="none" stroke-linecap="round"/>
          <circle cx="${M.x - 5}" cy="${M.y + 36}" r="6.5" fill="#FFD76A"/>
          </g></g></g>`;
        const SL = Z.SLAB;
        g += `<ellipse cx="${SL.x + 50}" cy="${SL.y + 34}" rx="${SL.rx + 60}" ry="${SL.ry + 10}" fill="url(#golge)"/>`;
        g += `<path d="M${SL.x - SL.rx} ${SL.y} L ${SL.x - SL.rx} ${SL.y + 22} A ${SL.rx} ${SL.ry} 0 0 0 ${SL.x + SL.rx} ${SL.y + 22} L ${SL.x + SL.rx} ${SL.y} Z" fill="#555E96"/>`;
        g += `<ellipse cx="${SL.x}" cy="${SL.y}" rx="${SL.rx}" ry="${SL.ry}" fill="url(#yassi)"/>`;
        g += `<path d="M${SL.x - SL.rx + 4} ${SL.y - 6} A ${SL.rx} ${SL.ry} 0 0 1 ${SL.x - 40} ${SL.y - SL.ry + 1}" stroke="${RIM}" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.8"/>`;
        let row = ""; for (let k = 0; k < 8; k++) row += `<ellipse id="gl${k}" cx="0" cy="0" rx="26" ry="8" fill="url(#golge)" opacity="0"/>`;
        g += `<g id="gGolge">${row}</g><g id="gPuf"></g>`;
        let fl = ""; for (let k = 0; k < 8; k++) fl += pebbleSVG("fp" + k, k);
        g += `<g id="gUcan">${fl}</g>`;
        g += `<g id="parilti" opacity="0"><circle r="70" fill="url(#parlakHale)" opacity="0.85"/><path id="yildiz" d="M0 -34 Q 2.6 -2.6 24 0 Q 2.6 2.6 0 34 Q -2.6 2.6 -24 0 Q -2.6 -2.6 0 -34 Z" fill="#FFF5DA"/><circle r="4" fill="#FFFFFF"/></g>`;
        // fireflies (kept to the upper and left parts)
        { const r = Z.rng(9); let ff = ""; for (let k = 0; k < 12; k++) ff += `<circle class="ates" data-x="${f1(300 + r() * 1400)}" data-y="${f1(360 + r() * 260)}" data-p="${f1(r() * 6.28)}" r="${f1(9 + r() * 7)}" fill="url(#ates)"/>`; g += `<g id="gAtes">${ff}</g>`; }
        $("#L3").innerHTML = g;
        let sb = "", shd = "";
        for (let i = 0; i < 8; i++) { sb += sheepSVG(i); shd += `<ellipse id="sg${i}" cx="0" cy="0" rx="80" ry="10" fill="url(#golge)"/>`; }
        $("#gSheepM").innerHTML = sb; $("#gShM").innerHTML = shd;
        let pf = ""; for (let k = 0; k < 8; k++) for (let j = 0; j < 4; j++) pf += `<circle id="pf${k}_${j}" r="6" fill="#FFE3A8" opacity="0"/>`;
        $("#gPuf").innerHTML = pf;
        const STARS = [...document.querySelectorAll(".yildiz")], ATES = [...document.querySelectorAll(".ates")];
        function extra(t) {
          STARS.forEach((e) => e.setAttribute("opacity", (0.45 + 0.4 * Math.sin(t * 2.2 + +e.dataset.p)).toFixed(3)));
          ATES.forEach((e, k) => {
            const p = +e.dataset.p;
            e.setAttribute("cx", f1(+e.dataset.x + Math.sin(t * 0.6 + p) * 30 + t * 4));
            e.setAttribute("cy", f1(+e.dataset.y + Math.sin(t * 0.9 + p * 2) * 16));
            e.setAttribute("opacity", (0.35 + 0.35 * Math.sin(t * 1.6 + p * 3)).toFixed(3));
          });
        }

