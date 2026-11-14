#!/usr/bin/env python3
"""Turn an RQ1 reference set (requirements-benchmark-references, reference-sets-v3/<case>.json)
into a BLIND atom set for this tool (the A-gold input of the RQ2 plan), plus an evaluator map.

The atom set holds only what the model may see:
- an opaque id (A-001, ...), never the reference id ("JRC-6.2" names the case, "Req-17.1" reuses
  the source's numbering);
- the standard-form statement;
- the subject (standard_form.resource);
- the modality.

It has no source reference, no case name, no benchmark id, and no evaluator fields (relation to the
base, reuse rules, anchor quotes, evidence labels, overlaps): they would put the answer into the
input.

The evaluator map (<out>.evalmap.json) joins each opaque id back to the case, the original id, the
source locator and the modality mapping. It is for scoring only: never give it to the tool. By
default only the atoms scored by default are taken.

Both files are local files for a run; do not commit reference-derived files to this repository.

Modality: the reference sets record the SOURCE's kind of statement, not must/should/may. The mapping
below is conservative; everything else becomes "unspecified" (strongest licensed obligation:
recommended). Where the reference document is the published profile itself (StatDCAT-AP,
HealthDCAT-AP), the mapped modality repeats that profile's obligation levels; --modality unspecified
withholds it (a blinder condition). The choice is recorded in the map.

Usage: python scripts/import_rq1_reference.py <case.json> <out.yaml> [--all] [--base dcat-ap-1.1]
                                              [--modality map|unspecified]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

MODALITY = {
    "explicit_requirement": "must",
    "mandatory": "must",
    "recommendation": "should",
    "recommended": "should",
    "optional": "may",
}
BASES = {f"DCAT-AP {r}": f"dcat-ap-{r}" for r in ("1.1", "1.2", "1.2.1", "2.0.0", "2.0.1", "2.1.0", "2.1.1", "3.0.0", "3.0.1")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("reference", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--all", action="store_true", help="take every content atom, not only those scored by default")
    parser.add_argument("--base", help="base profile id (default: from the reference set's 'base' field)")
    parser.add_argument("--modality", choices=["map", "unspecified"], default="map")
    args = parser.parse_args(argv)

    data = json.loads(args.reference.read_text(encoding="utf-8"))
    case = str(data.get("case") or args.reference.stem)
    base = args.base or BASES.get(str(data.get("base")).strip())
    chosen = [atom for atom in data["atoms"]
              if (atom.get("scored_by_default") if not args.all else atom.get("stratum") == "content")]
    # Opaque ids in an order that does not follow the reference numbering.
    chosen.sort(key=lambda atom: hashlib.sha256(f"{case}|{atom['id']}".encode()).hexdigest())
    atoms, evalmap = [], {}
    for number, atom in enumerate(chosen, start=1):
        opaque = f"A-{number:03d}"
        form = atom.get("standard_form") or {}
        subject = str(form.get("resource") or "dataset").split(" or ")[0].strip().lower() or "dataset"
        raw = str(atom.get("modality") or "").lower()
        mapped = MODALITY.get(raw, "unspecified") if args.modality == "map" else "unspecified"
        atoms.append({"id": opaque, "statement": atom["statement"], "subject": subject, "modality": mapped})
        evalmap[opaque] = {"case": case, "original_id": atom["id"], "source_locator": str(atom.get("source_locator") or ""),
                           "reference_document": str(data.get("reference_document") or ""), "raw_modality": raw,
                           "modality": mapped, "modality_mode": args.modality,
                           "standard_form_resource": str(form.get("resource") or "")}
    out = {
        "title": "Requirement atoms",
        "description": "Imported by scripts/import_rq1_reference.py (blind: opaque ids, no source references).",
        "base_profile_ids": [base] if base else [],
        "atoms": atoms,
    }
    args.out.write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")
    map_path = args.out.with_suffix(".evalmap.json")
    map_path.write_text(json.dumps({"case": case, "base": base, "atoms": evalmap}, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"{len(atoms)} atoms -> {args.out} (base {base}); evaluator map -> {map_path} (keep it away from the tool)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
