"""Conformance runs on every base: the witness check (C7) never fails to run, and C2 catches a class range
contradicted by a literal range (adversarial review: 2.1.x range shapes, 3.0.1 DataService links)."""
import pytest

from profile_extensioner.compile.model import build_view
from profile_extensioner.conformance.check import check_conformance
from profile_extensioner.contracts import Atom, CoverageLink, Decision, Facets, ProfileChange, Project
from profile_extensioner.knowledge import list_base_profiles, load_knowledge_base

DCAT, DCT = "http://www.w3.org/ns/dcat#", "http://purl.org/dc/terms/"


def change(target, path, **facets):
    return ProfileChange(id="c1", kind="refine_property", target_class=target, path=path, facets=Facets(**facets),
                         covers=[CoverageLink(atom_id="a1", reason="r", evidence_quote="x")],
                         decision=Decision(status="accepted", decided_by="human:rev"))


def view_for(base, item):
    kb = load_knowledge_base(base, profile_namespace="https://example.org/x#", profile_prefix="ext")
    project = Project(id="p", name="p", base_profile_id=base, profile_namespace="https://example.org/x#", profile_prefix="ext")
    return build_view(project, kb, [Atom(id="a1", statement="Users can see x.", subject="dataset")], [item])


@pytest.mark.parametrize("base", [info.id for info in list_base_profiles()])
def test_the_witness_check_runs_on_every_base(base):
    for target in (DCAT + "Dataset", DCAT + "Distribution", DCAT + "Catalog"):
        report = check_conformance(view_for(base, change(target, DCT + "description", obligation="mandatory", min_count=1)))
        c7 = next(c for c in report.checks if c.id == "C7")
        assert "could not run" not in c7.message, (base, target, c7.message)


def test_a_literal_range_against_a_base_class_range_is_a_contradiction():
    # DCAT-AP 3.0.1 constrains dct:publisher on dcat:Dataset to foaf:Agent; a datatype range cannot hold with it
    report = check_conformance(view_for("dcat-ap-3.0.1", change(DCAT + "Dataset", DCT + "publisher",
                                                                range_datatype="http://www.w3.org/2001/XMLSchema#string")))
    c2 = next(c for c in report.checks if c.id == "C2")
    assert not c2.passed
