#!/usr/bin/env python3
"""Run one imported atom set end to end and write a summary.

Usage:
  run_reference_case.py <case> <mock|kiconnect> [--model M] [--dir D] [--tag T] [--store PATH]
                        [--effort low|medium|high] [--max-output-tokens N] [--replay project|global|off] [--replace]

  <dir>/<case>.atoms.yaml must exist (make it with scripts/import_rq1_reference.py, outside this repository:
  imported benchmark atoms are reference-derived). The summary goes to <dir>/<project id>.txt.

Benchmark hygiene (leakage rule): nothing that names the case or the published profile reaches a prompt.
The project title and namespace are neutral ("Extension under test", https://example.org/ext#); the atoms'
source references are kept on the workbench but never printed in prompts (engine/prompts.py). Each run is
an independent project: the replay cache is project-scoped by default, so answers of earlier runs are not
replayed (--replay global reuses them on purpose; --replay off disables replay inside the run too).

kiconnect needs RBDPE_LLM_API_KEY (the session proxy injects the real key; set it to proxy-injected).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from profile_extensioner.contracts import LLMSettings, PipelineConfig, Project  # noqa: E402
from profile_extensioner.engine.intake import parse_atom_set  # noqa: E402
from profile_extensioner.engine.pipeline import Pipeline  # noqa: E402
from profile_extensioner.engine.verbalise import verbalise_change  # noqa: E402
from profile_extensioner.llm.registry import Credentials  # noqa: E402
from profile_extensioner.store.blackboard import Store  # noqa: E402

KICONNECT = "https://chat.kiconnect.nrw/api/v1"
NEUTRAL_TITLE = "Extension under test"
NEUTRAL_NAMESPACE = "https://example.org/ext#"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("case")
    parser.add_argument("provider", choices=["mock", "kiconnect"])
    parser.add_argument("--model", default="inferenz-gpt-oss-120b")
    parser.add_argument("--dir", type=Path, default=Path.cwd())
    parser.add_argument("--tag", default="")
    parser.add_argument("--store", default="/tmp/rbdpe-ws/blackboard.sqlite3")
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--max-output-tokens", type=int, default=8000)
    parser.add_argument("--replay", default="project", choices=["project", "global", "off"])
    parser.add_argument("--replace", action="store_true", help="delete an earlier project with the same id first")
    # experiment conditions (ablations); the defaults are the full pipeline
    parser.add_argument("--no-retrieval", action="store_true", help="no candidate terms for the proposer")
    parser.add_argument("--no-verify", action="store_true", help="no symbolic checks (a well-formedness guard stays)")
    parser.add_argument("--no-judge", action="store_true", help="no T2 attribution judge")
    parser.add_argument("--repair-rounds", type=int, default=3)
    parser.add_argument("--votes", type=int, default=1)
    parser.add_argument("--top-k", type=int, default=8)
    args = parser.parse_args(argv)

    atoms = parse_atom_set((args.dir / f"{args.case}.atoms.yaml").read_text(encoding="utf-8"))
    model = None if args.provider == "mock" else args.model
    pid = f"{args.case}-{args.provider}-{model or 'rules'}" + (f"-{args.tag}" if args.tag else "")
    pid = pid.replace("/", "_")
    store = Store(args.store)
    if store.get_project(pid) is not None:
        if not args.replace:
            print(f"project {pid} exists in {args.store}; use another --tag or --replace", file=sys.stderr)
            return 2
        store.delete_project(pid)
    llm = LLMSettings(provider="mock") if args.provider == "mock" else LLMSettings(
        provider="openai-compatible", model=model, base_url=KICONNECT, effort=args.effort,
        max_output_tokens=args.max_output_tokens)
    store.save_project(Project(
        id=pid, name=NEUTRAL_TITLE, base_profile_id=atoms.base_profile_ids[0], profile_title=NEUTRAL_TITLE,
        profile_namespace=NEUTRAL_NAMESPACE, profile_prefix="ext", llm=llm,
        config=PipelineConfig(max_parallel_calls=1, replay_cache=args.replay, retrieval=not args.no_retrieval,
                              verify=not args.no_verify, attribution_check=not args.no_judge,
                              repair_rounds=args.repair_rounds, votes=args.votes, top_k=args.top_k, blind=True)))
    store.replace_atoms(pid, atoms.atoms)
    pipeline = Pipeline(store, Credentials(), pid)
    started = time.time()
    pipeline.run_all()
    took = round(time.time() - started)

    lines = [f"# {pid}: {took} s", "",
             f"SETTINGS base={pipeline.project.base_profile_id} dcat={pipeline.kb.dcat.id} provider={llm.provider} "
             f"model={model or '-'} effort={llm.effort} max_output_tokens={llm.max_output_tokens} replay={args.replay}",
             f"CONFIG {pipeline.project.config.model_dump_json()}", ""]
    for assessment in store.list_assessments(pid):
        lines.append(f"{assessment.atom_id:9s} {assessment.disposition:16s} {assessment.reason[:220]}")
    lines.append("")
    for change in pipeline.changes():
        if change.decision.status == "superseded":
            continue
        failed = [f"{r.check}:{r.severity[0]}" for r in change.verification if not r.passed]
        lines.append(f"{change.decision.status:13s} {','.join(change.atom_ids):16s} {verbalise_change(change, pipeline.kb)} "
                     f"{failed} r{change.provenance.repair_round}")
    report = store.get_conformance(pid)
    lines += ["", f"CONFORMANCE {report.verdict}: {report.summary}"]
    lines += [f"  FAIL {check.id} {check.message}" for check in report.checks if not check.passed]
    calls = store.list_llm_calls(pid)
    lines.append(f"METRICS {json.dumps(pipeline.metrics())}")
    lines.append(f"CALLS {len(calls)} " + json.dumps({s: sum(1 for c in calls if c.status == s) for s in {c.status for c in calls}})
                 + f" replayed_from_other_projects={sum(1 for c in calls if c.cached and c.replayed_from_project != pid)}")
    leaks = leak_scan(store.list_llm_calls(pid, limit=None), args.dir / f"{args.case}.atoms.evalmap.json", atoms)
    lines.append("LEAKCHECK " + ("clean" if not leaks else "LEAK " + json.dumps(leaks)))
    (args.dir / f"{pid}.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 3 if leaks else 0


PROFILE_CANARIES = ("StatDCAT", "GeoDCAT", "HealthDCAT", "mobilityDCAT", "DCAT-AP-JRC", "NAPCORE", "BRegDCAT")


def leak_scan(calls, evalmap_path: Path, atoms) -> dict[str, int]:
    """Count prompts that contain anything identifying the case or its published profile: the case name, the
    original reference ids, the source locators, the reference document, published-profile names. A canary that
    also occurs in an atom statement is a property of the input, not a leak of the tool, and is not counted."""
    canaries: set[str] = set(PROFILE_CANARIES)
    if evalmap_path.exists():
        data = json.loads(evalmap_path.read_text(encoding="utf-8"))
        canaries.add(str(data.get("case") or ""))
        for entry in (data.get("atoms") or {}).values():
            canaries |= {entry.get("original_id", ""), entry.get("source_locator", ""), entry.get("reference_document", "")}
    statements = " ".join(atom.statement for atom in atoms.atoms).lower()
    canaries = {c for c in canaries if c and len(c) >= 4 and c.lower() not in statements}
    hits: dict[str, int] = {}
    for call in calls:
        text = f"{call.system_prompt}\n{call.user_prompt}".lower()
        for canary in canaries:
            if canary.lower() in text:
                hits[canary] = hits.get(canary, 0) + 1
    return hits


if __name__ == "__main__":
    sys.exit(main())
