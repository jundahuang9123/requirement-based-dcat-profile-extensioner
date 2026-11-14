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
