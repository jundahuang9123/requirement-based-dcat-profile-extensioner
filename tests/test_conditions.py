"""Experiment conditions (ablations): PipelineConfig.verify and require_human_signoff do what they say."""
from pathlib import Path

from profile_extensioner.contracts import PipelineConfig, Project
from profile_extensioner.engine.intake import parse_atom_set
from profile_extensioner.engine.pipeline import Pipeline
from profile_extensioner.llm.registry import Credentials
from profile_extensioner.store.blackboard import Store

DEMO = Path(__file__).resolve().parents[1] / "examples" / "materials-testing-lab" / "atoms.yaml"
SYMBOLIC = {"V1", "V2", "V3", "V4", "V5", "D1", "D2", "D3", "T1"}


def run(**config):
    store = Store()
    store.save_project(Project(id="p", name="Lab", profile_namespace="https://example.org/lab#", profile_prefix="lab",
                               config=PipelineConfig(**config)))
    store.replace_atoms("p", parse_atom_set(DEMO.read_text(encoding="utf-8")).atoms)
    pipeline = Pipeline(store, Credentials(), "p")
    pipeline.run_all()
    return pipeline


def live(pipe):
    return [c for c in pipe.changes() if c.decision.status != "superseded"]


def test_verification_off_runs_only_the_guard_and_says_so():
    pipe = run(verify=False, attribution_check=False)
    checks = {r.check for c in live(pipe) for r in c.verification}
    assert not checks & SYMBOLIC and "V0" in checks
    assert not any("all checks passed" in c.decision.note for c in live(pipe))
    assert any("switched off" in c.decision.note for c in live(pipe) if c.decision.status == "auto_accepted")
    assert not any("(Check B1:" in a.reason for a in pipe.store.list_assessments("p"))
    report = pipe.store.get_conformance("p")
    assert {c.id for c in report.checks} >= {"C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"}   # the outcome is still measured


def test_verification_off_keeps_the_judge_when_it_is_on():
    pipe = run(verify=False, attribution_check=True)
    assert any(r.check == "T2" for c in live(pipe) for r in c.verification)


def test_the_ablation_changes_a_decision_a_symbolic_check_would_block():
    """An invented term: full verification sends it to a person (V1); the ablation does not check it."""
    from profile_extensioner.contracts import CoverageLink, Facets, ProfileChange

    outcomes = {}
    for verify in (True, False):
        store = Store()
        store.save_project(Project(id="p", name="Lab", profile_namespace="https://example.org/lab#", profile_prefix="lab",
                                   config=PipelineConfig(verify=verify, attribution_check=False)))
        store.replace_atoms("p", parse_atom_set(DEMO.read_text(encoding="utf-8")).atoms[:1])
        pipe = Pipeline(store, Credentials(), "p")
        atom_id = store.list_atoms("p")[0].id
        store.save_change("p", ProfileChange(
            id="invented", kind="reuse_property", target_class="http://www.w3.org/ns/dcat#Dataset",
            path="http://example.org/not-a-vocabulary#madeUp", facets=Facets(obligation="recommended"),
            covers=[CoverageLink(atom_id=atom_id, reason="r", evidence_quote="x")], confidence=0.9))
        pipe.run_verify()
        outcomes[verify] = store.get_change("p", "invented").decision.status
    assert outcomes[True] == "needs_review" and outcomes[False] == "auto_accepted"


def test_release_without_a_human_only_when_the_condition_says_so():
    assert run().store.get_project("p").signoff is None                       # default: a person signs off
    pipe = run(require_human_signoff=False)
    project = pipe.store.get_project("p")
    if pipe.store.get_conformance("p").verdict != "non_conformant":
        assert project.signoff is not None and project.signoff.by == "rule:auto-release"
        assert project.stage_states["review"] == "skipped"
        readme = next(a for a in pipe.store.list_artifacts("p") if a.name == "README.md").content
        assert "Released automatically, without human review" in readme
        some = next(c for c in live(pipe) if c.included)
        pipe.decide(some.id, "rejected", "rev")                                # a later decision withdraws it
        assert pipe.store.get_project("p").signoff is None
