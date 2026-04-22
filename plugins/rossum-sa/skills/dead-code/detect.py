#!/usr/bin/env python3
"""Detect unused/orphan config in a Rossum prd2 env directory.

Usage: python3 detect.py <env_dir>

Six high-confidence checks:
  1. orphan formula .py — no matching schema field id in the same queue
  2. hooks with no queue attachment (scheduled import hooks excluded)
  3. disabled hooks
  4. dead rules — disabled or queues: []
  5. label candidates — no enabled rule action references them (not proof of
     death: labels can be applied manually; the skill must verify annotation
     usage via the Rossum API before deleting)
  6. unused engines — no queue.json.engine points at them

Emits a markdown report. No JSON mode, no fuzzy checks (schema field
readers, engine field usage, rule trigger refs) — those are noisy; use
ripgrep for them if needed.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FIELD_CATS = {"datapoint", "multivalue", "tuple", "button"}
URL_ID = re.compile(r"/(\d+)/?$")


def url_id(url: object) -> int | None:
    if not isinstance(url, str):
        return None
    m = URL_ID.search(url)
    return int(m.group(1)) if m else None


def schema_field_ids(schema: dict) -> set[str]:
    ids: set[str] = set()
    def walk(n: object) -> None:
        if isinstance(n, dict):
            if n.get("category") in FIELD_CATS and isinstance(n.get("id"), str):
                ids.add(n["id"])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(schema.get("content", []))
    return ids


def is_scheduled(h: dict) -> bool:
    """Scheduled hooks (cron-triggered) legitimately run without a queue."""
    cron = (((h.get("config") or {}).get("schedule") or {}).get("cron") or "").strip()
    return bool(cron)


def load_all(path: Path) -> list[dict]:
    if not path.is_dir():
        return []
    out = []
    for p in sorted(path.glob("*.json")):
        d = json.loads(p.read_text())
        d["_path"] = p
        out.append(d)
    return out


def load_engines(path: Path) -> list[dict]:
    if not path.is_dir():
        return []
    out = []
    for d in sorted(path.iterdir()):
        ej = d / "engine.json"
        if ej.is_file():
            e = json.loads(ej.read_text())
            e["_path"] = ej
            out.append(e)
    return out


def main(env_dir: str) -> None:
    env = Path(env_dir).resolve()
    if not env.is_dir():
        print(f"error: {env} is not a directory", file=sys.stderr)
        sys.exit(2)

    hooks = load_all(env / "hooks")
    rules = load_all(env / "rules")
    labels = load_all(env / "labels")
    engines = load_engines(env / "engines")

    # Walk queues for orphan .py files and engine-reference tracking.
    orphan_py: list[tuple[str, Path]] = []
    queue_engines: set[int] = set()
    for qp in env.rglob("queue.json"):
        q = json.loads(qp.read_text())
        eid = url_id(q.get("engine"))
        if eid is not None:
            queue_engines.add(eid)
        sp = qp.parent / "schema.json"
        fdir = qp.parent / "formulas"
        if not (sp.is_file() and fdir.is_dir()):
            continue
        ids = schema_field_ids(json.loads(sp.read_text()))
        for py in sorted(fdir.glob("*.py")):
            if py.stem not in ids:
                orphan_py.append((q.get("name", "?"), py))

    orphan_hooks = [h for h in hooks if not h.get("queues") and not is_scheduled(h)]
    disabled_hooks = [h for h in hooks if h.get("active") is False]
    dead_rules = [r for r in rules if r.get("enabled") is False or not r.get("queues")]

    # Label references from enabled rule actions
    label_refs: set = set()
    for r in rules:
        for a in r.get("actions") or []:
            if a.get("enabled") is False:
                continue
            for k, v in (a.get("payload") or {}).items():
                if "label" not in k.lower():
                    continue
                for item in (v if isinstance(v, list) else [v]):
                    if isinstance(item, str):
                        label_refs.add(item)
                        uid = url_id(item)
                        if uid is not None:
                            label_refs.add(uid)
    unused_labels = [l for l in labels if l.get("id") not in label_refs
                     and (l.get("url") or "") not in label_refs]

    unused_engines = [e for e in engines if e.get("id") not in queue_engines]

    # Render
    print(f"# Rossum Dead Code Report — `{env}`\n")
    def section(title: str, items: list, fmt) -> None:
        print(f"## {title} ({len(items)})\n")
        for it in items:
            print("- " + fmt(it))
        print()

    section("Orphan formula .py files", orphan_py,
            lambda t: f"queue **{t[0]}** — `{t[1]}` (no schema field `{t[1].stem}`) → **delete**")
    section("Hooks with no queue attachment (scheduled hooks excluded)", orphan_hooks,
            lambda h: f"**{h.get('name')}** (id={h.get('id')}) `{h['_path']}` → **delete**")
    section("Disabled hooks", disabled_hooks,
            lambda h: f"**{h.get('name')}** (id={h.get('id')}) `{h['_path']}` → **investigate**")
    section("Dead rules", dead_rules,
            lambda r: f"**{r.get('name')}** (id={r.get('id')}) `{r['_path']}` — "
                      f"{'disabled' if r.get('enabled') is False else 'queues: []'} → **delete**")
    section("Label candidates — no rule references (verify annotation usage before deleting)", unused_labels,
            lambda l: f"**{l.get('name')}** (id={l.get('id')}) `{l['_path']}` → "
                      f"**verify with `rossum_search_annotations` `labels={l.get('id')}`, "
                      f"delete only if 0 annotations use it**")
    section("Unused engines", unused_engines,
            lambda e: f"**{e.get('name')}** (id={e.get('id')}) `{e['_path']}` → **delete**")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: detect.py <env_dir>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1])
