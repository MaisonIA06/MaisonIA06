#!/usr/bin/env python3
"""
Génère le « héros » SVG animé du profil (assets/hero-dark.svg / hero-light.svg),
aux couleurs de la charte graphique MIA (2026).

Fenêtre terminal 1180×610 :
  • VISUAL.MAP (gauche) : logo officiel tramé (pixels, couleurs fidèles : M + phrase
    en couleur principale, « IA » toujours terracotta) révélé par bandes, puis dissous
    en particules bicolores qui se morphent en boucle : logo → icônes des missions
    (Sensibiliser, Fédérer, Valoriser, Inspirer) → Robotique → « 06 » → logo…
    Fond : pattern I/A de la charte.
  • SYSTEM.INFO (droite) : fiche « clé ····· valeur » révélée ligne par ligne.

SMIL pur (GitHub l'affiche via <img>).
Usage : python3 generate_hero.py [--logo-dark …] [--logo-light …] [--icons assets/icons]
                                 [--font Pogonia-Black.otf] [--out assets] [--particles 1100]
"""
from __future__ import annotations

import argparse
import html
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ──────────────────────────── palette officielle (charte 2026) ────────────────────────────
DEEP_BLUE, BLEU_QUANTIQUE, BLEU_LUMEN = "#163458", "#98A8C6", "#C2D4EF"
ROUGE_LOVELACE, TERRA, AURIA = "#994845", "#AE6557", "#F2B2A5"
MATIERE_GRISE, DATA_BLOOM, NEURA_VERDE = "#C0C0BE", "#E5EAA8", "#F1F4D0"
WHITE = "#FFFFFF"
# teintes de profondeur du Deep Blue (fenêtre / panneaux), issues de la même dominante
DEEP_BLUE_2, DEEP_BLUE_3 = "#112B4B", "#0E2440"
CHARTE_COLORS = {DEEP_BLUE, BLEU_QUANTIQUE, BLEU_LUMEN, ROUGE_LOVELACE, TERRA, AURIA,
                 MATIERE_GRISE, DATA_BLOOM, NEURA_VERDE, WHITE, DEEP_BLUE_2, DEEP_BLUE_3}

THEMES = {
    "dark": {
        "BG": DEEP_BLUE, "PANEL": DEEP_BLUE_3, "PANEL2": DEEP_BLUE_2, "BAR": DEEP_BLUE_2,
        "TEXT": WHITE, "KEY": BLEU_LUMEN, "MUTED": BLEU_QUANTIQUE, "DIM": BLEU_QUANTIQUE,
        "ACCENT": TERRA, "ACCENT2": AURIA, "HIGHLIGHT": DATA_BLOOM, "FRAME": BLEU_QUANTIQUE,
        "DOT": WHITE, "DOT2": TERRA,
        "BARLINE": "rgba(194,212,239,0.12)", "PANEL_STROKE": "rgba(152,168,198,0.45)",
        "PILL_BG": "rgba(174,101,87,0.28)", "PILL_STROKE": "rgba(242,178,165,0.6)",
        "PATTERN": "rgba(194,212,239,0.16)",
    },
    "light": {
        "BG": WHITE, "PANEL": WHITE, "PANEL2": NEURA_VERDE, "BAR": BLEU_LUMEN,
        "TEXT": DEEP_BLUE, "KEY": ROUGE_LOVELACE, "MUTED": DEEP_BLUE, "DIM": BLEU_QUANTIQUE,
        "ACCENT": TERRA, "ACCENT2": ROUGE_LOVELACE, "HIGHLIGHT": ROUGE_LOVELACE, "FRAME": DEEP_BLUE,
        "DOT": DEEP_BLUE, "DOT2": TERRA,
        "BARLINE": "rgba(22,52,88,0.12)", "PANEL_STROKE": "rgba(22,52,88,0.35)",
        "PILL_BG": "rgba(194,212,239,0.45)", "PILL_STROKE": "rgba(22,52,88,0.45)",
        "PATTERN": "rgba(22,52,88,0.13)",
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
MISSION_ICONS = ["sensibiliser", "federer", "valoriser", "inspirer", "robotique"]

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
_FONT_PATH: str | None = None              # police explicite (--font), ex. Pogonia-Black.otf

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


# ──────────────────────────────── images → grille ───────────────────────
def _fit_image(img: Image.Image, gw: int, gh: int, margin: float) -> Image.Image:
    """Recadre sur la forme, redimensionne dans la grille (ratio conservé) et centre (RGBA)."""
    if img.mode in ("LA", "RGBA", "PA"):
        rgba = img.convert("RGBA")
    else:  # dessins PIL en mode L : la luminance sert de forme
        lum = img.convert("L")
        rgba = Image.merge("RGBA", (lum, lum, lum, lum))
    alpha = rgba.split()[-1]
    bbox = alpha.getbbox() or (0, 0, rgba.width, rgba.height)
    rgba = rgba.crop(bbox)
    avail_w, avail_h = gw * (1 - 2 * margin), gh * (1 - 2 * margin)
    scale = min(avail_w / rgba.width, avail_h / rgba.height)
    nw, nh = max(1, round(rgba.width * scale)), max(1, round(rgba.height * scale))
    rgba = rgba.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
    canvas.paste(rgba, ((gw - nw) // 2, (gh - nh) // 2))
    return canvas


def _alpha_of(canvas: Image.Image) -> np.ndarray:
    return np.asarray(canvas.split()[-1], dtype=np.float32) / 255.0


def load_logo(path, gw: int = GRID_W, gh: int = GRID_H):
    """(alpha, classe) : classe 0 = couleur principale (M, phrase), 1 = terracotta (IA)."""
    canvas = _fit_image(Image.open(path), gw, gh, margin=0.08)
    arr = np.asarray(canvas, dtype=np.int16)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    klass = ((r - b > 40) & (r > g)).astype(np.int8)      # rougeâtre → terracotta
    return _alpha_of(canvas), klass


def icon_mask(path, gw: int = GRID_W, gh: int = GRID_H) -> np.ndarray:
    return _alpha_of(_fit_image(Image.open(path), gw, gh, margin=0.12)) > 0.5


def _font(size: int):
    candidates = ([_FONT_PATH] if _FONT_PATH else []) + FONT_CANDIDATES
    for p in candidates:
        if p and Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def text_mask(text: str, gw: int = GRID_W, gh: int = GRID_H) -> np.ndarray:
    big = Image.new("L", (900, 900), 0)
    ImageDraw.Draw(big).text((450, 450), text, fill=255, font=_font(520), anchor="mm")
    return _alpha_of(_fit_image(big, gw, gh, margin=0.10)) > 0.5


def build_shapes(logo_path, icons_dir):
    """Formes successives du morphing : (nom, masque booléen)."""
    alpha, _ = load_logo(logo_path)
    shapes = [("logo", alpha > 0.5)]
    icons_dir = Path(icons_dir)
    for name in MISSION_ICONS:
        p = icons_dir / f"{name}.png"
        if p.exists():
            shapes.append((name, icon_mask(p)))
    shapes.append(("06", text_mask("06")))
    return shapes


# ──────────────────────────────── particules ────────────────────────────
def sample_points(mask: np.ndarray, n: int, seed: int = SEED) -> np.ndarray:
    """n points (x, y) tirés uniformément dans le masque (déterministe)."""
    rng = np.random.default_rng(seed)
    ys, xs = np.nonzero(mask)
    idx = rng.choice(len(xs), size=n, replace=len(xs) < n)
    pts = np.stack([xs[idx], ys[idx]], axis=1)
    order = np.lexsort((pts[:, 0], pts[:, 1] // 12))      # bandes horizontales → trajectoires cohérentes
    return pts[order]


def _timeline(n_shapes: int):
    """Durée totale et keyTimes d'une boucle hold→morph pour n formes (retour à la 1re)."""
    total = n_shapes * (HOLD + MORPH)
    times, t = [0.0], 0.0
    for _ in range(n_shapes):
        t += HOLD; times.append(t / total)
        t += MORPH; times.append(t / total)
    times[-1] = 1.0
    return total, times


def particles_svg(shapes, klass: np.ndarray, n: int, th: dict, seed: int = SEED) -> str:
    """Particules bicolores (couleur héritée du pixel du logo), un seul <set> sur le groupe
    et interpolation linéaire : indispensable pour que le navigateur tienne la cadence."""
    sets = [sample_points(m, n, seed + i) for i, (_, m) in enumerate(shapes)]
    total, times = _timeline(len(shapes))
    kt = ";".join(f"{t:.3f}" for t in times)
    out = [
        f'<defs><rect id="pA" width="0.95" height="0.75" fill="{th["DOT"]}"/>'
        f'<rect id="pB" width="0.95" height="0.75" fill="{th["DOT2"]}"/></defs>',
        f'<g opacity="0" transform="translate({PX + 4},{PY + 4}) scale({CELL})">',
        f'<set attributeName="opacity" to="1" begin="{T_SWITCH}s"/>',
    ]
    logo_pts = sets[0]
    for i in range(n):
        pos = [f"{s[i][0]} {s[i][1]}" for s in sets]
        vals = []
        for p in pos:
            vals += [p, p]               # maintien puis départ du morph
        vals.append(pos[0])              # retour à la première forme
        x0, y0 = logo_pts[i]
        ref = "pB" if klass[y0, x0] else "pA"
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
    tone = alpha * (0.58 + 0.42 * (1 - (xx / w * 0.5 + yy / h * 0.5)))
    thr = np.tile(BAYER4, (math.ceil(h / 4), math.ceil(w / 4)))[:h, :w]
    return tone > thr


def _row_runs(row: np.ndarray):
    runs, start = [], None
    for x, v in enumerate(row):
        if v and start is None:
            start = x
        elif not v and start is not None:
            runs.append((start, x)); start = None
    if start is not None:
        runs.append((start, len(row)))
    return runs


def halftone_svg(alpha: np.ndarray, klass: np.ndarray, th: dict, band: int = 8) -> str:
    cells = halftone(alpha)
    out = [f'<g shape-rendering="crispEdges" transform="translate({PX + 4},{PY + 4}) scale({CELL})">',
           f'<set attributeName="opacity" to="0" begin="{T_SWITCH}s"/>']
    h = cells.shape[0]
    for b, y0 in enumerate(range(0, h, band)):
        paths = {0: [], 1: []}
        for y in range(y0, min(h, y0 + band)):
            for k in (0, 1):
                for s, e in _row_runs(cells[y] & (klass[y] == k)):
                    paths[k].append(f"M{s} {y}h{e - s}v1h{-(e - s)}z")
        if not paths[0] and not paths[1]:
            continue
        begin = 0.2 + b * 0.07
        out.append(f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.7s" begin="{begin:.2f}s" '
                   f'fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".4 0 .2 1"/>')
        if paths[0]:
            out.append(f'<path fill="{th["DOT"]}" d="{"".join(paths[0])}"/>')
        if paths[1]:
            out.append(f'<path fill="{th["DOT2"]}" d="{"".join(paths[1])}"/>')
        out.append('</g>')
    out.append("</g>")
    return "".join(out)


# ──────────────────────────────── pattern I/A (charte) ──────────────────
def ia_pattern_def(th: dict) -> str:
    """Motif « I A » de la charte (trapèzes), en contour, rangées alternées tête-bêche."""
    tile_w, tile_h, s = 64, 96, th["PATTERN"]
    # « I » : parallélogramme incliné ; « A » : trapèze + triangle intérieur
    i_path = "M2 46 L12 2 L22 2 L12 46 Z"
    a_path = "M24 46 L36 2 L54 2 L62 46 Z M41 36 L47 14 L53 36 Z"
    row = f'<path d="{i_path}" fill="none" stroke="{s}" stroke-width="1.2"/><path d="{a_path}" fill="none" stroke="{s}" stroke-width="1.2"/>'
    return (f'<pattern id="iaPattern" width="{tile_w}" height="{tile_h}" patternUnits="userSpaceOnUse">'
            f'{row}<g transform="translate({tile_w},{tile_h}) rotate(180)">{row}</g></pattern>')


# ──────────────────────────────── SYSTEM.INFO ───────────────────────────
def leader(key: str, value: str, cols: int = COLS) -> str:
    dots = max(3, cols - len(key) - len(value) - 2)
    return f"{key} {'.' * dots} {value}"


def info_svg(th: dict) -> str:
    out = []
    a = out.append
    a(f'<text x="{INFO_X}" y="74" font-size="10" letter-spacing="3" fill="{th["DIM"]}">SYSTEM.INFO</text>')
    a(f'<line x1="{INFO_X}" y1="82" x2="{W - 30}" y2="82" stroke="url(#accent)" stroke-width="1.5" opacity="0.9"/>')
    pill_w = 9 * len(HANDLE) + 34
    a(f'<rect x="{INFO_X}" y="96" width="{pill_w}" height="24" rx="6" fill="{th["PILL_BG"]}" stroke="{th["PILL_STROKE"]}"/>')
    a(f'<circle cx="{INFO_X + 13}" cy="108" r="3.5" fill="{th["HIGHLIGHT"]}">'
      f'<animate attributeName="opacity" values="1;0.25;1" dur="1.8s" repeatCount="indefinite"/></circle>')
    a(f'<text x="{INFO_X + 24}" y="112.5" font-size="13" font-weight="700" fill="{th["TEXT"]}">{HANDLE}</text>')
    a(f'<text x="{INFO_X + pill_w + 12}" y="112.5" font-size="11" fill="{th["MUTED"]}">online · sophia-antipolis · 06</text>')

    y, i = 148, 0
    for item in INFO_LINES:
        begin = 0.5 + i * 0.12
        if item is None:
            a(f'<text x="{INFO_X}" y="{y}" font-size="12" fill="{th["DIM"]}" opacity="0">'
              f'<animate attributeName="opacity" values="0;1" dur="0.4s" begin="{begin:.2f}s" fill="freeze"/>'
              f'<tspan fill="{th["ACCENT"]}">- Contact </tspan>{"-" * (COLS - 10)}</text>')
        else:
            key, val = item
            line = leader(key, val)
            dots = line[len(key) + 1: len(line) - len(val) - 1]
            a(f'<text x="{INFO_X}" y="{y}" font-size="12" fill="{th["TEXT"]}" opacity="0">'
              f'<animate attributeName="opacity" values="0;1" dur="0.4s" begin="{begin:.2f}s" fill="freeze"/>'
              f'<animateTransform attributeName="transform" type="translate" values="-8 0;0 0" dur="0.4s" '
              f'begin="{begin:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".4 0 .2 1"/>'
              f'<tspan fill="{th["KEY"]}">{esc(key)} </tspan>'
              f'<tspan fill="{th["DIM"]}">{dots}</tspan>'
              f'<tspan fill="{th["TEXT"]}"> {esc(val)}</tspan></text>')
        y += 22
        i += 1
    a(f'<text x="{INFO_X}" y="{y}" font-size="12" fill="{th["ACCENT2"]}" opacity="0">'
      f'<animate attributeName="opacity" values="0;1" dur="0.1s" begin="{0.5 + i * 0.12:.2f}s" fill="freeze"/>'
      f'<tspan fill="{th["HIGHLIGHT"]}">$</tspan> <tspan>█<animate attributeName="opacity" values="1;0;1" dur="1s" '
      f'repeatCount="indefinite"/></tspan></text>')
    return "".join(out)


# ──────────────────────────────── assemblage ────────────────────────────
def build_svg(logo_path, icons_dir, theme: str = "dark", n_particles: int = 1100) -> str:
    th = THEMES[theme]
    alpha, klass = load_logo(logo_path)
    shapes = build_shapes(logo_path, icons_dir)
    s = []
    a = s.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'font-family="{FONT}" role="img" aria-label="Maison de l\'IA — profile.sh --live">')
    a('<defs>'
      f'<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0" stop-color="{th["ACCENT"]}"><animate attributeName="stop-color" values="{th["ACCENT"]};{th["ACCENT2"]};{th["KEY"]};{th["ACCENT"]}" dur="10s" repeatCount="indefinite"/></stop>'
      f'<stop offset="0.5" stop-color="{th["ACCENT2"]}"><animate attributeName="stop-color" values="{th["ACCENT2"]};{th["KEY"]};{th["ACCENT"]};{th["ACCENT2"]}" dur="10s" repeatCount="indefinite"/></stop>'
      f'<stop offset="1" stop-color="{th["KEY"]}"><animate attributeName="stop-color" values="{th["KEY"]};{th["ACCENT"]};{th["ACCENT2"]};{th["KEY"]}" dur="10s" repeatCount="indefinite"/></stop>'
      '</linearGradient>'
      f'<linearGradient id="panelGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{th["BG"]}"/><stop offset="1" stop-color="{th["PANEL2"]}"/></linearGradient>'
      f'<linearGradient id="patternFade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>'
      f'<mask id="patternMask"><rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" fill="url(#patternFade)"/></mask>'
      '<filter id="glow3" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3"/></filter>'
      f'{ia_pattern_def(th)}'
      f'<clipPath id="winClip"><rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="18"/></clipPath>'
      f'<clipPath id="panelClip"><rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="10"/></clipPath>'
      '</defs>')
    # fenêtre
    a(f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="18" fill="{th["BG"]}"/>')
    a('<g clip-path="url(#winClip)">')
    a(f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" fill="url(#panelGrad)"/>')
    a(f'<rect x="2" y="2" width="{W - 4}" height="46" fill="{th["BAR"]}"/>')
    a(f'<line x1="2" y1="48" x2="{W - 2}" y2="48" stroke="{th["BARLINE"]}"/>')
    a(f'<circle cx="30" cy="25" r="5.5" fill="{th["ACCENT"]}"/><circle cx="50" cy="25" r="5.5" fill="{th["ACCENT2"]}"/><circle cx="70" cy="25" r="5.5" fill="{th["HIGHLIGHT"]}"/>')
    a(f'<text x="{W / 2}" y="29" text-anchor="middle" font-size="12" fill="{th["MUTED"]}">{esc(TITLE_BAR)}</text>')
    # panneau VISUAL.MAP
    a(f'<text x="{PX + 2}" y="74" font-size="10" letter-spacing="3" fill="{th["DIM"]}">VISUAL.MAP</text>')
    a(f'<rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="10" fill="none" stroke="{th["FRAME"]}" stroke-width="2" opacity="0.45" filter="url(#glow3)"/>')
    a(f'<rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="10" fill="{th["PANEL"]}" stroke="{th["PANEL_STROKE"]}"/>')
    a(f'<rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="10" fill="url(#iaPattern)" mask="url(#patternMask)"/>')
    a('<g clip-path="url(#panelClip)">')
    a(halftone_svg(alpha, klass, th))
    a(particles_svg(shapes, klass, n_particles, th))
    a(f'<rect x="{PX}" y="{PY}" width="{PW}" height="2" fill="{th["ACCENT2"]}" opacity="0.35">'
      f'<animateTransform attributeName="transform" type="translate" values="0 -4;0 {PH + 4}" dur="5s" repeatCount="indefinite"/></rect>')
    a('</g>')
    # coins (« cadres » de la charte)
    a(f'<g fill="none" stroke="{th["FRAME"]}" stroke-width="2" opacity="0.9">'
      f'<path d="M{PX - 6} {PY + 14}V{PY - 6}H{PX + 14}"/><path d="M{PX + PW - 14} {PY - 6}H{PX + PW + 6}V{PY + 14}"/>'
      f'<path d="M{PX - 6} {PY + PH - 14}V{PY + PH + 6}H{PX + 14}"/><path d="M{PX + PW - 14} {PY + PH + 6}H{PX + PW + 6}V{PY + PH - 14}"/></g>')
    a(info_svg(th))
    a(f'<text x="{W / 2}" y="{H - 12}" text-anchor="middle" font-size="10.5" fill="{th["DIM"]}">{esc(FOOTER)}</text>')
    a('</g>')
    a(f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="18" fill="none" stroke="url(#accent)" stroke-opacity="0.6"/>')
    a('</svg>')
    return "".join(s)


def main(argv=None) -> int:
    global _FONT_PATH
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logo-dark", default="assets/logo/mia-logo-dark.png")
    ap.add_argument("--logo-light", default="assets/logo/mia-logo-light.png")
    ap.add_argument("--icons", default="assets/icons")
    ap.add_argument("--font", default=None, help="police .ttf/.otf pour la forme « 06 » (ex. Pogonia-Black)")
    ap.add_argument("--out", default="assets")
    ap.add_argument("--particles", type=int, default=1100)
    args = ap.parse_args(argv)
    _FONT_PATH = args.font
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for theme, logo in (("dark", args.logo_dark), ("light", args.logo_light)):
        svg = build_svg(logo, args.icons, theme, args.particles)
        p = out / f"hero-{theme}.svg"
        p.write_text(svg, encoding="utf-8")
        print(f"écrit {p} ({len(svg) // 1024} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
