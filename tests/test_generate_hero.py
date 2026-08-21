"""Tests du générateur de héros SVG (étape 1)."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github" / "scripts"))

import generate_hero as gh  # noqa: E402


@pytest.fixture
def logo_png(tmp_path):
    """Petit logo synthétique (disque blanc sur fond transparent)."""
    img = Image.new("LA", (120, 80), (0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((20, 10, 100, 70), fill=(255, 255))
    p = tmp_path / "logo.png"
    img.save(p)
    return p


def test_load_mask_keeps_aspect_and_is_boolean(logo_png):
    mask = gh.load_mask(logo_png, gh.GRID_W, gh.GRID_H)
    assert mask.dtype == bool
    assert mask.shape == (gh.GRID_H, gh.GRID_W)
    # le logo est centré : présence de pixels au milieu, aucun dans les coins
    assert mask[gh.GRID_H // 2, gh.GRID_W // 2]
    assert not mask[0, 0] and not mask[-1, -1]


def test_sample_points_all_inside_mask(logo_png):
    mask = gh.load_mask(logo_png, gh.GRID_W, gh.GRID_H)
    pts = gh.sample_points(mask, 300, seed=1)
    assert pts.shape == (300, 2)
    ys, xs = pts[:, 1], pts[:, 0]
    assert mask[ys, xs].all()


def test_sample_points_is_deterministic(logo_png):
    mask = gh.load_mask(logo_png, gh.GRID_W, gh.GRID_H)
    a = gh.sample_points(mask, 50, seed=7)
    b = gh.sample_points(mask, 50, seed=7)
    assert np.array_equal(a, b)


def test_shape_masks_have_same_grid_and_are_non_empty(logo_png):
    shapes = gh.build_shapes(logo_png)
    assert len(shapes) >= 3
    for name, m in shapes:
        assert m.shape == (gh.GRID_H, gh.GRID_W), name
        assert m.sum() > 200, name


def test_dotted_leader_fills_columns():
    line = gh.leader("Subject", "Maison de l'IA", cols=60)
    assert len(line) == 60
    assert line.startswith("Subject ") and line.endswith(" Maison de l'IA")
    assert "....." in line


def test_build_svg_is_valid_xml_and_contains_expected_blocks(logo_png):
    svg = gh.build_svg(logo_png, theme="dark", n_particles=120)
    root = ET.fromstring(svg)  # XML bien formé
    assert root.tag.endswith("svg")
    assert 'viewBox="0 0 1180 610"' in svg
    for token in ("VISUAL.MAP", "SYSTEM.INFO", "Subject", "Origin", "Status", "MaisonIA06"):
        assert token in svg, token
    # animations SMIL présentes (trame + particules + curseur)
    assert svg.count("<animateTransform") >= 120
    assert "repeatCount=\"indefinite\"" in svg


def test_light_theme_uses_light_palette(logo_png):
    dark = gh.build_svg(logo_png, theme="dark", n_particles=20)
    light = gh.build_svg(logo_png, theme="light", n_particles=20)
    assert gh.THEMES["dark"]["BG"] in dark and gh.THEMES["dark"]["BG"] not in light
    assert gh.THEMES["light"]["BG"] in light


def test_main_writes_both_files(tmp_path, logo_png):
    out = gh.main(["--logo", str(logo_png), "--out", str(tmp_path), "--particles", "30"])
    assert out == 0
    for name in ("hero-dark.svg", "hero-light.svg"):
        p = tmp_path / name
        assert p.exists() and p.stat().st_size > 1000


def test_drawn_masks_are_shapes_not_full_rectangles():
    """Les masques dessinés (texte, réseau) ne doivent pas remplir toute la grille."""
    for name, mask in (("IA", gh.text_mask("IA")), ("neural", gh.neural_mask()), ("06", gh.text_mask("06"))):
        fill = mask.mean()
        assert 0.03 < fill < 0.45, (name, fill)
        assert not mask[0, 0] and not mask[-1, -1], name
