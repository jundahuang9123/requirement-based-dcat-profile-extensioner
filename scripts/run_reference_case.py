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
        config=PipelineConfig(max_parallel_calls=1, replay_cache=args.replay)))
    store.replace_atoms(pid, atoms.atoms)
    pipeline = Pipeline(store, Credentials(), pid)
    started = time.time()
    pipeline.run_all()
    took = round(time.time() - started)

    lines = [f"# {pid}: {took} s", "",
             f"SETTINGS base={pipeline.project.base_profile_id} dcat={pipeline.kb.dcat.id} provider={llm.provider} "
             f"model={model or '-'} effort={llm.effort} max_output_tokens={llm.max_output_tokens} replay={args.replay}", ""]
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
    (args.dir / f"{pid}.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
