#!/usr/bin/env python3
"""Idempotently create/update Axiom's shared GitHub issue/PR labels.

Runs ONLY from manually dispatched, default-branch GitHub Actions.
Never removes unrelated labels. No third-party Python dependencies.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LABELS_FILE = ROOT / ".github" / "labels.json"


def load_catalog() -> list[dict[str, str]]:
    labels = json.loads(LABELS_FILE.read_text(encoding="utf-8"))
    if not isinstance(labels, list) or not labels:
        raise ValueError("Label catalog must be a nonempty JSON array")
    seen: set[str] = set()
    for label in labels:
        if not isinstance(label, dict) or set(label) != {"name", "color", "description"}:
            raise ValueError(f"Invalid label entry: {label!r}")
        name, color, description = label["name"], label["color"], label["description"]
        if not (isinstance(name, str) and 1 <= len(name) <= 50 and name.casefold() not in seen):
            raise ValueError(f"Invalid or duplicate label name: {name!r}")
        if not (isinstance(color, str) and len(color) == 6 and
                all(c in "0123456789abcdefABCDEF" for c in color)):
            raise ValueError(f"Invalid RGB hex color for {name}")
        if not (isinstance(description, str) and len(description) <= 100):
            raise ValueError(f"Invalid description for {name}")
        seen.add(name.casefold())
    return labels


def request_json(method: str, path: str, token: str, payload: dict | None = None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(
        "https://api.github.com" + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "axiom-label-sync",
        },
    )
    try:
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        # Don't log headers: they could include credentials.
        raise RuntimeError(f"GitHub {method} {path} returned HTTP {exc.code}") from exc


def sync() -> None:
    catalog = load_catalog()
    token = os.environ.get("GH_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    ref = os.environ.get("GITHUB_REF", "")
    if not token:
        raise RuntimeError("Missing GH_TOKEN (GitHub Actions token)")
    if not repository or repository.count("/") != 1:
        raise RuntimeError("Invalid GITHUB_REPOSITORY")
    if ref != "refs/heads/main":
        raise RuntimeError("Label writes allowed only from main")

    base = "/repos/" + "/".join(quote(part, safe="") for part in repository.split("/")) + "/labels"
    existing: dict[str, dict] = {}
    page = 1
    while True:
        labels = request_json("GET", f"{base}?per_page=100&page={page}", token)
        if not isinstance(labels, list):
            raise RuntimeError("Unexpected GitHub label response")
        for label in labels:
            existing[label["name"].casefold()] = label
        if len(labels) < 100:
            break
        page += 1

    created = updated = unchanged = 0
    for spec in catalog:
        name = spec["name"]
        if name.casefold() not in existing:
            request_json("POST", base, token, spec)
            created += 1
            print(f"Created {name}")
            continue

        current = existing[name.casefold()]
        if (current.get("color", "").lower() == spec["color"].lower()
                and current.get("description", "") == spec["description"]):
            unchanged += 1
            continue
        request_json(
            "PATCH", base + "/" + quote(current["name"], safe=""), token,
            {"color": spec["color"], "description": spec["description"]},
        )
        updated += 1
        print(f"Updated {name}")

    print(f"Sync complete: {created} created, {updated} updated, "
          f"{unchanged} unchanged. Existing unrelated labels were preserved.")


if __name__ == "__main__":
    sync()
