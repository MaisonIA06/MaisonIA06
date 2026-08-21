# MaisonIA06/MaisonIA06 — README de profil GitHub

Dépôt spécial : son `README.md` s'affiche sur https://github.com/MaisonIA06.
Design « System UI / terminal cyberpunk » (violet `#7C3AED` · cyan `#22D3EE` · rose `#F472B6`).

## Structure

- `README.md` — le profil (images SVG générées + widgets externes).
- `assets/hero-dark.svg`, `assets/hero-light.svg` — héros animé (fenêtre terminal :
  `VISUAL.MAP` logo tramé → particules morphant logo → IA → réseau de neurones → 06,
  `SYSTEM.INFO` clé····valeur). **Générés, ne pas éditer à la main.**
- `assets/logo/mia-logo.png` — logo officiel (source des masques du héros).
- `.github/scripts/generate_hero.py` — générateur du héros (contenu des lignes
  `SYSTEM.INFO` dans `INFO_LINES`, formes dans `build_shapes`).
- `tests/` — tests pytest du générateur.
- `.github/workflows/ci.yml` — pytest + génération à blanc à chaque push.

## Commandes

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests                 # tests
.venv/bin/python .github/scripts/generate_hero.py   # régénère assets/hero-*.svg
```

Prévisualiser un SVG **en document** (`http://127.0.0.1:8765/hero-dark.svg` via
`python3 -m http.server`) : les captures Chrome/CDP d'un SVG dans `<img>` sont figées
à t=0, même si GitHub l'anime bien en navigation réelle.

## Contraintes GitHub README

- Pas de CSS/JS : tout effet = SVG (SMIL) servi via `raw.githubusercontent.com`,
  ou widgets externes (streak-stats, github-readme-stats, snake).
- Blocs ```` ```ansi ```` non colorés par GitHub → utiliser ```` ```diff ```` pour la couleur.
- Garder le nombre d'animations SMIL par SVG raisonnable (≈1 000 particules, un seul
  `<set>` au niveau du groupe, interpolation linéaire) sinon le rendu gèle.
- `github-readme-stats.vercel.app` (officiel) est parfois en pause → miroir
  `github-readme-stats-eight-theta.vercel.app` (vérifié le 2026-08-21).
