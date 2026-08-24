"""Tests du panneau projets (étape 2) — palette charte, données offline."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github" / "scripts"))

import charte  # noqa: E402
import fetch_projects as fp  # noqa: E402
import generate_projects as gp  # noqa: E402

NOW = "2026-08-24T12:00:00Z"

SAMPLE = [
    {"name": "Real VS AI", "repo": "MaisonIA06/Real_VS_AI", "icon": "sensibiliser",
     "description": "Plateforme éducative pour développer l'esprit critique face aux contenus IA",
     "tags": ["TypeScript", "Django"], "stars": 3,
     "languages": {"TypeScript": 6000, "Python": 3000, "CSS": 1000},
     "pushed_at": "2026-08-20T10:00:00Z"},
    {"name": "DeepFake", "repo": "MaisonIA06/DeepFake", "icon": "robotique",
     "description": "Face Swap temps réel", "tags": ["Python"], "stars": 0,
     "languages": {}, "pushed_at": None},
]


def test_rel_time():
    assert gp.rel_time("2026-08-23T12:00:00Z", NOW) == "il y a 1 j"
    assert gp.rel_time("2026-06-20T12:00:00Z", NOW) == "il y a 2 mois"
    assert gp.rel_time("2024-08-24T12:00:00Z", NOW) == "il y a 2 ans"
    assert gp.rel_time("2026-08-24T09:00:00Z", NOW) == "il y a 3 h"
    assert gp.rel_time(None, NOW) == "n/a"


def test_wrap_text_two_lines_with_ellipsis():
    lines = gp.wrap_text("un texte assez long pour devoir être coupé en plusieurs morceaux vraiment", 20, 2)
    assert len(lines) == 2 and lines[-1].endswith("…")
    assert gp.wrap_text("court", 20, 2) == ["court"]


def test_donut_segments_cover_circle():
    svg, legend = gp.donut_segments({"Python": 70, "C++": 20, "CMake": 10}, 100, 100, 27, 0.5)
    assert abs(sum(frac for _, frac, _ in legend) - 1.0) < 1e-6
    assert all(col.upper() in charte.CHARTE_COLORS for _, _, col in legend)
    assert "circle" in svg


def test_icon_b64_differs_per_theme_and_handles_unknown():
    dark = gp.icon_b64("robotique", "dark")
    light = gp.icon_b64("robotique", "light")
    assert dark and light and dark != light
    assert dark.startswith("data:image/png;base64,")
    assert gp.icon_b64("inexistante", "dark") is None


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_build_valid_xml_charte_only(theme):
    svg = gp.build(SAMPLE, theme=theme, now=NOW)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    for token in ("PROJECTS.LIST", "MaisonIA06/Real_VS_AI", "Real VS AI", "DeepFake", "TypeScript"):
        assert token in svg, token
    for forbidden in ("#7C3AED", "#22D3EE", "#10B981", "#EC4899"):
        assert forbidden.upper() not in svg.upper()
    assert "data:image/png;base64," in svg  # icônes embarquées


def test_fetch_merge_offline_with_failures_and_data():
    projects = [{"repo": "MaisonIA06/A", "description": ""}, {"repo": "MaisonIA06/B", "description": "curée"}]

    def fake(url):
        if "MaisonIA06/A" in url and url.endswith("languages"):
            return {"Python": 10}
        if "MaisonIA06/A" in url:
            return {"stargazers_count": 4, "pushed_at": NOW, "description": "auto"}
        raise OSError("réseau HS")

    merged = fp.merge(projects, fake)
    a, b = merged
    assert a["stars"] == 4 and a["languages"] == {"Python": 10} and a["description"] == "auto"
    assert b["stars"] == 0 and b["languages"] == {} and b["pushed_at"] is None and b["description"] == "curée"


def test_main_writes_both_themes(tmp_path):
    src = tmp_path / "merged.json"
    src.write_text(json.dumps(SAMPLE), encoding="utf-8")
    rc = gp.main([str(src), str(tmp_path), "--now", NOW])
    assert rc == 0
    for name in ("projects.svg", "projects-light.svg"):
        p = tmp_path / name
        assert p.exists() and p.stat().st_size > 2000
