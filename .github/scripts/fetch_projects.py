#!/usr/bin/env python3
"""
Fusionne projects.json (curé à la main) avec les données GitHub en direct.
À lancer dans l'Action avec GITHUB_TOKEN. Produit merged.json pour le générateur.

Curé : name, repo, icon, description (prioritaire si non vide), tags, ordre.
Auto : stars, languages (répartition en octets pour le donut), pushed_at.
Si l'API échoue pour un dépôt, la carte se rend quand même avec les données curées.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")


def gh(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {TOKEN}" if TOKEN else "",
        "User-Agent": "mia-projects-panel",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def merge(projects, fetch=gh):
    for p in projects:
        repo = p.get("repo", "").replace("https://github.com/", "").strip("/")
        p["repo"] = repo
        try:
            info = fetch(f"https://api.github.com/repos/{repo}")
            p["stars"] = info.get("stargazers_count", 0)
            p["pushed_at"] = info.get("pushed_at")
            if not p.get("description"):
                p["description"] = info.get("description") or ""
            p["languages"] = fetch(f"https://api.github.com/repos/{repo}/languages")
        except Exception as e:  # noqa: BLE001 — la carte doit survivre à l'API
            print(f"avertissement : {repo} inaccessible : {e}", file=sys.stderr)
            p.setdefault("stars", 0)
            p.setdefault("languages", {})
            p.setdefault("pushed_at", None)
    return projects


def main():
    with open("projects.json", encoding="utf-8") as f:
        projects = json.load(f)
    merge(projects)
    with open("merged.json", "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False)
    print(f"{len(projects)} projets fusionnés")


if __name__ == "__main__":
    main()
