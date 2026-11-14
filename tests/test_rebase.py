"""Rebase: moving an extension onto another DCAT-AP release (and so onto another DCAT version), as a
staged plan: preview (nothing changes), apply with choices (defaults where none is given), or cancel."""
import pytest

from profile_extensioner.contracts import (
    Atom, AtomAssessment, CoverageLink, Decision, ElementRef, Facets, MintJustification, PipelineConfig, ProfileChange,
    Project, Provenance,
)
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


def project_with(base, atoms, changes, assessments=()):
    store = Store()
    store.save_project(Project(id="p", name="p", base_profile_id=base, profile_namespace=NS, profile_prefix="ext"))
    store.replace_atoms("p", atoms)
    pipeline = Pipeline(store, Credentials(), "p")
    pipeline.run_intake()
    for assessment in assessments:
        store.save_assessment("p", assessment)
    pipeline.run_retrieve()
    for change in changes:
        store.save_change("p", change)
    return pipeline


@pytest.fixture()
def pipe():
    return project_with("dcat-ap-1.1", [
        Atom(id="a1", statement="Users can reach the service behind a distribution.", subject="distribution", modality="should"),
        Atom(id="a2", statement="Users can find the previous version of a dataset.", subject="dataset", modality="should"),
        Atom(id="a3", statement="Users can see the version of a dataset.", subject="dataset", modality="should"),
    ], [
        make_change("c-access", "reuse_property", DCAT + "Distribution", DCAT + "accessService", atom="a1",
                    range_class=DCAT + "DataService"),
        make_change("c-prev", "mint_property", DCAT + "Dataset", NS + "previousVersion", atom="a2",
                    range_class=DCAT + "Dataset", label="previous version"),
        make_change("c-version", "reuse_property", DCAT + "Dataset", DCT + "hasVersion", atom="a3",
                    range_class=DCAT + "Dataset", decided_by="human:rev", status="accepted"),
    ])


def by_finding(items):
    return {(item.change_id or item.atom_id, item.finding): item for item in items}


def test_preview_changes_nothing_and_cancel_leaves_the_project_as_it_was(pipe):
    before = pipe._state_hash()
    plan = pipe.rebase_preview("dcat-ap-3.0.1", "rev")
    assert pipe.store.get_project("p").base_profile_id == "dcat-ap-1.1" and pipe._state_hash() == before
    assert pipe.store.get_project("p").pending_rebase.plan_id == plan.plan_id
    with pytest.raises(ValueError):
        pipe.sign_off("rev")                                    # a pending plan blocks the release
    pipe.rebase_cancel(plan.plan_id, "rev")
    project = pipe.store.get_project("p")
    assert project.pending_rebase is None and project.rebases == [] and pipe._state_hash() == before


def test_plan_items_have_choices_and_defaults(pipe):
    plan = pipe.rebase_preview("dcat-ap-3.0.1", "rev")
    found = by_finding(plan.items)
    assert found[("c-access", "dcat_now_current")].default_choice == "keep"
    prev = found[("c-prev", "mint_now_reusable")]                       # minted; DCAT 3 has dcat:previousVersion
    assert prev.replacement == DCAT + "previousVersion" and prev.default_choice == "manual" and "replace" in prev.choices
    version = found[("c-version", "deprecated_by_base")]               # DCAT-AP 3: dct:hasVersion -> dcat:hasVersion
    assert version.replacement == DCAT + "hasVersion" and version.human_decided
    assert version.default_choice in ("keep", "manual")                # a human decision is never undone by default


def test_apply_with_choices_replaces_and_keeps_human_decisions(pipe):
    plan = pipe.rebase_preview("dcat-ap-3.0.1", "rev")
    found = by_finding(plan.items)
    report = pipe.rebase_apply(plan.plan_id, {found[("c-prev", "mint_now_reusable")].id: "replace"}, "rev")
    project = pipe.store.get_project("p")
    assert project.base_profile_id == "dcat-ap-3.0.1" and project.pending_rebase is None and pipe.kb.dcat.id == "dcat-3"
    assert pipe.store.get_change("p", "c-prev").decision.status == "superseded"
    replaced = pipe.store.get_change("p", report.new_change_ids[0])
    assert replaced.path == DCAT + "previousVersion" and replaced.kind == "reuse_property" and replaced.supersedes == "c-prev"
    human = pipe.store.get_change("p", "c-version")
    assert human.decision.status == "accepted" and human.decision.decided_by == "human:rev"
    assert any("rebase dcat-ap-1.1 -> dcat-ap-3.0.1" in note for note in human.engine_notes)
    readme = next(a for a in pipe.store.list_artifacts("p") if a.name == "README.md").content
    assert "Base history" in readme and "DCAT 3" in readme
    assert pipe.store.get_conformance("p").base_profile_id == "dcat-ap-3.0.1"


def test_manual_items_stay_with_a_human_after_consolidation():
    # review finding 1: consolidation used to re-decide rule:rebase changes back to auto_accepted
    pipe = project_with("dcat-ap-1.1",
                        [Atom(id="a1", statement="Users can see who created a dataset.", subject="dataset", modality="may")],
                        [make_change("c-creator", "reuse_property", DCAT + "Dataset", DCT + "creator", atom="a1",
                                     obligation="optional", range_class="http://xmlns.com/foaf/0.1/Agent")])
    plan = pipe.rebase_preview("dcat-ap-3.0.1", "rev")
    item = by_finding(plan.items)[("c-creator", "now_in_base")]
    assert item.default_choice == "withdraw"                            # 3.0.1 defines it; the change adds nothing
    pipe.rebase_apply(plan.plan_id, {item.id: "manual"}, "rev")
    change = pipe.store.get_change("p", "c-creator")
    assert change.decision.status == "needs_review" and change.decision.decided_by == "rule:rebase"
    with pytest.raises(ValueError):
        pipe.sign_off("rev")                                            # the queue is not empty


def test_covered_claims_are_rechecked_against_the_new_base():
    # review finding 2: a "covered by the base" claim must hold under the new base, or the atom is re-proposed
    atom = Atom(id="a1", statement="Users must find the datasets of a catalogue.", subject="catalogue", modality="must")
    covered = AtomAssessment(atom_id="a1", disposition="covered_by_base", resource_class=DCAT + "Catalog",
                             covered_by=[ElementRef(target_class=DCAT + "Catalog", path=DCAT + "dataset")],
                             provenance=Provenance(author_type="llm", author="llm:mock"))
    pipe = project_with("dcat-ap-2.1.1", [atom], [], [covered])
    plan = pipe.rebase_preview("dcat-ap-3.0.1", "rev")
    item = by_finding(plan.items)[("a1", "covered_claim_weakened")]     # mandatory in 2.1.1, recommended in 3.0.1
    assert item.default_choice == "repropose"
    report = pipe.rebase_apply(plan.plan_id, {}, "rev")
    assert report.reproposed_atoms == ["a1"]
    assert pipe.store.get_assessment("p", "a1").disposition != "covered_by_base" or \
        pipe.store.get_assessment("p", "a1").provenance.author_type != "llm"


def test_keep_claim_records_a_human_judgement():
    atom = Atom(id="a1", statement="Users must find the datasets of a catalogue.", subject="catalogue", modality="must")
    covered = AtomAssessment(atom_id="a1", disposition="covered_by_base", resource_class=DCAT + "Catalog",
                             covered_by=[ElementRef(target_class=DCAT + "Catalog", path=DCAT + "dataset")])
    pipe = project_with("dcat-ap-2.1.1", [atom], [], [covered])
    plan = pipe.rebase_preview("dcat-ap-3.0.1", "rev")
    item = by_finding(plan.items)[("a1", "covered_claim_weakened")]
    pipe.rebase_apply(plan.plan_id, {item.id: "keep_claim"}, "rev")
    kept = pipe.store.get_assessment("p", "a1")
    assert kept.disposition == "covered_by_base" and kept.provenance.author_type == "human"


def test_intake_is_redone_under_the_new_base():
    # review finding 3: DCAT-AP 1.1 has no Data Service class; 3.0.1 has one
    atom = Atom(id="a1", statement="A data service should state the address of its endpoint.", subject="data service",
                modality="should")
    pipe = project_with("dcat-ap-1.1", [atom], [])
    assert pipe.store.get_assessment("p", "a1").resource_class is None
    plan = pipe.rebase_preview("dcat-ap-3.0.1", "rev")
    assert by_finding(plan.items)[("a1", "intake_changed")].default_choice == "repropose"
    report = pipe.rebase_apply(plan.plan_id, {}, "rev")
    assert pipe.store.get_assessment("p", "a1").resource_class == DCAT + "DataService"
    assert report.reproposed_atoms == ["a1"]
    states = pipe.store.get_project("p").stage_states
    assert states["intake"] == states["retrieve"] == states["propose"] == states["verify"] == "done"


def test_a_stale_plan_is_refused(pipe):
    plan = pipe.rebase_preview("dcat-ap-3.0.1", "rev")
    pipe.decide("c-access", "rejected", "rev", "changed my mind")
    with pytest.raises(ValueError, match="preview it again"):
        pipe.rebase_apply(plan.plan_id, {}, "rev")


def test_rebase_back_onto_an_older_dcat_flags_later_terms(pipe):
    pipe.rebase("dcat-ap-3.0.1", "rev")
    plan = pipe.rebase_preview("dcat-ap-1.1", "rev")
    item = by_finding(plan.items)[("c-access", "dcat_now_later")]
    assert item.default_choice == "manual"                             # later_dcat_terms = review


def test_rebase_refuses_the_same_or_an_unknown_base(pipe):
    with pytest.raises(ValueError):
        pipe.rebase_preview("dcat-ap-1.1", "rev")
    with pytest.raises(KeyError):
        pipe.rebase_preview("dcat-ap-9.9", "rev")


def test_dcat_rung_respects_hidden_namespaces():
    # review finding 4: terms of an excluded namespace must not be offered by the DCAT rung
    from profile_extensioner.engine.retrieve import retrieve_candidates
    from profile_extensioner.knowledge import load_knowledge_base

    kb = load_knowledge_base("dcat-ap-3.0.1", profile_namespace=NS, profile_prefix="ext",
                             exclude_namespaces=["http://www.w3.org/ns/odrl/2/"])
    atom = Atom(id="a1", statement="Users can see the usage policy of the catalogue.", subject="catalogue")
    assert all(not c.iri.startswith("http://www.w3.org/ns/odrl/2/") for c in retrieve_candidates(atom, None, kb))


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
    plan = client.post(f"/api/projects/{pid}/rebase/preview", json={"base_profile_id": "dcat-ap-3.0.1", "by": "rev"}).json()
    assert plan["to_dcat"] == "dcat-3" and plan["from_dcat"] == "dcat-2"
    assert client.get(f"/api/projects/{pid}").json()["project"]["pending_rebase"]["plan_id"] == plan["plan_id"]
    report = client.post(f"/api/projects/{pid}/rebase/{plan['plan_id']}/apply", json={"by": "rev"}).json()
    assert report["to_base"] == "dcat-ap-3.0.1"
    snap = client.get(f"/api/projects/{pid}").json()
    assert snap["project"]["base_profile_id"] == "dcat-ap-3.0.1" and snap["conformance"]["dcat_version"] == "dcat-3"
    assert client.post(f"/api/projects/{pid}/rebase/preview", json={"base_profile_id": "dcat-ap-3.0.1"}).status_code == 400
    again = client.post(f"/api/projects/{pid}/rebase/preview", json={"base_profile_id": "dcat-ap-2.1.1"}).json()
    assert client.delete(f"/api/projects/{pid}/rebase/{again['plan_id']}").json() == {"cancelled": again["plan_id"]}


def test_api_validates_the_declared_base_before_saving():
    # review finding 6: an atom set may name its base by title; an unknown one falls back, never orphans a project
    from fastapi.testclient import TestClient

    from profile_extensioner.api.app import app

    client = TestClient(app)
    declared = client.post("/api/projects", json={
        "name": "titled base", "atoms_text": "base_profile_ids: [DCAT-AP 2.1.1]\natoms:\n  - id: a1\n    statement: x\n",
        "profile_namespace": "https://example.org/t#", "profile_prefix": "t"})
    assert declared.status_code == 200 and declared.json()["base_profile_id"] == "dcat-ap-2.1.1"
    unknown = client.post("/api/projects", json={"name": "bad", "base_profile_id": "dcat-ap-9.9",
                                                 "profile_namespace": "https://example.org/b#", "profile_prefix": "b"})
    assert unknown.status_code == 400
    assert "bad" not in {p["name"] for p in client.get("/api/projects").json()}
