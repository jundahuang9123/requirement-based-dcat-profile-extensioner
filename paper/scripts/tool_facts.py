#!/usr/bin/env python3
"""Print the tool facts the RQ2 paper quotes (vocabulary index, base profiles), read-only, no model calls.

Usage (repository root, backend installed): python paper/scripts/tool_facts.py > paper/inputs/tool-facts.txt
Every count about the tool in the paper comes from this script's output, recorded in paper/inputs/tool-facts.txt.
"""
from __future__ import annotations

import collections
import json
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from profile_extensioner.knowledge import list_base_profiles, load_base_profile, load_knowledge_base  # noqa: E402
from profile_extensioner.knowledge.vocab_index import VocabularyIndex  # noqa: E402

DATA = ROOT / "backend" / "profile_extensioner" / "data"


def main() -> int:
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    print(f"# tool facts at commit {commit}")

    manifest = json.loads((DATA / "vocab" / "MANIFEST.json").read_text(encoding="utf-8"))
    entries = manifest.get("vocabularies", manifest) if isinstance(manifest, dict) else manifest
    if isinstance(entries, dict):
        entries = list(entries.values())
    print(f"vendored vocabularies: {len(entries)}")
    print("vocabulary prefixes: " + ", ".join(sorted(str(e.get('prefix', '?')) for e in entries)))
    print(f"vendored triples (MANIFEST): {sum(int(e.get('triples', 0)) for e in entries)}")

    index = VocabularyIndex.load(DATA / "vocab")
    kinds = collections.Counter(t.kind for t in index.terms())
    print(f"index terms without base: {len(index)} ({kinds['class']} classes, {kinds['property']} properties)")
    for info in list_base_profiles():
        kb = load_knowledge_base(info.id, profile_namespace="https://example.org/ns#", profile_prefix="ex")
        k = collections.Counter(t.kind for t in kb.vocab.terms())
        print(f"index terms with base {info.id}: {len(kb.vocab)} ({k['class']} classes, {k['property']} properties)")

    for info in list_base_profiles():
        base = load_base_profile(info.id)
        obligations = collections.Counter(base.obligation(*key) for key in base.index.elements)
        listed = yaml.safe_load((DATA / "base-profiles" / info.id / "obligations.yaml").read_text(encoding="utf-8"))
        rows = collections.Counter(level for entry in listed["classes"].values()
                                   for level in (entry.get("properties") or {}).values())
        print(f"base {info.id}: {info.class_count} target classes, {info.element_count} (class, property) elements; "
              f"obligations of the elements {dict(sorted(obligations.items()))}; "
              f"obligation table rows {dict(sorted(rows.items()))}; unhandled SHACL constructs {len(base.index.unhandled)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
