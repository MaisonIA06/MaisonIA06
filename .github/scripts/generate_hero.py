#!/usr/bin/env python3
"""
Génère le « héros » SVG animé du profil (assets/hero-dark.svg / hero-light.svg).

Fenêtre terminal 1180×610 :
  • VISUAL.MAP (gauche) : logo MIA tramé en pixels (révélé ligne par ligne), puis
    dissous en particules qui se morphent en boucle entre plusieurs formes
    (logo → « IA » → réseau de neurones → « 06 » → logo…).
  • SYSTEM.INFO (droite) : fiche système « clé ····· valeur » révélée ligne par
    ligne, curseur clignotant.

Aucune dépendance externe côté rendu : SMIL pur (GitHub l'affiche via <img>).
Usage : python3 generate_hero.py [--logo assets/logo/mia-logo.png] [--out assets] [--particles 1400]
"""
from __future__ import annotations

import argparse
import html
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ──────────────────────────────── thèmes ────────────────────────────────
THEMES = {
    "dark": {
        "BG": "#070B16", "PANEL": "#0A101F", "PANEL2": "#0C1426", "BAR": "#0B1222",
        "CYAN": "#22D3EE", "VIOLET": "#A78BFA", "VIOLET2": "#7C3AED", "PINK": "#F472B6",
        "EMERALD": "#10B981", "TEXT": "#F8FAFC", "MUTED": "#94A3B8", "DIM": "#475569",
        "BARLINE": "rgba(255,255,255,0.10)", "PANEL_STROKE": "rgba(34,211,238,0.35)",
        "PILL_BG": "rgba(124,58,237,0.30)", "PILL_STROKE": "rgba(167,139,250,0.55)",
        "DOT": "#A78BFA", "DOT2": "#22D3EE", "DOT3": "#F472B6",
    },
    "light": {
        "BG": "#F1F5F9", "PANEL": "#FFFFFF", "PANEL2": "#F8FAFC", "BAR": "#E2E8F0",
        "CYAN": "#0891B2", "VIOLET": "#7C3AED", "VIOLET2": "#6D28D9", "PINK": "#DB2777",
        "EMERALD": "#059669", "TEXT": "#0F172A", "MUTED": "#475569", "DIM": "#94A3B8",
        "BARLINE": "rgba(0,0,0,0.08)", "PANEL_STROKE": "rgba(8,145,178,0.45)",
        "PILL_BG": "rgba(124,58,237,0.12)", "PILL_STROKE": "rgba(124,58,237,0.45)",
        "DOT": "#7C3AED", "DOT2": "#0891B2", "DOT3": "#DB2777",
    },
}

# ──────────────────────────────── géométrie ─────────────────────────────
W, H = 1180, 610
PX, PY, PW, PH = 36, 84, 400, 492          # panneau VISUAL.MAP
GRID_W, GRID_H = 160, 197                  # grille interne (1 cellule ≈ 2.45 px)
CELL = 2.45
INFO_X = 470                               # colonne SYSTEM.INFO
COLS = 86                                  # largeur en caractères des lignes clé····valeur
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
T_SWITCH = 3.2                             # trame → particules
HOLD, MORPH = 2.2, 1.1                     # durées par forme (s)
SEED = 6

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

# ──────────────────────────────── contenu ───────────────────────────────
TITLE_BAR = "maison-intelligence-artificielle.com — % ./profile.sh --live"
HANDLE = "MaisonIA06"
INFO_LINES = [
    ("Subject", "Maison de l'Intelligence Artificielle"),
    ("Role", "Lieu public dédié à l'IA — showroom, ateliers, événements"),
    ("Origin", "Sophia Antipolis · Biot · Alpes-Maritimes (06)"),
    ("Operator", "Département des Alpes-Maritimes"),
    ("Online.Since", "2020"),
    ("Status", "Sensibiliser + Fédérer + Valoriser + Inspirer"),
    ("Users.Reached", "+130 000 personnes · 1 000 m²"),
    ("Core.Lang", "Python, TypeScript"),
    ("Core.AI", "PyTorch, OpenCV, LLM / IA générative"),
    ("Core.Web", "Django, React, FastAPI"),
    ("Core.Infra", "Docker, Nginx, GitHub Actions"),
    ("Core.Robotics", "Reachy, drones Tello"),
    None,  # séparateur « Contact »
    ("Grid.Web", "maison-intelligence-artificielle.com"),
    ("Grid.Phone", "04 22 21 50 42"),
    ("Grid.LinkedIn", "maison-de-l-intelligence-artificielle"),
    ("Grid.GitHub", "@MaisonIA06"),
    ("Grid.Social", "@maison_ia06 · Instagram / TikTok / YouTube · @maison_ia (X)"),
]
FOOTER = "▸ Plus d'infos, stats & projets ci-dessous dans le README ↓"


def esc(s: str) -> str:
    return html.escape(str(s), quote=False)


# ──────────────────────────────── masques ───────────────────────────────
def _fit_into(img: Image.Image, gw: int, gh: int, margin: float = 0.08) -> np.ndarray:
    """Redimensionne la forme d'une image dans la grille (conserve le ratio, centre).

    Forme = canal alpha si l'image en a un (logo PNG), sinon luminance (dessins PIL en mode L).
    """
    alpha = img.convert("LA").split()[-1] if img.mode in ("LA", "RGBA", "PA") else img.convert("L")
    bbox = alpha.getbbox() or (0, 0, alpha.width, alpha.height)
    alpha = alpha.crop(bbox)
    avail_w, avail_h = gw * (1 - 2 * margin), gh * (1 - 2 * margin)
    scale = min(avail_w / alpha.width, avail_h / alpha.height)
    nw, nh = max(1, round(alpha.width * scale)), max(1, round(alpha.height * scale))
    alpha = alpha.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("L", (gw, gh), 0)
    canvas.paste(alpha, ((gw - nw) // 2, (gh - nh) // 2))
    return np.asarray(canvas, dtype=np.float32) / 255.0


def load_alpha(path, gw: int = GRID_W, gh: int = GRID_H) -> np.ndarray:
    return _fit_into(Image.open(path), gw, gh)


def load_mask(path, gw: int = GRID_W, gh: int = GRID_H) -> np.ndarray:
    return load_alpha(path, gw, gh) > 0.5


def _font(size: int):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def text_mask(text: str, gw: int = GRID_W, gh: int = GRID_H) -> np.ndarray:
    big = Image.new("L", (800, 800), 0)
    d = ImageDraw.Draw(big)
    d.text((400, 400), text, fill=255, font=_font(520), anchor="mm")
    return _fit_into(big, gw, gh, margin=0.10) > 0.5


def neural_mask(gw: int = GRID_W, gh: int = GRID_H) -> np.ndarray:
    """Réseau de neurones : 4 couches de nœuds reliés."""
    big = Image.new("L", (600, 700), 0)
    d = ImageDraw.Draw(big)
    layers = [3, 5, 5, 2]
    xs = [80, 227, 373, 520]
    pts = []
    for li, n in enumerate(layers):
        ys = [350 + (i - (n - 1) / 2) * 110 for i in range(n)]
        pts.append([(xs[li], y) for y in ys])
    for a, b in zip(pts, pts[1:]):
        for p in a:
            for q in b:
                d.line([p, q], fill=255, width=7)
    for layer in pts:
        for (x, y) in layer:
            d.ellipse((x - 30, y - 30, x + 30, y + 30), fill=255)
            d.ellipse((x - 16, y - 16, x + 16, y + 16), fill=0)
    return _fit_into(big, gw, gh, margin=0.08) > 0.5


def build_shapes(logo_path):
    """Formes successives du morphing : (nom, masque booléen)."""
    return [
        ("logo", load_mask(logo_path)),
        ("IA", text_mask("IA")),
        ("neural", neural_mask()),
        ("06", text_mask("06")),
    ]


# ──────────────────────────────── particules ────────────────────────────
def sample_points(mask: np.ndarray, n: int, seed: int = SEED) -> np.ndarray:
    """n points (x, y) tirés uniformément dans le masque (déterministe)."""
    rng = np.random.default_rng(seed)
    ys, xs = np.nonzero(mask)
    idx = rng.choice(len(xs), size=n, replace=len(xs) < n)
    pts = np.stack([xs[idx], ys[idx]], axis=1)
    # tri spatial (bandes horizontales) → trajectoires cohérentes entre formes
    order = np.lexsort((pts[:, 0], pts[:, 1] // 12))
    return pts[order]


def _timeline(n_shapes: int):
    """durée totale et keyTimes d'une boucle hold→morph pour n formes (retour à la 1re)."""
    total = n_shapes * (HOLD + MORPH)
    times = [0.0]
    t = 0.0
    for _ in range(n_shapes):
        t += HOLD; times.append(t / total)
        t += MORPH; times.append(t / total)
    times[-1] = 1.0
    return total, times


def particles_svg(shapes, n: int, th: dict, seed: int = SEED) -> str:
    sets = [sample_points(m, n, seed + i) for i, (_, m) in enumerate(shapes)]
    total, times = _timeline(len(shapes))
    kt = ";".join(f"{t:.3f}" for t in times)
    # Un seul <set> sur le groupe (et non par particule) + interpolation linéaire :
    # indispensable pour que le navigateur tienne la cadence avec ~1000 particules.
    out = [
        f'<defs><rect id="pA" width="0.95" height="0.75" fill="{th["DOT"]}"/>'
        f'<rect id="pB" width="0.95" height="0.75" fill="{th["DOT2"]}"/>'
        f'<rect id="pC" width="0.95" height="0.75" fill="{th["DOT3"]}"/></defs>',
        f'<g opacity="0" transform="translate({PX + 4},{PY + 4}) scale({CELL})">',
        f'<set attributeName="opacity" to="1" begin="{T_SWITCH}s"/>',
    ]
    for i in range(n):
        pos = [f"{s[i][0]} {s[i][1]}" for s in sets]
        vals = []
        for p in pos:
            vals += [p, p]               # maintien (hold) puis départ du morph
        vals.append(pos[0])              # retour à la première forme
        ref = "pA" if i % 10 < 7 else ("pB" if i % 10 < 9 else "pC")
        out.append(
            f'<use href="#{ref}"><animateTransform attributeName="transform" type="translate" '
            f'values="{";".join(vals)}" keyTimes="{kt}" '
            f'dur="{total:.1f}s" begin="{T_SWITCH}s" repeatCount="indefinite"/></use>'
        )
    out.append("</g>")
    return "".join(out)


# ──────────────────────────────── trame (halftone) ──────────────────────
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) / 16.0


def halftone(alpha: np.ndarray) -> np.ndarray:
    """Trame ordonnée (Bayer 4×4) sur alpha × dégradé diagonal → cellules allumées."""
    h, w = alpha.shape
    yy, xx = np.mgrid[0:h, 0:w]
    tone = alpha * (0.38 + 0.62 * (1 - (xx / w * 0.5 + yy / h * 0.5)))
    thr = np.tile(BAYER4, (math.ceil(h / 4), math.ceil(w / 4)))[:h, :w]
    return tone > thr


def _row_runs(row: np.ndarray):
    """Segments [start, end) de cellules allumées d'une ligne."""
    runs, start = [], None
    for x, v in enumerate(row):
        if v and start is None:
            start = x
        elif not v and start is not None:
            runs.append((start, x)); start = None
    if start is not None:
        runs.append((start, len(row)))
    return runs


def halftone_svg(alpha: np.ndarray, th: dict, band: int = 8) -> str:
    cells = halftone(alpha)
    out = [f'<g fill="{th["DOT"]}" shape-rendering="crispEdges" transform="translate({PX + 4},{PY + 4}) scale({CELL})">',
           f'<set attributeName="opacity" to="0" begin="{T_SWITCH}s"/>']
    h = cells.shape[0]
    for b, y0 in enumerate(range(0, h, band)):
        d = []
        for y in range(y0, min(h, y0 + band)):
            for s, e in _row_runs(cells[y]):
                d.append(f"M{s} {y}h{e - s}v1h{-(e - s)}z")
        if not d:
            continue
        begin = 0.2 + b * 0.07
        out.append(f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.7s" begin="{begin:.2f}s" '
                   f'fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".4 0 .2 1"/>'
                   f'<path d="{"".join(d)}"/></g>')
    out.append("</g>")
    return "".join(out)


# ──────────────────────────────── SYSTEM.INFO ───────────────────────────
def leader(key: str, value: str, cols: int = COLS) -> str:
    """'key ' + points + ' value' calé sur `cols` colonnes (monospace)."""
    dots = max(3, cols - len(key) - len(value) - 2)
    return f"{key} {'.' * dots} {value}"


def info_svg(th: dict) -> str:
    out = []
    a = out.append
    a(f'<text x="{INFO_X}" y="74" font-size="10" letter-spacing="3" fill="{th["DIM"]}">SYSTEM.INFO</text>')
    a(f'<line x1="{INFO_X}" y1="82" x2="{W - 30}" y2="82" stroke="url(#accent)" stroke-width="1.5" opacity="0.8"/>')
    # pastille identifiant
    pill_w = 9 * len(HANDLE) + 34
    a(f'<rect x="{INFO_X}" y="96" width="{pill_w}" height="24" rx="6" fill="{th["PILL_BG"]}" stroke="{th["PILL_STROKE"]}"/>')
    a(f'<circle cx="{INFO_X + 13}" cy="108" r="3.5" fill="{th["EMERALD"]}">'
      f'<animate attributeName="opacity" values="1;0.25;1" dur="1.8s" repeatCount="indefinite"/></circle>')
    a(f'<text x="{INFO_X + 24}" y="112.5" font-size="13" font-weight="700" fill="{th["TEXT"]}">{HANDLE}</text>')
    a(f'<text x="{INFO_X + pill_w + 12}" y="112.5" font-size="11" fill="{th["MUTED"]}">online · sophia-antipolis · 06</text>')

    y, i = 148, 0
    for item in INFO_LINES:
        begin = 0.5 + i * 0.12
        if item is None:
            a(f'<text x="{INFO_X}" y="{y}" font-size="12" fill="{th["DIM"]}" opacity="0">'
              f'<animate attributeName="opacity" values="0;1" dur="0.4s" begin="{begin:.2f}s" fill="freeze"/>'
              f'<tspan fill="{th["PINK"]}">- Contact </tspan>{"-" * (COLS - 10)}</text>')
        else:
            key, val = item
            line = leader(key, val)
            dots = line[len(key) + 1: len(line) - len(val) - 1]
            a(f'<text x="{INFO_X}" y="{y}" font-size="12" fill="{th["TEXT"]}" opacity="0">'
              f'<animate attributeName="opacity" values="0;1" dur="0.4s" begin="{begin:.2f}s" fill="freeze"/>'
              f'<animateTransform attributeName="transform" type="translate" values="-8 0;0 0" dur="0.4s" '
              f'begin="{begin:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".4 0 .2 1"/>'
              f'<tspan fill="{th["CYAN"]}">{esc(key)} </tspan>'
              f'<tspan fill="{th["DIM"]}">{dots}</tspan>'
              f'<tspan fill="{th["TEXT"]}"> {esc(val)}</tspan></text>')
        y += 22
        i += 1
    # curseur
    a(f'<text x="{INFO_X}" y="{y}" font-size="12" fill="{th["CYAN"]}" opacity="0">'
      f'<animate attributeName="opacity" values="0;1" dur="0.1s" begin="{0.5 + i * 0.12:.2f}s" fill="freeze"/>'
      f'<tspan fill="{th["EMERALD"]}">$</tspan> <tspan>█<animate attributeName="opacity" values="1;0;1" dur="1s" '
      f'repeatCount="indefinite"/></tspan></text>')
    return "".join(out)


# ──────────────────────────────── assemblage ────────────────────────────
def build_svg(logo_path, theme: str = "dark", n_particles: int = 1100) -> str:
    th = THEMES[theme]
    alpha = load_alpha(logo_path)
    shapes = build_shapes(logo_path)
    s = []
    a = s.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'font-family="{FONT}" role="img" aria-label="Maison de l\'IA — profile.sh --live">')
    a('<defs>'
      f'<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0" stop-color="{th["VIOLET2"]}"><animate attributeName="stop-color" values="{th["VIOLET2"]};{th["CYAN"]};{th["PINK"]};{th["VIOLET2"]}" dur="10s" repeatCount="indefinite"/></stop>'
      f'<stop offset="0.5" stop-color="{th["CYAN"]}"><animate attributeName="stop-color" values="{th["CYAN"]};{th["PINK"]};{th["VIOLET2"]};{th["CYAN"]}" dur="10s" repeatCount="indefinite"/></stop>'
      f'<stop offset="1" stop-color="{th["PINK"]}"><animate attributeName="stop-color" values="{th["PINK"]};{th["VIOLET2"]};{th["CYAN"]};{th["PINK"]}" dur="10s" repeatCount="indefinite"/></stop>'
      '</linearGradient>'
      f'<linearGradient id="panelGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{th["PANEL"]}"/><stop offset="1" stop-color="{th["PANEL2"]}"/></linearGradient>'
      '<filter id="glow3" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3"/></filter>'
      f'<pattern id="pgrid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="{th["CYAN"]}" stroke-opacity="0.07"/></pattern>'
      f'<clipPath id="winClip"><rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="18"/></clipPath>'
      f'<clipPath id="panelClip"><rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="10"/></clipPath>'
      '</defs>')
    # fenêtre
    a(f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="18" fill="{th["BG"]}"/>')
    a('<g clip-path="url(#winClip)">')
    a(f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" fill="url(#panelGrad)"/>')
    a(f'<rect x="2" y="2" width="{W - 4}" height="46" fill="{th["BAR"]}"/>')
    a(f'<line x1="2" y1="48" x2="{W - 2}" y2="48" stroke="{th["BARLINE"]}"/>')
    a('<circle cx="30" cy="25" r="5.5" fill="#ff5f56"/><circle cx="50" cy="25" r="5.5" fill="#ffbd2e"/><circle cx="70" cy="25" r="5.5" fill="#27c93f"/>')
    a(f'<text x="{W / 2}" y="29" text-anchor="middle" font-size="12" fill="{th["MUTED"]}">{esc(TITLE_BAR)}</text>')
    # panneau VISUAL.MAP
    a(f'<text x="{PX + 2}" y="74" font-size="10" letter-spacing="3" fill="{th["DIM"]}">VISUAL.MAP</text>')
    a(f'<rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="10" fill="none" stroke="{th["CYAN"]}" stroke-width="2" opacity="0.45" filter="url(#glow3)"/>')
    a(f'<rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="10" fill="{th["PANEL"]}" stroke="{th["PANEL_STROKE"]}"/>')
    a(f'<rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="10" fill="url(#pgrid)"/>')
    a('<g clip-path="url(#panelClip)">')
    a(halftone_svg(alpha, th))
    a(particles_svg(shapes, n_particles, th))
    # ligne de scan
    a(f'<rect x="{PX}" y="{PY}" width="{PW}" height="2" fill="{th["CYAN"]}" opacity="0.35">'
      f'<animateTransform attributeName="transform" type="translate" values="0 -4;0 {PH + 4}" dur="5s" repeatCount="indefinite"/></rect>')
    a('</g>')
    # coins HUD du panneau
    a(f'<g fill="none" stroke="{th["CYAN"]}" stroke-width="2" opacity="0.9">'
      f'<path d="M{PX - 6} {PY + 14}V{PY - 6}H{PX + 14}"/><path d="M{PX + PW - 14} {PY - 6}H{PX + PW + 6}V{PY + 14}"/>'
      f'<path d="M{PX - 6} {PY + PH - 14}V{PY + PH + 6}H{PX + 14}"/><path d="M{PX + PW - 14} {PY + PH + 6}H{PX + PW + 6}V{PY + PH - 14}"/></g>')
    # SYSTEM.INFO
    a(info_svg(th))
    # pied
    a(f'<text x="{W / 2}" y="{H - 12}" text-anchor="middle" font-size="10.5" fill="{th["DIM"]}">{esc(FOOTER)}</text>')
    a('</g>')
    a(f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="18" fill="none" stroke="url(#accent)" stroke-opacity="0.55"/>')
    a('</svg>')
    return "".join(s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logo", default="assets/logo/mia-logo.png")
    ap.add_argument("--out", default="assets")
    ap.add_argument("--particles", type=int, default=1100)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        svg = build_svg(args.logo, theme, args.particles)
        p = out / f"hero-{theme}.svg"
        p.write_text(svg, encoding="utf-8")
        print(f"écrit {p} ({len(svg) // 1024} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
