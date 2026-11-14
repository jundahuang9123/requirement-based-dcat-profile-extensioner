"""Rebase: moving an extension onto another DCAT-AP release (and so onto another DCAT version)."""
import pytest

from profile_extensioner.contracts import Atom, CoverageLink, Decision, Facets, MintJustification, ProfileChange, Project
from profile_extensioner.engine.pipeline import Pipeline
from profile_extensioner.llm.registry import Credentials
from profile_extensioner.store.blackboard import Store

DCAT, DCT = "http://www.w3.org/ns/dcat#", "http://purl.org/dc/terms/"
NS = "https://example.org/x#"


def make_change(cid, kind, target, path, *, atom, obligation="recommended", range_class=None, decided_by="rule:policy",
                status="auto_accepted", label=""):
    return ProfileChange(
        id=cid, kind=kind, target_class=target, path=path, label=label,
        facets=Facets(obligation=obligation, range_class=range_class),
        covers=[CoverageLink(atom_id=atom, reason="r", evidence_quote="Users")],
        mint=MintJustification(reason_no_reuse="nothing fits") if kind.startswith("mint") else None,
        decision=Decision(status=status, decided_by=decided_by), confidence=0.9,
    )


@pytest.fixture()
def pipe():
    store = Store()
    store.save_project(Project(id="p", name="p", base_profile_id="dcat-ap-1.1", profile_namespace=NS, profile_prefix="ext"))
    store.replace_atoms("p", [
        Atom(id="a1", statement="Users can reach the service behind a distribution.", subject="distribution", modality="should"),
        Atom(id="a2", statement="Users can find the previous version of a dataset.", subject="dataset", modality="should"),
        Atom(id="a3", statement="Users can see the version of a dataset.", subject="dataset", modality="should"),
    ])
    pipeline = Pipeline(store, Credentials(), "p")
    pipeline.run_intake()
    pipeline.run_retrieve()
    for change in (
        make_change("c-access", "reuse_property", DCAT + "Distribution", DCAT + "accessService", atom="a1",
                    range_class=DCAT + "DataService"),
        make_change("c-prev", "mint_property", DCAT + "Dataset", NS + "previousVersion", atom="a2",
                    range_class=DCAT + "Dataset", label="previous version"),
        make_change("c-version", "reuse_property", DCAT + "Dataset", DCT + "hasVersion", atom="a3",
                    range_class=DCAT + "Dataset", decided_by="human:rev", status="accepted"),
    ):
        store.save_change("p", change)
    return pipeline


def test_rebase_onto_dcat_ap_3_finds_what_changed(pipe):
    report = pipe.rebase("dcat-ap-3.0.1", "rev", "move to the newest release")
    assert (report.from_base, report.to_base, report.from_dcat, report.to_dcat) == \
        ("dcat-ap-1.1", "dcat-ap-3.0.1", "dcat-2014", "dcat-3")
    findings = {(item.change_id, item.finding): item for item in report.items}
    assert ("c-access", "dcat_now_current") in findings                 # DCAT 2 term, part of DCAT 3
    prev = findings[("c-prev", "mint_now_reusable")]                    # minted, DCAT 3 has dcat:previousVersion
    assert prev.replacement == DCAT + "previousVersion" and prev.suggestion == "replace"
    deprecated = findings[("c-version", "deprecated_by_base")]          # DCAT-AP 3.x: dct:hasVersion -> dcat:hasVersion
    assert deprecated.replacement == DCAT + "hasVersion" and deprecated.severity == "error"

    project = pipe.store.get_project("p")
    assert project.base_profile_id == "dcat-ap-3.0.1" and project.rebases[-1].summary == report.summary
    assert pipe.kb.dcat.id == "dcat-3"
    assert pipe.store.get_change("p", "c-prev").decision.status == "needs_review"      # machine change: a human decides
    human = pipe.store.get_change("p", "c-version")
    assert human.decision.status == "accepted" and human.decision.decided_by == "human:rev"   # human decision stays
    assert any("rebase dcat-ap-1.1 -> dcat-ap-3.0.1" in note for note in human.engine_notes)
    report_doc = next(a for a in pipe.store.list_artifacts("p") if a.name == "README.md").content
    assert "Base history" in report_doc and "DCAT 3" in report_doc
    assert pipe.store.get_conformance("p").base_profile_id == "dcat-ap-3.0.1"


def test_rebase_back_onto_an_older_dcat_flags_later_terms(pipe):
    pipe.rebase("dcat-ap-3.0.1", "rev")
    report = pipe.rebase("dcat-ap-1.1", "rev")
    assert any(item.finding == "dcat_now_later" and item.change_id == "c-access" for item in report.items)


def test_rebase_refuses_the_same_or_an_unknown_base(pipe):
    with pytest.raises(ValueError):
        pipe.rebase("dcat-ap-1.1", "rev")
    with pytest.raises(KeyError):
        pipe.rebase("dcat-ap-9.9", "rev")


def test_rebase_through_the_api():
    from fastapi.testclient import TestClient

    from profile_extensioner.api.app import app

    client = TestClient(app)
    created = client.post("/api/projects", json={
        "name": "rebase demo", "base_profile_id": "dcat-ap-2.1.1",
        "atoms_text": "atoms:\n  - id: a1\n    statement: Users can see the licence of a distribution.\n"
                      "    subject: distribution\n    modality: should\n",
        "profile_namespace": "https://example.org/r#", "profile_prefix": "r"}).json()
    pid = created["id"]
    client.post(f"/api/projects/{pid}/run", json={"from_stage": "intake"})
    report = client.post(f"/api/projects/{pid}/rebase", json={"base_profile_id": "dcat-ap-3.0.1", "by": "rev"}).json()
    assert report["to_dcat"] == "dcat-3" and report["from_dcat"] == "dcat-2"
    snap = client.get(f"/api/projects/{pid}").json()
    assert snap["project"]["base_profile_id"] == "dcat-ap-3.0.1" and snap["conformance"]["dcat_version"] == "dcat-3"
    assert client.post(f"/api/projects/{pid}/rebase", json={"base_profile_id": "dcat-ap-3.0.1"}).status_code == 400
