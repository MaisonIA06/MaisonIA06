"""Tests du générateur de héros SVG (palette de la charte MIA)."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github" / "scripts"))

import generate_hero as gh  # noqa: E402

ICONS = ROOT / "assets" / "icons"


@pytest.fixture
def logo_png(tmp_path):
    """Logo synthétique bicolore : disque blanc à gauche, disque terracotta à droite."""
    img = Image.new("RGBA", (240, 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((10, 10, 90, 90), fill=(255, 255, 255, 255))
    d.ellipse((150, 10, 230, 90), fill=(174, 101, 87, 255))
    p = tmp_path / "logo.png"
    img.save(p)
    return p


def test_palette_is_the_official_charte():
    dark, light = gh.THEMES["dark"], gh.THEMES["light"]
    assert dark["BG"].upper() == gh.DEEP_BLUE == "#163458"
    assert dark["DOT2"].upper() == gh.TERRA == "#AE6557"
    assert light["TEXT"].upper() == gh.DEEP_BLUE
    for th in (dark, light):
        for k, v in th.items():
            if v.startswith("#"):
                assert v.upper() in gh.CHARTE_COLORS, (k, v)  # aucune couleur hors charte


def test_load_logo_returns_alpha_and_color_classes(logo_png):
    alpha, klass = gh.load_logo(logo_png, gh.GRID_W, gh.GRID_H)
    assert alpha.shape == klass.shape == (gh.GRID_H, gh.GRID_W)
    mask = alpha > 0.5
    # classe 0 (couleur principale) à gauche, classe 1 (terracotta) à droite
    left = klass[mask & (np.arange(gh.GRID_W)[None, :] < gh.GRID_W // 2)]
    right = klass[mask & (np.arange(gh.GRID_W)[None, :] >= gh.GRID_W // 2)]
    assert (left == 0).all() and (right == 1).all()
    assert not mask[0, 0] and not mask[-1, -1]


def test_sample_points_inside_mask_and_deterministic(logo_png):
    alpha, _ = gh.load_logo(logo_png, gh.GRID_W, gh.GRID_H)
    mask = alpha > 0.5
    a = gh.sample_points(mask, 300, seed=1)
    b = gh.sample_points(mask, 300, seed=1)
    assert a.shape == (300, 2) and np.array_equal(a, b)
    assert mask[a[:, 1], a[:, 0]].all()


def test_icon_masks_are_outlines_not_blobs():
    for name in ("sensibiliser", "federer", "valoriser", "inspirer", "robotique"):
        m = gh.icon_mask(ICONS / f"{name}.png")
        assert m.shape == (gh.GRID_H, gh.GRID_W)
        assert 0.01 < m.mean() < 0.35, (name, m.mean())


def test_text_mask_is_a_shape():
    m = gh.text_mask("06")
    assert 0.03 < m.mean() < 0.45
    assert not m[0, 0] and not m[-1, -1]


def test_build_shapes_starts_with_logo_and_includes_missions(logo_png):
    shapes = gh.build_shapes(logo_png, ICONS)
    names = [n for n, _ in shapes]
    assert names[0] == "logo"
    for n in ("sensibiliser", "federer", "valoriser", "inspirer"):
        assert n in names
    for _, m in shapes:
        assert m.shape == (gh.GRID_H, gh.GRID_W) and m.sum() > 200


def test_dotted_leader_fills_columns():
    line = gh.leader("Subject", "Maison de l'IA", cols=60)
    assert len(line) == 60 and "....." in line
    assert line.startswith("Subject ") and line.endswith(" Maison de l'IA")


def test_build_svg_valid_xml_with_pattern_and_blocks(logo_png):
    svg = gh.build_svg(logo_png, ICONS, theme="dark", n_particles=120)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg") and 'viewBox="0 0 1180 610"' in svg
    for token in ("VISUAL.MAP", "SYSTEM.INFO", "Subject", "Origin", "Status", "MaisonIA06", 'id="iaPattern"'):
        assert token in svg, token
    assert svg.count("<animateTransform") >= 120
    assert 'href="#pA"' in svg and 'href="#pB"' in svg  # particules bicolores
    assert "#7C3AED" not in svg.upper() and "#22D3EE" not in svg.upper()  # plus de violet/cyan


def test_light_theme_uses_light_palette(logo_png):
    dark = gh.build_svg(logo_png, ICONS, theme="dark", n_particles=20)
    light = gh.build_svg(logo_png, ICONS, theme="light", n_particles=20)
    assert gh.THEMES["dark"]["BG"] in dark and gh.THEMES["light"]["BG"] in light
    # les teintes sombres du panneau n'apparaissent pas en clair (le Deep Blue y sert de texte)
    assert gh.THEMES["dark"]["PANEL"] not in light and gh.THEMES["dark"]["PANEL2"] not in light


def test_main_writes_both_files(tmp_path, logo_png):
    rc = gh.main(["--logo-dark", str(logo_png), "--logo-light", str(logo_png),
                  "--icons", str(ICONS), "--out", str(tmp_path), "--particles", "30"])
    assert rc == 0
    for name in ("hero-dark.svg", "hero-light.svg"):
        p = tmp_path / name
        assert p.exists() and p.stat().st_size > 1000
