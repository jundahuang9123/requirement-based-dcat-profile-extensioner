"""Benchmark hygiene: nothing that identifies a case or its published profile reaches a prompt or the
provider context (the leak that contaminated the first pilot runs)."""
from profile_extensioner.contracts import Atom, Project, SourceReference
from profile_extensioner.engine.intake import lint_atom, run_intake
from profile_extensioner.engine.prompts import build_propose_prompt
from profile_extensioner.engine.retrieve import retrieve_candidates
from profile_extensioner.knowledge import load_knowledge_base


def test_sources_titles_and_prefixes_never_reach_the_model():
    kb = load_knowledge_base("dcat-ap-1.1", profile_namespace="https://example.org/statdcat#", profile_prefix="stat")
    atom = Atom(id="A-001", statement="Users can see the dimensions of a dataset.", subject="dataset", modality="should",
                source_reference=SourceReference(document="statdcat", locator="StatDCAT-AP 1.0.0 §7.2.1"),
                hints=["stat:dimension"])
    project = Project(id="statdcat-run", name="statdcat extension", profile_title="statdcat extension",
                      base_profile_id="dcat-ap-1.1", profile_namespace="https://example.org/statdcat#", profile_prefix="stat")
    assessment = run_intake([atom], kb)[0]
    system, user, context = build_propose_prompt(atom, assessment, retrieve_candidates(atom, assessment, kb), kb, project)
    text = f"{system}\n{user}".lower()
    for canary in ("statdcat", "§7.2.1", "stat:", "source:"):
        assert canary not in text, canary
    assert set(context["atom"]) == {"id", "statement", "subject", "modality"}   # what the offline provider sees too


def test_profile_names_in_statements_are_flagged():
    issues = lint_atom(Atom(id="a", statement="Users can find datasets as StatDCAT-AP describes them.", subject="dataset"))
    assert any(issue.code == "contains_profile_name" for issue in issues)


def test_minted_terms_reach_judge_and_repair_prompts_as_NEW_only():
    import json

    from profile_extensioner.contracts import CheckResult, CoverageLink, Facets, MintJustification, ProfileChange
    from profile_extensioner.engine.prompts import build_judge_prompt, build_repair_prompt

    kb = load_knowledge_base("dcat-ap-1.1", profile_namespace="https://example.org/statdcat#", profile_prefix="stat")
    project = Project(id="p", name="statdcat extension", profile_title="statdcat extension", base_profile_id="dcat-ap-1.1",
                      profile_namespace="https://example.org/statdcat#", profile_prefix="stat")
    atom = Atom(id="A-001", statement="Users can see the dimensions of a dataset.", subject="dataset", modality="should")
    minted = ProfileChange(
        id="c1", kind="mint_property", target_class="http://www.w3.org/ns/dcat#Dataset",
        path="https://example.org/statdcat#dimension", label="dimension",
        facets=Facets(obligation="recommended", range_class="https://example.org/statdcat#Dimension"),
        covers=[CoverageLink(atom_id="A-001", reason="stat:dimension carries it", evidence_quote="dimensions")],
        mint=MintJustification(reason_no_reuse="nothing fits"))
    failure = CheckResult(check="V1", passed=False, message="The class stat:Dimension is used but no change mints it.")
    _, judge_user, judge_context = build_judge_prompt(minted, [atom], kb)
    _, repair_user, repair_context = build_repair_prompt(minted, [failure], [atom], [], kb, project, round_number=1,
                                                         proposed_json=minted.model_dump_json())
    for text in (judge_user, repair_user, json.dumps(judge_context), json.dumps(repair_context)):
        assert "statdcat" not in text.lower() and "stat:" not in text
    assert "NEW:dimension" in judge_user and "NEW:Dimension" in repair_user
