"""A valid change must never be lost because it was merged with a failing duplicate (adversarial review, H1):
only valid changes are merged, the judged-supported one is kept, and a machine withdrawal of a merged change
restores what it had absorbed."""
from profile_extensioner.contracts import PipelineConfig, Project
from profile_extensioner.engine.intake import parse_atom_set
from profile_extensioner.engine.pipeline import Pipeline
from profile_extensioner.engine.schemas import AttributionOut
from profile_extensioner.llm.client import LLMClient
from profile_extensioner.llm.mock import MockProvider
from profile_extensioner.llm.registry import Credentials
from profile_extensioner.store.blackboard import Store

HEADER = "base_profile_ids: [dcat-ap-3.0.1]\natoms:\n"


def atom(aid, statement):
    return f"  - id: {aid}\n    statement: {statement}\n    subject: distribution\n    modality: must\n"


A1 = atom("a1", "Each distribution must state the licence under which the file may be reused.")
A2 = atom("a2", "Every distribution must give the licence of its file.")


class RejectsA2(MockProvider):
    """A judge that rejects every claim involving a2, as a model would when a2 asks for something else."""

    def _judge(self, context):
        if any(a["id"] == "a2" for a in context["atoms"]):
            return AttributionOut(verdict="unsupported", explanation="a2 asks for something else", unsupported_facets=[])
        return super()._judge(context)


def run(atoms_yaml):
    store = Store()
    store.save_project(Project(id="p1", name="T", profile_namespace="https://example.org/x#", profile_prefix="x",
                               config=PipelineConfig()))
    store.replace_atoms("p1", parse_atom_set(HEADER + atoms_yaml).atoms)
    pipe = Pipeline(store, Credentials(), "p1")
    pipe._llm = LLMClient(RejectsA2(), pipe.project.llm, store=store, project_id="p1")
    pipe.run_all()
    return pipe


def test_a_valid_change_survives_a_failing_duplicate():
    alone = run(A1)
    assert alone.coverage()["a1"] == "addressed"
    both = run(A1 + A2)
    assert both.coverage()["a1"] == "addressed"            # was 'unaddressed' when the merged keeper was withdrawn
    included = [c for c in both.changes() if c.included]
    assert any("a1" in c.atom_ids for c in included)
    assert not any("a2" in c.atom_ids for c in included)  # the judge never supported a2's claim
