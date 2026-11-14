"""The W3C DCAT state a base builds on: vendored versions, pinning, retrieval, checks D1-D3, C8, defaults."""
import hashlib
from pathlib import Path

import pytest
import yaml

from profile_extensioner.compile.model import build_view
from profile_extensioner.compile.shacl import compile_shacl
from profile_extensioner.conformance.check import check_conformance
from profile_extensioner.contracts import Atom, CoverageLink, Decision, Facets, PipelineConfig, ProfileChange, Project
from profile_extensioner.engine.prompts import build_propose_prompt
from profile_extensioner.engine.retrieve import retrieve_candidates
from profile_extensioner.engine.verify import VerifyContext, verify_change
from profile_extensioner.knowledge import (
    DATA_DIR, latest_base_profile_id, list_base_profiles, list_dcat_versions, load_knowledge_base,
)

DCAT, DCT = "http://www.w3.org/ns/dcat#", "http://purl.org/dc/terms/"
DCAT_DIR = DATA_DIR / "dcat"


def kb_for(base: str):
    return load_knowledge_base(base, profile_namespace="https://example.org/x#", profile_prefix="ext")


def change(kind: str, target: str, path: str | None, *, obligation="recommended", range_class=None,
           decided_by="rule:policy", status="auto_accepted") -> ProfileChange:
    return ProfileChange(
        id=f"c-{(path or target).rsplit('#', 1)[-1]}", kind=kind, target_class=target, path=path,
        facets=Facets(obligation=obligation, range_class=range_class),
        covers=[CoverageLink(atom_id="a1", reason="r", evidence_quote="x")],
        decision=Decision(status=status, decided_by=decided_by),
    )


def results(kb, item: ProfileChange, *, policy="review"):
    project = Project(id="p", name="p", base_profile_id=kb.base.info.id, profile_namespace="https://example.org/x#",
                      profile_prefix="ext", config=PipelineConfig(later_dcat_terms=policy))
    atom = Atom(id="a1", statement="Users can see x.", subject="dataset", modality="should")
    return verify_change(item, VerifyContext(kb=kb, project=project, atoms={"a1": atom}, changes=[item]))


def failed(found, check):
    return [r for r in found if r.check == check and not r.passed]


# -- vendored data -----------------------------------------------------------


def test_every_dcat_version_is_kept_unmodified():
    manifest = yaml.safe_load((DCAT_DIR / "versions.yaml").read_text(encoding="utf-8"))
    assert [v["id"] for v in manifest["versions"]] == ["dcat-2014", "dcat-2", "dcat-3"]
    for version in manifest["versions"]:
        for part in ("rdf", "spec"):
            path = DCAT_DIR / version[part]["file"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == version[part]["sha256"], path
        assert (DCAT_DIR / version["model"]["file"]).exists()
    assert [v.id for v in list_dcat_versions(DATA_DIR)][-1] == "dcat-3"
    assert list_dcat_versions(DATA_DIR)[-1].is_latest


def test_every_base_names_the_dcat_it_builds_on():
    known = {v.id for v in list_dcat_versions(DATA_DIR)}
    pins = {info.id: info.dcat.dcat for info in list_base_profiles()}
    assert set(pins.values()) <= known
    assert pins["dcat-ap-1.1"] == pins["dcat-ap-1.2"] == pins["dcat-ap-1.2.1"] == "dcat-2014"
    assert pins["dcat-ap-2.0.0"] == pins["dcat-ap-2.0.1"] == pins["dcat-ap-2.1.0"] == pins["dcat-ap-2.1.1"] == "dcat-2"
    assert pins["dcat-ap-3.0.0"] == pins["dcat-ap-3.0.1"] == "dcat-3"
    status = {info.id: info.dcat.dcat_status_at_release for info in list_base_profiles()}
    assert "Candidate Recommendation" in status["dcat-ap-2.0.0"] and "Proposed Recommendation" in status["dcat-ap-3.0.0"]
    for info in list_base_profiles():
        assert info.release_date and info.dcat.evidence and info.dcat.evidence[0]["quote"]


def test_the_newest_release_is_the_default_base():
    infos = list_base_profiles()
    assert [info.release_date for info in infos] == sorted(info.release_date for info in infos)
    assert latest_base_profile_id() == infos[-1].id == "dcat-ap-3.0.1"
    assert [info.id for info in infos if info.is_latest] == ["dcat-ap-3.0.1"]


def test_term_history_and_model():
    kb = kb_for("dcat-ap-1.1")
    assert kb.dcat.id == "dcat-2014" and "2014-01-16" in kb.dcat.describe_version()
    assert kb.dcat.introduced_in(DCAT + "DataService") == "dcat-2"
    assert kb.dcat.introduced_in(DCAT + "DatasetSeries") == "dcat-3"
    assert kb.dcat.status(DCAT + "accessService") == "later"
    assert kb.dcat.status(DCAT + "size") == "deprecated"
    assert kb.dcat.status(DCAT + "keyword") == "current"
    assert kb.dcat.status(DCT + "title") == ""
    assert {p.path for p in kb.dcat.properties_for(DCAT + "Dataset")} >= {DCAT + "keyword", DCT + "identifier"}
    new = kb_for("dcat-ap-3.0.1")
    assert new.dcat.status(DCAT + "accessService") == "current" and new.dcat.status(DCAT + "size") == "removed"
    inherited = new.dcat.listed_for(DCAT + "Dataset", DCAT + "previousVersion")
    assert inherited is not None and inherited.listed_on == DCAT + "Resource"   # Dataset is a Cataloged Resource
    assert len(new.dcat.inverse_pairs()) == 11


def test_the_index_holds_the_pinned_dcat_version():
    old, new = kb_for("dcat-ap-1.1"), kb_for("dcat-ap-3.0.1")
    assert old.term(DCAT + "keyword").domain == [DCAT + "Dataset"]          # DCAT 2014 declares a domain
    assert new.term(DCAT + "keyword").domain == []                         # DCAT 2 dropped it
    assert old.term(DCAT + "accessService").dcat_status == "later"
    assert set(new.term(DCAT + "hadRole").domain) == {DCAT + "Relationship", "http://www.w3.org/ns/prov#Attribution"}
    assert new.term(DCAT + "isDistributionOf") is not None                 # declared by owl:inverseOf only


def test_specification_only_elements_of_dcat_ap_1_1():
    kb = kb_for("dcat-ap-1.1")
    element = kb.base.element(DCAT + "Dataset", DCAT + "keyword")          # listed in the spec, no official shape
    assert element is not None and element.facets.obligation == "recommended" and "specification" in element.source
    assert kb.base.obligation(DCAT + "Dataset", DCT + "accrualPeriodicity") == "optional"   # RDF typo corrected
    loosened = results(kb, change("refine_property", DCAT + "Dataset", DCAT + "keyword", obligation="optional"))
    assert failed(loosened, "V3")


# -- retrieval and prompts ------------------------------------------------------


def test_retrieval_offers_dcat_properties_and_marks_later_ones():
    new = kb_for("dcat-ap-3.0.1")
    atom = Atom(id="a1", statement="Users can find the previous version of a dataset.", subject="dataset", modality="should")
    found = {c.iri: c for c in retrieve_candidates(atom, None, new)}
    assert DCAT + "previousVersion" in found
    assert found[DCAT + "previousVersion"].dcat_listed_on_class and "optional field" in found[DCAT + "previousVersion"].why
    old = kb_for("dcat-ap-1.1")
    hits = {c.iri: c for c in retrieve_candidates(atom, None, old)}
    if DCAT + "previousVersion" in hits:
        assert hits[DCAT + "previousVersion"].dcat_status == "later" and "DCAT 3" in hits[DCAT + "previousVersion"].why


def test_the_prompt_states_the_dcat_state():
    kb = kb_for("dcat-ap-1.1")
    atom = Atom(id="a1", statement="Users can see keywords.", subject="dataset", modality="should")
    from profile_extensioner.engine.intake import run_intake

    assessment = run_intake([atom], kb)[0]
    project = Project(id="p", name="p", base_profile_id="dcat-ap-1.1", profile_namespace="https://example.org/x#", profile_prefix="ext")
    _, user, _ = build_propose_prompt(atom, assessment, retrieve_candidates(atom, assessment, kb), kb, project)
    assert "builds on W3C DCAT 2014" in user


# -- checks D1-D3 and the decision ------------------------------------------------


def test_d1_later_dcat_term_goes_to_a_human():
    kb = kb_for("dcat-ap-1.1")
    item = change("reuse_property", DCAT + "Distribution", DCAT + "accessService", range_class=DCAT + "DataService")
    found = results(kb, item)
    d1 = failed(found, "D1")
    assert d1 and d1[0].severity == "warning" and d1[0].details["requires_human"]
    assert not [r for r in found if not r.passed and r.severity == "error" and r.check == "D1"]
    assert failed(results(kb, item, policy="forbid"), "D1")[0].severity == "error"
    assert not failed(results(kb, item, policy="allow"), "D1")
    assert not failed(results(kb_for("dcat-ap-3.0.1"), item), "D1")


def test_policy_sends_later_terms_to_review():
    from profile_extensioner.engine.intake import parse_atom_set
    from profile_extensioner.engine.pipeline import Pipeline
    from profile_extensioner.llm.registry import Credentials
    from profile_extensioner.store.blackboard import Store

    store = Store()
    store.save_project(Project(id="p", name="p", base_profile_id="dcat-ap-1.1",
                               profile_namespace="https://example.org/x#", profile_prefix="ext"))
    store.replace_atoms("p", parse_atom_set("atoms:\n  - id: a1\n    statement: Users can reach the service.\n"
                                            "    subject: distribution\n    modality: should\n").atoms)
    pipe = Pipeline(store, Credentials(), "p")
    item = change("reuse_property", DCAT + "Distribution", DCAT + "accessService", range_class=DCAT + "DataService")
    item.verification = results(pipe.kb, item)
    item.confidence = 0.9
    pipe._decide(item)
    assert item.decision.status == "needs_review" and "D1" in item.decision.note and "DCAT 2014" in item.decision.note


def test_d2_deprecated_and_d3_inverse_and_v2_union_domain():
    old, new = kb_for("dcat-ap-1.1"), kb_for("dcat-ap-3.0.1")
    d2 = failed(results(old, change("reuse_property", DCAT + "Distribution", DCAT + "size")), "D2")
    assert d2 and "dcat:byteSize" in d2[0].message
    d3 = failed(results(new, change("reuse_property", DCAT + "Distribution", DCAT + "isDistributionOf",
                                    range_class=DCAT + "Dataset")), "D3")
    assert d3 and d3[0].severity == "warning" and "dcat:distribution" in d3[0].message
    v2 = failed(results(new, change("reuse_property", DCAT + "Dataset", DCAT + "hadRole", range_class=DCAT + "Role")), "V2")
    assert v2 and v2[0].severity == "error"


# -- conformance and compiled output -----------------------------------------------


def test_c8_reports_dcat_terms_beyond_the_base_dcat():
    kb = kb_for("dcat-ap-1.1")
    project = Project(id="p", name="p", base_profile_id="dcat-ap-1.1", profile_namespace="https://example.org/x#",
                      profile_prefix="ext")
    atoms = [Atom(id="a1", statement="Users can reach the service.", subject="distribution", modality="should")]
    accepted = change("reuse_property", DCAT + "Distribution", DCAT + "accessService", range_class=DCAT + "DataService",
                      decided_by="human:rev", status="accepted")
    report = check_conformance(build_view(project, kb, atoms, [accepted]))
    c8 = next(c for c in report.checks if c.id == "C8")
    assert not c8.passed and c8.severity == "warning" and "DCAT 2" in c8.message
    assert report.dcat_version == "dcat-2014" and "(on DCAT 2014)" in report.summary
    clean = change("refine_property", DCAT + "Dataset", DCAT + "keyword", obligation="mandatory")
    clean.facets.min_count = 1
    view = build_view(project, kb, atoms, [clean])
    assert next(c for c in check_conformance(view).checks if c.id == "C8").passed
    assert "REC-vocab-dcat-20140116" in compile_shacl(view)


def test_api_defaults_to_the_newest_base_and_lists_dcat_versions():
    from fastapi.testclient import TestClient

    from profile_extensioner.api.app import app

    client = TestClient(app)
    assert [v["id"] for v in client.get("/api/dcat-versions").json()] == ["dcat-2014", "dcat-2", "dcat-3"]
    created = client.post("/api/projects", json={
        "name": "default base", "atoms_text": "atoms:\n  - id: a1\n    statement: Users can see the licence.\n",
        "profile_namespace": "https://example.org/d#", "profile_prefix": "d"}).json()
    assert created["base_profile_id"] == latest_base_profile_id()
    detail = client.get("/api/base-profiles/dcat-ap-1.1").json()
    assert detail["dcat"]["version"]["id"] == "dcat-2014" and detail["info"]["release_date"] == "2015-10-23"
    assert client.get("/api/base-profiles/nope").status_code == 404


def test_release_rdf_typos_are_corrected_and_adopted_terms_are_not_flagged():
    two = kb_for("dcat-ap-2.0.0")            # the 2.0.0 RDF writes https://www.w3.org/ns/dcat#hadRole
    assert two.base.obligation(DCAT + "Relationship", DCAT + "hadRole") == "mandatory"
    assert two.base.obligation(DCAT + "Dataset", DCT + "accrualPeriodicity") == "optional"
    assert two.base.obligation(DCAT + "DataService", DCAT + "servesDataset") == "recommended"
    old = kb_for("dcat-ap-1.2.1")            # DCAT 2014 base whose shapes already use DCAT 2's dcat:startDate
    assert old.dcat.status(DCAT + "startDate") == "later" and old.dcat_status(DCAT + "startDate") == "adopted"
    item = change("refine_property", DCT + "PeriodOfTime", DCAT + "startDate", obligation="recommended")
    assert not failed(results(old, item), "D1")


@pytest.mark.parametrize("base", [info.id for info in list_base_profiles()])
def test_each_base_loads_with_its_dcat(base):
    kb = kb_for(base)
    assert kb.dcat.id == kb.base.info.dcat.dcat
    assert kb.term(DCAT + "Dataset") is not None and kb.term(DCAT + "Dataset").dcat_status == "current"
    assert Path(DCAT_DIR / kb.dcat.id / "dcat.ttl").exists()
