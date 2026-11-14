"""Run one imported RQ1 reference case through the whole pipeline and write a summary.

Usage: run_reference_case.py <case> <mock|kiconnect> [model] [dir] [tag]
  <dir>/<case>.atoms.yaml must exist (make it with scripts/import_rq1_reference.py);
  the summary is written to <dir>/<project id>.txt. Blackboard: /tmp/rbdpe-ws/blackboard.sqlite3.
  kiconnect needs RBDPE_LLM_API_KEY (the session proxy injects the real key; use proxy-injected).
  The atom files and summaries are reference-derived: keep them out of the repository.
"""
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

case, provider = sys.argv[1], sys.argv[2]
model = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
out = Path(sys.argv[4]) if len(sys.argv) > 4 else Path.cwd()
tag = f"-{sys.argv[5]}" if len(sys.argv) > 5 else ""
atoms = parse_atom_set((out / f"{case}.atoms.yaml").read_text())
pid = f"{case}-{provider}-{model or 'rules'}{tag}".replace("/", "_")
store = Store("/tmp/rbdpe-ws/blackboard.sqlite3")
llm = LLMSettings(provider="mock") if provider == "mock" else LLMSettings(
    provider="openai-compatible", model=model, base_url="https://chat.kiconnect.nrw/api/v1", max_output_tokens=8000)
store.delete_project(pid)
store.save_project(Project(id=pid, name=f"{case} ({provider} {model or 'rules'})", base_profile_id=atoms.base_profile_ids[0],
    profile_title=f"{case} extension", profile_namespace=f"https://example.org/{case}#", profile_prefix="ext",
    llm=llm, config=PipelineConfig(max_parallel_calls=1)))
store.replace_atoms(pid, atoms.atoms)
p = Pipeline(store, Credentials(), pid)
t = time.time()
p.run_all()
took = round(time.time() - t)
lines = [f"# {pid}: {took} s", ""]
for a in store.list_assessments(pid):
    lines.append(f"{a.atom_id:9s} {a.disposition:16s} {a.reason[:220]}")
lines.append("")
for c in p.changes():
    if c.decision.status == "superseded":
        continue
    failed = [f"{r.check}:{r.severity[0]}" for r in c.verification if not r.passed]
    lines.append(f"{c.decision.status:13s} {','.join(c.atom_ids):16s} {verbalise_change(c, p.kb)} {failed} r{c.provenance.repair_round}")
r = store.get_conformance(pid)
lines += ["", f"CONFORMANCE {r.verdict}: {r.summary}"] + [f"  FAIL {ch.id} {ch.message}" for ch in r.checks if not ch.passed]
calls = store.list_llm_calls(pid)
lines.append(f"METRICS {json.dumps(p.metrics())}")
lines.append(f"CALLS {len(calls)} " + json.dumps({s: sum(1 for c in calls if c.status == s) for s in {c.status for c in calls}}))
(out / f"{pid}.txt").write_text("\n".join(lines))
print("\n".join(lines))
