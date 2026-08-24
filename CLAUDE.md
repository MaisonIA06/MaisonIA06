# MaisonIA06/MaisonIA06 — README de profil GitHub

Dépôt spécial : son `README.md` s'affiche sur https://github.com/MaisonIA06.
Design « System UI / terminal » **aux couleurs de la charte graphique MIA (2026)** —
source : `/home/mia/Documents/Charte Graphique/` (PDF, logos, icônes, police Pogonia).

## Charte graphique (à respecter partout : héros, widgets, badges, panneaux)

| Nom | Hex | Usage |
|---|---|---|
| Deep Blue | `#163458` | fond principal (dark), texte (light) |
| Bleu Quantique | `#98A8C6` | texte secondaire, cadres |
| Bleu Lumen | `#C2D4EF` | clés, barre (light) |
| Rouge Lovelace | `#994845` | accent fort (light) |
| Terra d'IA | `#AE6557` | **le « IA » du logo, toujours terracotta** ; accent |
| Auria | `#F2B2A5` | accent clair |
| Data Bloom | `#E5EAA8` | mise en lumière de texte (vert) |
| Neura Verde | `#F1F4D0` | fond clair secondaire |
| Matière grise | `#C0C0BE` | neutre |

Teintes de profondeur tolérées du Deep Blue : `#112B4B`, `#0E2440`. **Aucune autre couleur**
(plus de violet/cyan/rose génériques) — un test le vérifie (`test_palette_is_the_official_charte`).
Règles : pas de déformation/contour/couleur hors palette sur le logo ; sur fond bleu foncé le
« M » et la phrase peuvent passer en blanc, le « IA » reste terracotta. Typos : Pogonia (corps),
Like that (signature), Space Odyssey (touche) — non embarquables dans les SVG GitHub (licence /
pas de requêtes externes) : Pogonia n'est utilisée que rasterisée (forme « 06 »), le texte SVG
reste monospace système.

## Structure

- `README.md` — le profil (images SVG générées + widgets externes).
- `assets/hero-dark.svg`, `assets/hero-light.svg` — héros animé (fenêtre terminal :
  `VISUAL.MAP` logo complet tramé bicolore → particules (couleur héritée du pixel du logo,
  M rééquilibré à ~45 % des points via `logo_points`) morphant marque M/A seule → sceau du
  Département 06 → « IA » (Pogonia) → papillon « Inspirer » ; pattern I/A de la charte en
  fond ; `SYSTEM.INFO` clé····valeur). **Générés, ne pas éditer.**
- `assets/logo/` : `mia-logo-*` (logo complet, trame), `mia-mark-*` (marque M/A seule,
  particules), `dept-06.png` (emblème du sceau départemental, nettoyé du texte circulaire) ;
  `assets/icons/*.png` — icônes officielles (version blanche, 420 px).
- `.github/scripts/generate_hero.py` — générateur (palette `THEMES`, lignes `INFO_LINES`,
  formes `MISSION_ICONS`/`build_shapes`, pattern `ia_pattern_def`).
- `projects.json` — liste curée des projets (ordre = ordre d'affichage ; name, repo,
  icon (nom dans `assets/icons*/`), description, tags). Les étoiles/langages/dates sont
  récupérés en live par le workflow.
- `.github/scripts/charte.py` — palette partagée ; `fetch_projects.py` (fusion API GitHub)
  et `generate_projects.py` (cartes terminal, donut langages, icônes embarquées en base64 :
  blanches en sombre, bleues en clair via `assets/icons-bleu/`).
- `.github/workflows/projects.yml` — quotidien + push : publie `projects.svg` /
  `projects-light.svg` sur la branche **`projects`** (le README les référencera par
  `raw.githubusercontent.com/MaisonIA06/MaisonIA06/projects/…`).
- `tests/` — tests pytest des générateurs (héros + projets).
- `.github/workflows/ci.yml` — pytest + génération à blanc à chaque push.

## Commandes

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests                 # tests
# régénère assets/hero-*.svg (Pogonia pour la forme « 06 » ; sans --font → DejaVu)
.venv/bin/python .github/scripts/generate_hero.py \
  --font "/home/mia/Documents/Charte Graphique/POGONIA/POGONIA/Pogonia-Black.otf"
```

# panneau projets en local (token pour éviter le rate-limit anonyme)
GITHUB_TOKEN=$(gh auth token) .venv/bin/python .github/scripts/fetch_projects.py
.venv/bin/python .github/scripts/generate_projects.py merged.json /tmp/out

Prévisualiser un SVG **en document** (`http://127.0.0.1:8765/hero-dark.svg` via
`python3 -m http.server`) : les captures Chrome/CDP d'un SVG dans `<img>` sont figées
à t=0, même si GitHub l'anime bien en navigation réelle. Sans navigateur : `resvg` sur
une variante `sed 's/opacity="0"/opacity="1"/g'` (état final fidèle, animations = apparitions).

## Contraintes GitHub README

- Pas de CSS/JS : tout effet = SVG (SMIL) servi via `raw.githubusercontent.com`,
  ou widgets externes (streak-stats, github-readme-stats, snake).
- Blocs ```` ```ansi ```` non colorés par GitHub → utiliser ```` ```diff ```` pour la couleur.
- Garder le nombre d'animations SMIL par SVG raisonnable (**750 particules** par défaut,
  un seul `<set>` au niveau du groupe, interpolation linéaire) : au-delà, le rendu sature
  le CPU sur machine modeste (constaté avec Brave/CDP le 2026-08-24).
- `github-readme-stats.vercel.app` (officiel) est parfois en pause → miroir
  `github-readme-stats-one-bice.vercel.app` (vérifié le 2026-08-24 : gère custom_title/card_width, contrairement à eight-theta).
