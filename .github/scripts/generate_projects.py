#!/usr/bin/env python3
"""
Génère le panneau projets (projects.svg / projects-light.svg), aux couleurs de la
charte MIA, dans le style « terminal » du héros : grille de cartes 2 colonnes avec
icône officielle, description, pastilles de tags, étoiles, donut des langages.

Édition : modifier projects.json (ordre = ordre d'affichage) — le README ne change pas.
Usage : generate_projects.py merged.json out/ [--now ISO8601]
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from charte import (
    AURIA, BLEU_LUMEN, BLEU_QUANTIQUE, DATA_BLOOM, DEEP_BLUE, DEEP_BLUE_2, DEEP_BLUE_3,
    MATIERE_GRISE, NEURA_VERDE, ROUGE_LOVELACE, TERRA, WHITE,
)

ROOT = Path(__file__).resolve().parents[2]

THEMES = {
    "dark": {
        "BG": DEEP_BLUE, "PANEL": DEEP_BLUE_3, "BAR": DEEP_BLUE_2,
        "TEXT": WHITE, "MUTED": BLEU_QUANTIQUE, "DIM": BLEU_QUANTIQUE, "KEY": BLEU_LUMEN,
        "ACCENT": TERRA, "ACCENT2": AURIA, "HIGHLIGHT": DATA_BLOOM,
        "STROKE": "rgba(152,168,198,0.35)", "STROKE_HI": "rgba(152,168,198,0.6)",
        "BARLINE": "rgba(194,212,239,0.12)", "RING_BG": "rgba(152,168,198,0.2)",
        "PILL_BG": "rgba(174,101,87,0.28)", "PILL_STROKE": "rgba(242,178,165,0.55)",
        "PILL_TX": AURIA, "ICONS": "icons",
        "DONUT": [TERRA, BLEU_LUMEN, AURIA, DATA_BLOOM, BLEU_QUANTIQUE, MATIERE_GRISE],
    },
    "light": {
        "BG": WHITE, "PANEL": NEURA_VERDE, "BAR": BLEU_LUMEN,
        "TEXT": DEEP_BLUE, "MUTED": DEEP_BLUE, "DIM": BLEU_QUANTIQUE, "KEY": ROUGE_LOVELACE,
        "ACCENT": TERRA, "ACCENT2": ROUGE_LOVELACE, "HIGHLIGHT": ROUGE_LOVELACE,
        "STROKE": "rgba(22,52,88,0.3)", "STROKE_HI": "rgba(22,52,88,0.55)",
        "BARLINE": "rgba(22,52,88,0.12)", "RING_BG": "rgba(22,52,88,0.15)",
        "PILL_BG": "rgba(194,212,239,0.5)", "PILL_STROKE": "rgba(22,52,88,0.4)",
        "PILL_TX": DEEP_BLUE, "ICONS": "icons-bleu",
        "DONUT": [TERRA, DEEP_BLUE, ROUGE_LOVELACE, BLEU_QUANTIQUE, AURIA, MATIERE_GRISE],
    },
}

W = 1180
CARD_W, CARD_H, GAP, MARGIN = 578, 168, 14, 5
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"


def esc(s):
    return html.escape(str(s), quote=True)


def _parse(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def rel_time(iso, now=None):
    """Ancienneté en français ; `now` ISO8601 injectable pour les tests."""
    if not iso:
        return "n/a"
    try:
        ref = _parse(now) if now else datetime.now(timezone.utc)
        d = ref - _parse(iso)
        if d.days >= 730:
            return f"il y a {d.days // 365} ans"
        if d.days >= 365:
            return "il y a 1 an"
        if d.days >= 60:
            return f"il y a {d.days // 30} mois"
        if d.days >= 30:
            return "il y a 1 mois"
        if d.days >= 1:
            return f"il y a {d.days} j"
        h = d.seconds // 3600
        return f"il y a {h} h" if h else "à l'instant"
    except Exception:
        return "n/a"


def wrap_text(s, max_chars, max_lines=2):
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and len(" ".join(lines).split()) < len(words):
        lines[-1] = lines[-1][: max_chars - 1].rstrip() + "…"
    return lines


def icon_b64(name, theme):
    """Icône officielle embarquée (blanche en sombre, bleue en clair)."""
    if not name:
        return None
    p = ROOT / "assets" / THEMES[theme]["ICONS"] / f"{name}.png"
    if not p.exists():
        return None
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def donut_segments(languages, cx, cy, r, begin, th=None):
    """Donut animé (chaque segment se dessine) + légende [(langage, fraction, couleur)]."""
    th = th or THEMES["dark"]
    total = sum(languages.values()) or 1
    entries = sorted(languages.items(), key=lambda kv: -kv[1])[:4]
    other = total - sum(v for _, v in entries)
    if other > 0:
        entries.append(("Autres", other))
    C = 2 * math.pi * r
    out, legend, offset, t = [], [], 0.0, begin
    for i, (lang, v) in enumerate(entries):
        frac = v / total
        seg = frac * C
        col = th["DONUT"][i % len(th["DONUT"])]
        out.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="9" '
            f'stroke-dasharray="{seg:.2f} {C - seg:.2f}" stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx} {cy})" opacity="0">'
            f'<animate attributeName="opacity" from="0" to="1" dur="0.01s" begin="{t:.2f}s" fill="freeze"/>'
            f'<animate attributeName="stroke-dasharray" from="0 {C:.2f}" to="{seg:.2f} {C - seg:.2f}" '
            f'dur="0.6s" begin="{t:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.3 0 0.2 1"/>'
            f'</circle>')
        legend.append((lang, frac, col))
        offset += seg
        t += 0.18
    return "".join(out), legend


def card(p, x, y, idx, th, now=None):
    b = 0.25 + idx * 0.12
    e = []
    a = e.append
    repo = p.get("repo", "")
    a(f'<a href="https://github.com/{esc(repo)}" target="_blank">')
    a(f'<g opacity="0" transform="translate({x},{y})">')
    a(f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{b:.2f}s" fill="freeze"/>')
    a(f'<rect width="{CARD_W}" height="{CARD_H}" rx="12" fill="{th["PANEL"]}" stroke="{th["STROKE"]}">'
      f'<animate attributeName="stroke" values="{th["STROKE"]};{th["STROKE_HI"]};{th["STROKE"]}" '
      f'dur="4.5s" begin="{b + idx * 0.6:.2f}s" repeatCount="indefinite"/></rect>')
    a(f'<rect width="{CARD_W}" height="30" rx="12" fill="{th["BAR"]}"/>')
    a(f'<rect y="18" width="{CARD_W}" height="12" fill="{th["BAR"]}"/>')
    a(f'<line x1="0" y1="30" x2="{CARD_W}" y2="30" stroke="{th["BARLINE"]}"/>')
    a(f'<text x="16" y="19" font-size="10" fill="{th["MUTED"]}"><tspan fill="{th["ACCENT"]}">&#8226;</tspan> {esc(repo)}</text>')

    # pastille d'activité : pulse si poussé dans les 30 jours
    days = 999
    try:
        days = ((_parse(now) if now else datetime.now(timezone.utc)) - _parse(p.get("pushed_at", ""))).days
    except Exception:
        pass
    if days <= 30:
        a(f'<circle cx="{CARD_W - 16}" cy="15" r="3.5" fill="{th["HIGHLIGHT"]}">'
          f'<animate attributeName="opacity" values="1;0.25;1" dur="1.8s" repeatCount="indefinite"/></circle>')
    else:
        a(f'<circle cx="{CARD_W - 16}" cy="15" r="3.5" fill="{th["DIM"]}" opacity="0.6"/>')

    # icône officielle (flottement doux) ou monogramme
    flott = (f'<animateTransform attributeName="transform" type="translate" values="0 0; 0 -2.5; 0 0" '
             f'dur="5s" begin="{b + idx * 0.4:.2f}s" repeatCount="indefinite" calcMode="spline" '
             f'keyTimes="0;0.5;1" keySplines="0.4 0 0.6 1;0.4 0 0.6 1"/>')
    logo = icon_b64(p.get("icon"), "dark" if th is THEMES["dark"] else "light")
    if logo:
        a(f'<g>{flott}<image x="14" y="42" width="44" height="44" href="{logo}" preserveAspectRatio="xMidYMid meet"/></g>')
    else:
        initial = esc((p.get("name") or "?")[0].upper())
        a(f'<g>{flott}<rect x="14" y="42" width="44" height="44" rx="9" fill="{th["ACCENT"]}" opacity="0.9"/>'
          f'<text x="36" y="72" text-anchor="middle" font-size="20" font-weight="700" fill="{WHITE}">{initial}</text></g>')

    name = esc(p.get("name", "sans-nom"))
    a(f'<text x="68" y="61" font-size="17" font-weight="700" fill="{th["TEXT"]}">{name}'
      f'<tspan fill="{th["ACCENT"]}">_<animate attributeName="opacity" values="1;0;1" dur="1.2s" '
      f'begin="{b + 0.4:.2f}s" repeatCount="indefinite"/></tspan></text>')
    for i, line in enumerate(wrap_text(p.get("description", ""), 46)):
        a(f'<text x="68" y="{80 + i * 16}" font-size="11" fill="{th["MUTED"]}">{esc(line)}</text>')

    tx = 68
    for tag in (p.get("tags") or [])[:3]:
        tw = len(tag) * 6.6 + 14
        a(f'<rect x="{tx}" y="118" width="{tw:.0f}" height="17" rx="8.5" fill="{th["PILL_BG"]}" stroke="{th["PILL_STROKE"]}"/>')
        a(f'<text x="{tx + tw / 2:.0f}" y="130" text-anchor="middle" font-size="9.5" fill="{th["PILL_TX"]}">{esc(tag)}</text>')
        tx += tw + 7

    a(f'<text x="68" y="155" font-size="11" fill="{th["MUTED"]}">'
      f'<tspan fill="{th["ACCENT2"]}">&#9733;</tspan> {p.get("stars", 0)}'
      f'<tspan fill="{th["DIM"]}" dx="14">maj {rel_time(p.get("pushed_at"), now)}</tspan></text>')

    langs = p.get("languages") or {}
    if langs:
        cx, cy, r = CARD_W - 58, CARD_H // 2 + 6, 27
        segs, legend = donut_segments(langs, cx, cy, r, b + 0.3, th)
        a(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{th["RING_BG"]}" stroke-width="9"/>')
        a(segs)
        a(f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-size="11" font-weight="700" fill="{th["TEXT"]}">{legend[0][1] * 100:.0f}%</text>')
        dot_x = cx - r - 96
        ly = cy - 22
        for lang, frac, col in legend[:3]:
            a(f'<circle cx="{dot_x}" cy="{ly}" r="3.5" fill="{col}"/>')
            a(f'<text x="{dot_x + 9}" y="{ly + 4}" font-size="10" fill="{th["MUTED"]}">{esc(lang)} {frac * 100:.0f}%</text>')
            ly += 18
    a('</g></a>')
    return "".join(e)


def build(projects, theme="dark", now=None):
    th = THEMES[theme]
    rows = math.ceil(len(projects) / 2)
    height = 56 + rows * (CARD_H + GAP) + MARGIN
    s = []
    a = s.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" '
      f'font-family="{FONT}" role="img" aria-label="Projets de la Maison de l\'IA">')
    a(f'<rect width="{W}" height="{height}" fill="{th["BG"]}"/>')
    a(f'<defs><linearGradient id="acc" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0" stop-color="{th["ACCENT"]}"><animate attributeName="stop-color" values="{th["ACCENT"]};{th["KEY"]};{th["HIGHLIGHT"]};{th["ACCENT"]}" dur="10s" repeatCount="indefinite"/></stop>'
      f'<stop offset="1" stop-color="{th["KEY"]}"><animate attributeName="stop-color" values="{th["KEY"]};{th["HIGHLIGHT"]};{th["ACCENT"]};{th["KEY"]}" dur="10s" repeatCount="indefinite"/></stop>'
      f'</linearGradient></defs>')
    a(f'<text x="{MARGIN + 2}" y="18" font-size="11" letter-spacing="2" fill="{th["KEY"]}">PROJECTS.LIST</text>')
    a(f'<text x="{MARGIN + 130}" y="18" font-size="10" fill="{th["DIM"]}">./projects.sh --all</text>')
    a(f'<line x1="{MARGIN}" y1="28" x2="{W - MARGIN}" y2="28" stroke="url(#acc)" stroke-width="1.5" opacity="0.8"/>')
    for i, p in enumerate(projects):
        x = MARGIN + (i % 2) * (CARD_W + GAP + 4)
        y = 42 + (i // 2) * (CARD_H + GAP)
        a(card(p, x, y, i, th, now))
    a('</svg>')
    return "".join(s)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", nargs="?", default="merged.json")
    ap.add_argument("outdir", nargs="?", default=".")
    ap.add_argument("--now", default=None, help="date ISO8601 de référence (tests)")
    args = ap.parse_args(argv)
    with open(args.src, encoding="utf-8") as f:
        projects = json.load(f)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    for theme, fname in (("dark", "projects.svg"), ("light", "projects-light.svg")):
        svg = build(projects, theme, args.now)
        (out / fname).write_text(svg, encoding="utf-8")
        print(f"écrit {out / fname} ({len(svg) // 1024} Ko, {len(projects)} projets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
