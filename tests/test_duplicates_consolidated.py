"""Proposed regression tests for C6 (offline: default mock provider, in-memory store, no network).

Duplicates for one (class, property) must be merged by consolidation, never handed to the repairer; repair rounds
start from fresh failures; a merged change is judged (T2) with all its atoms; an unmergeable pair or a machine
duplicate of a human decision goes to a person."""
import pytest

from profile_extensioner.contracts import Atom, PipelineConfig, Project
from profile_extensioner.engine.pipeline import Pipeline
from profile_extensioner.engine.schemas import RepairOut
from profile_extensioner.llm import mock as mock_module
from profile_extensioner.llm.registry import Credentials
from profile_extensioner.store.blackboard import Store

EXT = "https://example.org/ext#"
DATASET = "http://www.w3.org/ns/dcat#Dataset"
AUTHOR = [  # three memoryless proposals that all mint ext:author on dcat:Dataset
    Atom(id="a-1", statement="A dataset should name the author.", subject="dataset", modality="should"),
    Atom(id="a-2", statement="Every dataset must name the author.", subject="dataset", modality="must"),
    Atom(id="a-3", statement="A dataset may name the author.", subject="dataset", modality="may"),
]
DUPLICATE_MESSAGE = "there must be one element per class and property"


def build(atoms, pid="p", **config):
    store = Store()
    store.save_project(Project(id=pid, name="Extension under test", profile_title="Extension under test",
                               profile_namespace=EXT, profile_prefix="ext",
                               config=PipelineConfig(max_parallel_calls=1, **config)))
    store.replace_atoms(pid, atoms)
    return Pipeline(store, Credentials(), pid)


def live(pipe):
    return [c for c in pipe.changes() if c.decision.status not in ("superseded", "rejected")]


def calls(pipe, purpose):
    return [c for c in pipe.store.list_llm_calls(pipe.pid) if c.purpose == purpose]


@pytest.fixture()
def withdraw_duplicates(monkeypatch):
    """A repairer that withdraws a change as soon as it is told the change is a duplicate (what gpt-oss-120b
    did in the KI:connect pilots)."""
    original = mock_module.MockProvider._repair

    def repair(self, context):
        if any((f.get("details") or {}).get("problem") == "duplicate_element" for f in context["failures"]):
            return RepairOut(action="withdraw", note="duplicate of another change", change=None)
        return original(self, context)
    monkeypatch.setattr(mock_module.MockProvider, "_repair", repair)


def test_duplicates_are_merged_by_consolidation_not_repaired():
    pipe = build(AUTHOR)
    pipe.run_all()
    assert not any(DUPLICATE_MESSAGE in c.user_prompt for c in calls(pipe, "repair"))
    [author] = [c for c in live(pipe) if c.path == EXT + "author"]
    assert author.target_class == DATASET and set(author.atom_ids) == {"a-1", "a-2", "a-3"}
    assert author.facets.obligation == "mandatory" and len(author.merged_from) == 2
    assert not any(r.details.get("problem") == "duplicate_element" for r in author.verification if not r.passed)


def test_a_repairer_that_withdraws_duplicates_never_sees_them(withdraw_duplicates):
    pipe = build(AUTHOR)
    pipe.run_all()
    assert pipe.metrics()["withdrawn_by_machine"] == 0 and pipe.metrics()["rejected_by_human"] == 0
    assert all(state != "unaddressed" for state in pipe.coverage().values())


def test_the_merged_change_is_judged_with_all_its_atoms():
    pipe = build(AUTHOR, auto_accept_min_confidence=0.4)     # the mock mints with confidence 0.45
    pipe.run_all()
    [author] = [c for c in live(pipe) if c.path == EXT + "author"]
    assert [r for r in author.verification if r.check == "T2"], "decided without the attribution judge"
    judged = [c for c in calls(pipe, "judge") if c.subject_id == author.id]
    assert judged and all(atom.statement in judged[-1].user_prompt for atom in AUTHOR)


def test_unmergeable_duplicates_go_to_a_person_without_repair(monkeypatch):
    original = mock_module.MockProvider._propose
    ranges = {"d-1": "xsd:date", "d-2": "xsd:string"}

    def propose(self, context):
        out = original(self, context)
        for change in out.changes:
            change.kind, change.path, change.label, change.definition = "mint_property", "NEW:review", "review", "The review."
            change.range, change.range_kind, change.node_kind = ranges[context["atom"]["id"]], "datatype", "Literal"
            change.reason_no_reuse = change.reason_no_reuse or "No retrieved term carries it."
        return out
    monkeypatch.setattr(mock_module.MockProvider, "_propose", propose)
    pipe = build([Atom(id="d-1", statement="A dataset should state the date of its review.", subject="dataset", modality="should"),
                  Atom(id="d-2", statement="A dataset should state its review.", subject="dataset", modality="should")])
    pipe.run_all()
    assert not calls(pipe, "repair")
    [conflict] = pipe.store.list_conflicts(pipe.pid)
    members = [pipe.store.get_change(pipe.pid, cid) for cid in conflict.change_ids]
    assert all(m.decision.status == "needs_review" and m.decision.decided_by == "rule:consolidate"
               and m.decision.note.startswith("conflict") for m in members)


def test_a_repair_round_starts_from_fresh_failures(withdraw_duplicates):
    pipe = build(AUTHOR[:2])
    pipe.run_intake(); pipe.run_retrieve(); pipe.run_propose(); pipe.run_verify()
    first, second = live(pipe)
    assert any(r.details.get("problem") == "duplicate_element" for r in first.verification)
    second.decision = second.decision.model_copy(update={"status": "rejected", "decided_by": "llm:mock/rules-v1"})
    pipe.store.save_change(pipe.pid, second)            # the partner was withdrawn in an earlier round
    pipe.run_repair()
    assert pipe.store.get_change(pipe.pid, first.id).decision.status != "rejected"
    assert not any(DUPLICATE_MESSAGE in c.user_prompt for c in calls(pipe, "repair"))


def test_a_machine_duplicate_of_a_human_decision_reaches_the_human(withdraw_duplicates):
    pipe = build(AUTHOR[:2])
    pipe.run_intake(); pipe.run_retrieve(); pipe.run_propose(["a-1"]); pipe.run_verify()
    [mine] = live(pipe)
    pipe.decide(mine.id, "accepted", "rev")
    pipe.run_propose(["a-2"])
    pipe.run_all(from_stage="verify")
    [other] = [c for c in pipe.changes() if c.atom_ids == ["a-2"] and c.decision.status != "superseded"]
    assert other.decision.status == "needs_review" and pipe.coverage()["a-2"] == "pending_review"
    with pytest.raises(ValueError):
        pipe.sign_off("rev")
