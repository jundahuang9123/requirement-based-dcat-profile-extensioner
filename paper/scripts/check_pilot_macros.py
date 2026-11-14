"""Independent check of paper/results/pilot-numbers.tex against the numbers-only input files.

Usage: python paper/scripts/check_pilot_macros.py paper   (prints the number of values checked and every mismatch)
"""
import re
import sys
from pathlib import Path

paper = Path(sys.argv[1])
macros = dict(re.findall(r"^\\@namedef\{(pilot(?:kind)?@[^}]+)\}\{(.*)\}$", (paper / "results/pilot-numbers.tex").read_text(), re.M))
expected = {}
cols = None
for f in ("inputs/pilot-runs-2026-11-13.md", "inputs/dev-runs-2026-11-14-run3.md"):
    for line in (paper / f).read_text().splitlines():
        if line.startswith("| case"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            continue
        if not line.startswith("| JRC") and not line.startswith("| Stat"):
            continue
        v = dict(zip(cols, [c.strip() for c in line.strip("|").split("|")]))
        case = {"JRC": "jrc", "Stat": "stat"}[v["case"]]
        run = "rules" if "rules" in v["provider"] else "run" + v["provider"][-1]
        key = f"pilot@{case}@{run}@"
        calls, cached = v["calls (cached)"].replace(")", "").split(" (")
        tin, tout = [t.strip().replace(",", "{,}") for t in v["in / out tokens"].split("/")]
        expected.update({key + "wall": v["wall s"], key + "calls": calls, key + "cached": cached,
                         key + "intok": tin, key + "outtok": tout, key + "addressed": v["addressed"],
                         key + "partial": v["partial"], key + "pending": v["pending review"],
                         key + "unaddressed": v["unaddressed"], key + "included": v["included"],
                         key + "rejected": v["rejected"], key + "needsreview": v["needs review"],
                         key + "extrate": v["ext. rate"], key + "covered": v.get("covered by base", "0")})
        conf = v["conformance"]
        expected[key + "verdict"] = conf.split(" (")[0]
        for word in ("added", "tightened", "loosened"):
            m = re.search(r"(\d+) " + word, conf)
            expected[key + word] = m.group(1) if m else ("0" if word == "loosened" else "")
        m = re.search(r"(\d+) warning", conf)
        expected[key + "warnings"] = m.group(1) if m else "0"
    for line in (paper / f).read_text().splitlines():
        m = re.match(r"- (JRC|Stat) run (\d): (.+)\.$", line.strip())
        if m:
            case = {"JRC": "jrc", "Stat": "stat"}[m.group(1)]
            parts = dict((p.rsplit(" ", 1)[0], p.rsplit(" ", 1)[1]) for p in m.group(3).split(", "))
            for name, field in (("reuse", "reuse"), ("refine", "refine"), ("mint property", "mintproperty"), ("mint class", "mintclass")):
                expected[f"pilotkind@{case}@run{m.group(2)}@{field}"] = parts.get(name, "0")
# Blind pilots (paper/inputs/pilot-runs-2026-11-14-blind.md), parsed independently of make_pilot_tables.py.
macros.update(dict(re.findall(r"^\\@namedef\{(pilotb(?:kind)?@[^}]+)\}\{(.*)\}$", (paper / "results/pilot-numbers.tex").read_text(), re.M)))
bcols = None
for line in (paper / "inputs/pilot-runs-2026-11-14-blind.md").read_text().splitlines():
    if line.startswith("| case"):
        bcols = [c.strip() for c in line.strip("|").split("|")]
        continue
    if bcols and (line.startswith("| JRC") or line.startswith("| Stat")):
        v = dict(zip(bcols, [c.strip() for c in line.strip("|").split("|")]))
        key = "pilotb@{}@{}@".format({"JRC": "jrc", "Stat": "stat"}[v["case"]], "rules" if "rules" in v["provider"] else "llm")
        calls, cached = v["calls (cached)"].replace(")", "").split(" (")
        tin, tout = [x.strip().replace(",", "{,}") for x in v["in / out tokens"].split("/")]
        ext, extp = [x.strip() for x in v["ext. rate (included / proposed)"].split("/")]
        expected.update({key + "wall": v["wall s"], key + "calls": calls, key + "cached": cached, key + "judge": v["judge calls"],
                         key + "intok": tin, key + "outtok": tout, key + "covered": v["covered by base"],
                         key + "addressed": v["addressed"], key + "partial": v["partial"], key + "pending": v["pending review"],
                         key + "unaddressed": v["unaddressed"], key + "included": v["included"], key + "auto": v["auto accepted"],
                         key + "needsreview": v["needs review"], key + "rejectedhuman": v["rejected by human"],
                         key + "withdrawn": v["withdrawn by machine"], key + "repaircalls": v["repair calls"],
                         key + "repairedincluded": v["repaired and included"], key + "extrate": ext, key + "extrateprop": extp})
        conf = v["conformance"]
        expected[key + "verdict"] = conf.split(" (")[0]
        for word, field in (("added", "added"), ("tightened", "tightened"), ("loosened", "loosened"), ("failing", "failing"), ("warning", "warnings")):
            expected[key + field] = re.search(r"(\d+) " + word, conf).group(1)
    m = re.match(r"- (JRC|Stat), (rules \(mock\)|gpt-oss-120b): (.+)\.$", line.strip())
    if m:
        parts = dict((x.rsplit(" ", 1)[0], x.rsplit(" ", 1)[1]) for x in m.group(3).split(", "))
        base = "pilotbkind@{}@{}@".format({"JRC": "jrc", "Stat": "stat"}[m.group(1)], "rules" if "rules" in m.group(2) else "llm")
        for name, field in (("reuse", "reuse"), ("refine", "refine"), ("mint property", "mintproperty"), ("mint class", "mintclass")):
            expected[base + field] = parts.get(name, "0")
bad = [(k, expected[k], macros.get(k)) for k in sorted(expected) if macros.get(k) != expected[k]]
extra = sorted(set(macros) - set(expected))
print(f"checked {len(expected)} values; mismatches {len(bad)}; macros without a source {len(extra)}")
for b in bad:
    print("MISMATCH", b)
for e in extra:
    print("EXTRA", e, macros[e])
