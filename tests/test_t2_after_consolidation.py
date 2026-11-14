"""Regression tests for C5: the T2 attribution verdict must hold for what is auto-accepted after consolidation.

Offline only: the stock mock provider, or MockProvider subclasses that script one task.
"""
import os
import tempfile

import pytest

os.environ.setdefault("RBDPE_WORKSPACE", tempfile.mkdtemp(prefix="rbdpe-test-"))

from profile_extensioner.contracts import (  # noqa: E402
    CheckResult, CoverageLink, Decision, MintJustification, PipelineConfig, ProfileChange, Project, Provenance,
)
from profile_extensioner.engine.intake import parse_atom_set  # noqa: E402
from profile_extensioner.engine.pipeline import Pipeline  # noqa: E402
from profile_extensioner.engine.schemas import AttributionOut  # noqa: E402
from profile_extensioner.llm.base import LLMError  # noqa: E402
from profile_extensioner.llm.client import LLMClient  # noqa: E402
from profile_extensioner.llm.mock import MockProvider  # noqa: E402
from profile_extensioner.llm.registry import Credentials  # noqa: E402
from profile_extensioner.store.blackboard import Store  # noqa: E402

NS = "https://example.org/x#"
DCAT, DCT = "http://www.w3.org/ns/dcat#", "http://purl.org/dc/terms/"
HEADER = "title: c5 (synthetic)\nbenchmark_id: c5\nbase_profile_ids: [dcat-ap-3.0.1]\natoms:\n"


def atom(aid, statement, subject):
    return (f"  - id: {aid}\n    statement: {statement}\n    subject: {subject}\n    modality: must\n"
            f"    source_reference: {{document: synthetic, locator: \"{aid}\"}}\n")


def make(atoms_yaml, config=None, provider=None):
    store = Store()
    store.save_project(Project(id="p1", name="C5", profile_namespace=NS, profile_prefix="x",
                               config=config or PipelineConfig()))
    store.replace_atoms("p1", parse_atom_set(HEADER + atoms_yaml).atoms)
    pipe = Pipeline(store, Credentials(), "p1")
    if provider is not None:
        pipe._llm = LLMClient(provider, pipe.project.llm, store=store, project_id="p1")
    return pipe


def unjudged_auto_accepted(pipe):
    return [c.id for c in pipe.changes() if c.decision.status == "auto_accepted"
            and not any(r.check == "T2" and r.passed for r in c.verification)]


def mint_class(cid, atom_id, quote, confidence, decided_by="llm:mock/rules-v1", status="proposed"):
    return ProfileChange(
        id=cid, kind="mint_class", target_class=NS + "TensileSpecimenBatch", label="Tensile specimen batch",
        definition="A batch of tensile specimens tested together.",
        mint=MintJustification(reason_no_reuse="No retrieved class denotes a specimen batch."),
        covers=[CoverageLink(atom_id=atom_id, reason="The atom asks for this kind of resource.", evidence_quote=quote)],
        confidence=confidence, provenance=Provenance(author_type="llm", author="llm:mock/rules-v1"),
        decision=Decision(status=status, decided_by=decided_by))


TWO_LICENCE_ATOMS = (atom("a1", "Each distribution must state the licence under which the file may be reused.", "distribution")
                     + atom("a2", "Every distribution must give the licence of its file.", "distribution"))
BATCH_ATOMS = (atom("a1", "The catalogue must describe each tensile specimen batch as a resource of its own.", "catalogue")
               + atom("a2", "Each dataset must state the colour of the packaging.", "dataset"))


def test_merged_duplicate_is_judged_before_it_is_auto_accepted():
    """Two atoms -> same (class, path): V5 duplicate_element blocks T2 in verify and repair; consolidate merges."""
    pipe = make(TWO_LICENCE_ATOMS)
    pipe.run_all()
    merged = [c for c in pipe.changes() if c.merged_from and c.decision.status != "superseded"]
    assert merged, "the scenario must produce a merged change"
    assert unjudged_auto_accepted(pipe) == []
    judged = {call.subject_id for call in pipe.store.list_llm_calls("p1") if call.purpose == "judge"}
    assert all(c.id in judged for c in merged if c.included)


class RejectsPackagingAtom(MockProvider):
    """A judge that (like a model would) rejects any change claiming to cover the packaging atom."""

    def _judge(self, context):
        if any(a["id"] == "a2" for a in context["atoms"]):
            return AttributionOut(verdict="unsupported", explanation="a2 asks for something else", unsupported_facets=[])
        return super()._judge(context)


@pytest.mark.parametrize("config", [PipelineConfig(repair_rounds=0), PipelineConfig()])
def test_judge_rejection_is_not_discarded_by_merging(config):
    pipe = make(BATCH_ATOMS, config=config, provider=RejectsPackagingAtom())
    pipe.run_intake(); pipe.run_retrieve()
    pipe.store.save_change("p1", mint_class("chg-A", "a1", "each tensile specimen batch", 0.9))
    pipe.store.save_change("p1", mint_class("chg-B", "a2", "the colour of the packaging", 0.6))
    pipe.run_all(from_stage="verify")                       # the pipeline's own order: verify, consolidate, repair
    live = [c for c in pipe.changes() if c.decision.status not in ("superseded", "rejected")]
    assert any("a1" in c.atom_ids for c in live), "the valid claim (a1) must survive"
    covering_a2 = [c for c in live if "a2" in c.atom_ids]
    assert all(c.decision.status != "auto_accepted" for c in covering_a2), \
        [(c.id, c.decision.status, c.decision.note) for c in covering_a2]
    accepted = [c for c in live if c.decision.status == "auto_accepted"]
    assert all("a2" not in c.atom_ids for c in accepted)


def test_policy_requires_a_t2_verdict_when_the_check_is_on():
    pipe = make(TWO_LICENCE_ATOMS)
    change = ProfileChange(id="x", kind="refine_property", target_class=DCAT + "Distribution", path=DCT + "license",
                           covers=[CoverageLink(atom_id="a1", reason="r", evidence_quote="licence")], confidence=0.9,
                           verification=[CheckResult(check="V1", passed=True, severity="info")])
    pipe._decide(change)
    assert change.decision.status == "needs_review"


class JudgeOutage(MockProvider):
    def _judge(self, context):
        raise LLMError("judge down")


def test_judge_outage_does_not_auto_accept():
    pipe = make(TWO_LICENCE_ATOMS.split("  - id: a2")[0], provider=JudgeOutage())
    pipe.run_all()
    assert unjudged_auto_accepted(pipe) == []


def test_consolidation_conflict_stays_with_the_human():
    pipe = make(atom("a1", "The catalogue must describe each tensile specimen batch as a resource of its own.", "catalogue")
                + atom("a2", "Every tensile specimen batch must be described as a resource in the catalogue.", "catalogue"))
    pipe.run_intake(); pipe.run_retrieve()
    pipe.store.save_change("p1", mint_class("chg-H", "a1", "each tensile specimen batch", 0.9, "human:rev", "accepted"))
    pipe.store.save_change("p1", mint_class("chg-M", "a2", "every tensile specimen batch", 0.9))
    pipe.run_verify(); pipe.run_consolidate()
    assert pipe.store.list_conflicts("p1")
    assert pipe.store.get_change("p1", "chg-M").decision.status == "needs_review"
