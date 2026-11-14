"""Rebase: move an extension onto another base profile, and so possibly onto another DCAT version.

A DCAT-AP release builds on one W3C DCAT state (DCAT-AP 1.1: DCAT 2014; 2.x: DCAT 2; 3.x: DCAT 3).
When the base of an extension moves (a newer DCAT-AP release, or another one), everything is looked
at again against the new base and the new DCAT:

* every change: does the new base define the element itself (the change may be redundant), drop it,
  or constrain it differently, and is the change still a legal refinement there (check V3 against the
  new base); is a DCAT term the change uses now part of the base's DCAT, no longer part of it, or
  outdated; does the new base deprecate the term (DCAT-AP 3.x: dct:hasVersion -> dcat:hasVersion);
  does a minted term now have a counterpart in the new base or its DCAT; is the target class still a
  class of the base;
* every atom: does its subject map to another class under the new base (intake); does a "covered by
  the base" claim still hold (check B1 against the new base: the element may be gone, or weaker).

The result is a PLAN (``Pipeline.rebase_preview``): nothing changes until a human applies it with
their choices (``Pipeline.rebase_apply``) or cancels it. Every item offers the choices that make sense
for its finding, with a default preselected (Dataspecer's change-propagation review was the model, see
docs/research/B3-dataspecer-update.md section 5; unlike it, a change the new base makes illegal is
never kept by default, and requirement levels, datatypes and deprecations are compared).
Human decisions stay final: an item on a human-decided change defaults to ``keep``/``manual``.
"""
from __future__ import annotations

from typing import Iterable

from ..contracts import Atom, AtomAssessment, PipelineConfig, ProfileChange, Project, RebaseItem
from ..iri import local_name
from ..knowledge import KnowledgeBase


def _facet_text(facets) -> str:
    parts = [facets.obligation, f"{facets.min_count or 0}..{'n' if facets.max_count is None else facets.max_count}"]
    if facets.range_class or facets.range_datatype:
        parts.append(local_name(facets.range_class or facets.range_datatype))
    return "; ".join(parts)


def _adds_nothing(change: ProfileChange, base_facets) -> bool:
    """True when the change asks for nothing beyond what the base element already says."""
    from ..contracts import OBLIGATION_RANK

    facets = change.facets
    if OBLIGATION_RANK.get(facets.obligation, 0) > OBLIGATION_RANK.get(base_facets.obligation, 0):
        return False
    if (facets.min_count or 0) > (base_facets.min_count or 0):
        return False
    if facets.max_count is not None and (base_facets.max_count is None or facets.max_count < base_facets.max_count):
        return False
    if facets.range_class and facets.range_class != base_facets.range_class:
        return False
    if facets.range_datatype and facets.range_datatype != base_facets.range_datatype:
        return False
    return not (facets.controlled_vocabulary or facets.pattern or facets.node_kind and facets.node_kind != base_facets.node_kind)


def _counterpart(change: ProfileChange, new: KnowledgeBase) -> str | None:
    """A term of the new base or its DCAT with the minted term's local name (or label)."""
    minted = change.target_class if change.kind == "mint_class" else change.path
    if not minted:
        return None
    name = local_name(minted).lower()
    label = (change.label or "").strip().lower()
    if change.kind == "mint_class":
        candidates = [cls.iri for cls in new.base.classes()] + new.dcat.classes()
    else:
        candidates = [element.path for element in new.base.elements(change.target_class)] \
            + [prop.path for prop in new.dcat.properties_for(change.target_class)]
    for iri in dict.fromkeys(candidates):
        if new.is_minted(iri):
            continue
        term = new.term(iri)
        if term is None:                          # hidden from the index (exclude_namespaces)
            continue
        if local_name(iri).lower() == name or (label and term.label.strip().lower() == label):
            return iri
    return None


def _item(items: list[RebaseItem], *, human: bool, choices: list[str], default: str, **fields) -> None:
    """Add an item. On a human-decided change the default never undoes the human: keep (or manual)."""
    if human and default not in ("keep", "manual"):
        default = "manual" if "manual" in choices else "keep"
    if default not in choices:
        choices = [default, *choices]
    items.append(RebaseItem(id=f"r{len(items) + 1:03d}", choices=choices, default_choice=default,  # type: ignore[arg-type]
                            suggestion=default, human_decided=human, **fields))  # type: ignore[arg-type]


def analyse_rebase(
    changes: Iterable[ProfileChange],
    assessments: Iterable[AtomAssessment],
    atoms: Iterable[Atom],
    old: KnowledgeBase,
    new: KnowledgeBase,
    project: Project,
) -> list[RebaseItem]:
    from .intake import run_intake
    from .verify import VerifyContext, check_refinement, verify_assessment

    items: list[RebaseItem] = []
    to_base = new.base.info.title
    atoms_by_id = {atom.id: atom for atom in atoms}
    live = [change for change in changes if change.decision.status not in ("superseded", "rejected")]
    policy = (project.config or PipelineConfig()).later_dcat_terms
    new_ctx = VerifyContext(kb=new, project=project, atoms=atoms_by_id, changes=live)

    for change in live:
        human = change.decision.decided_by.startswith("human:")
        target, path = change.target_class, change.path

        # 1. the element itself, in the old and the new base, and the change's legality under the new base
        if path and not change.is_class_change:
            old_element, new_element = old.base.element(target, path), new.base.element(target, path)
            legality = [r for r in check_refinement(change.model_copy(deep=True), new_ctx) if not r.passed]
            if new_element is not None and old_element is None:
                redundant = _adds_nothing(change, new_element.facets)
                _item(items, human=human, change_id=change.id, term=path, finding="now_in_base",
                      severity="warning" if redundant else "info",
                      choices=["withdraw", "keep", "manual"] if redundant else ["keep", "manual"],
                      default="withdraw" if redundant else "keep",
                      message=f"{to_base} defines {new.curie(path)} on {new.curie(target)} itself "
                              f"({_facet_text(new_element.facets)})"
                              + ("; the change adds nothing beyond it." if redundant else "; the change now tightens it."))
            elif old_element is not None and new_element is None:
                _item(items, human=human, change_id=change.id, term=path, finding="base_dropped", severity="info",
                      choices=["keep", "withdraw"], default="keep",
                      message=f"{to_base} does not define {new.curie(path)} on {new.curie(target)}; "
                              f"the change is now an addition.")
            elif old_element is not None and new_element is not None and \
                    _facet_text(old_element.facets) != _facet_text(new_element.facets):
                if legality:
                    _item(items, human=human, change_id=change.id, term=path, finding="base_changed", severity="error",
                          choices=["manual", "withdraw"], default="manual",
                          message=f"The base constraint on {new.curie(path)} changed: {_facet_text(old_element.facets)} "
                                  f"({old.base.info.title}) -> {_facet_text(new_element.facets)} ({to_base}), and the "
                                  f"change is no longer a legal refinement: " + "; ".join(r.message for r in legality))
                else:
                    _item(items, human=human, change_id=change.id, term=path, finding="base_changed", severity="info",
                          choices=["keep", "manual"], default="keep",
                          message=f"The base constraint on {new.curie(path)} changed: {_facet_text(old_element.facets)} "
                                  f"-> {_facet_text(new_element.facets)}; the change is still a legal refinement.")
            deprecated = new.base.deprecation(target, path)
            if deprecated and deprecated.get("kind") == "deprecated":
                replacement = deprecated.get("replacement") or None
                _item(items, human=human, change_id=change.id, term=path, finding="deprecated_by_base", severity="error",
                      choices=(["replace"] if replacement else []) + ["keep", "manual"],
                      default="replace" if replacement else "manual", replacement=replacement,
                      message=f"{to_base} deprecates {new.curie(path)} on {new.curie(target)}"
                              + (f"; use {new.curie(replacement)}." if replacement else f": {deprecated.get('message')}"))

        # 2. the DCAT terms the change uses, in the old and the new DCAT
        for iri in dict.fromkeys(v for v in (target, path, change.facets.range_class) if v and new.dcat.is_dcat(v)):
            before, after = old.dcat_status(iri), new.dcat_status(iri)
            if before == after:
                continue
            if before == "later" and after in ("current", "adopted"):
                _item(items, human=human, change_id=change.id, term=iri, finding="dcat_now_current", severity="info",
                      choices=["keep"], default="keep",
                      message=f"{new.curie(iri)} is part of {new.dcat.label}, the DCAT {to_base} builds on "
                              f"(it was later than {old.dcat.label}).")
            elif after == "later":
                default = {"review": "manual", "forbid": "withdraw", "allow": "keep"}[policy]
                _item(items, human=human, change_id=change.id, term=iri, finding="dcat_now_later",
                      severity="error" if policy == "forbid" else "warning",
                      choices=["manual", "keep", "withdraw"], default=default,
                      message=f"{new.curie(iri)} is not defined by {new.dcat.label}, the DCAT {to_base} builds on "
                              f"(introduced in {new.dcat.describe_version(new.dcat.introduced_in(iri))}).")
            elif after in ("deprecated", "removed"):
                replacement = new.dcat.replacement_for(iri)
                _item(items, human=human, change_id=change.id, term=iri, finding="dcat_outdated", severity="error",
                      choices=(["replace"] if replacement else []) + ["keep", "manual"],
                      default="replace" if replacement else "manual", replacement=replacement,
                      message=f"{new.curie(iri)} is {after} in {new.dcat.label}"
                              + (f"; use {new.curie(replacement)}." if replacement else "."))

        # 3. a minted term with a counterpart in the new base or its DCAT (reuse first: a human decides)
        if change.kind in ("mint_property", "mint_class"):
            counterpart = _counterpart(change, new)
            if counterpart:
                _item(items, human=human, change_id=change.id, term=change.path or change.target_class,
                      finding="mint_now_reusable", severity="warning", choices=["manual", "replace", "keep"],
                      default="manual", replacement=counterpart,
                      message=f"{new.curie(change.path or change.target_class)} was minted; {to_base} or "
                              f"{new.dcat.label} offers {new.curie(counterpart)}.")

        # 4. the target class
        if not new.is_minted(target) and old.base.has_class(target) and not new.base.has_class(target):
            _item(items, human=human, change_id=change.id, term=target, finding="class_not_in_base", severity="warning",
                  choices=["keep", "manual"], default="keep", message=f"{new.curie(target)} is not a class of {to_base}.")

    # 5. atoms: intake under the new base, and "covered by the base" claims (check B1 against the new base)
    stored = {assessment.atom_id: assessment for assessment in assessments}
    fresh = {assessment.atom_id: assessment for assessment in run_intake(
        [atom for atom in atoms_by_id.values() if atom.active], new)}
    for atom_id, now in fresh.items():
        before = stored.get(atom_id)
        if before is None:
            continue
        human = before.provenance.author_type == "human"
        if (before.resource_class or None) != (now.resource_class or None):
            _item(items, human=human, atom_id=atom_id, term=now.resource_class, finding="intake_changed",
                  severity="warning", choices=["repropose", "manual"], default="repropose",
                  message=f"Under {to_base} the subject of {atom_id} maps to "
                          f"{new.curie(now.resource_class) if now.resource_class else 'no class'} "
                          f"(was {old.curie(before.resource_class) if before.resource_class else 'no class'}).")
            continue
        if before.disposition == "covered_by_base":
            failures = [r for r in verify_assessment(before, atoms_by_id[atom_id], new) if not r.passed]
            if failures:
                gone = any(r.details.get("problem") in ("not_in_base", "no_element") for r in failures)
                _item(items, human=human, atom_id=atom_id,
                      term=before.covered_by[0].path if before.covered_by else None,
                      finding="covered_claim_lost" if gone else "covered_claim_weakened", severity="warning",
                      choices=["repropose", "keep_claim", "manual"], default="repropose",
                      message=f"{atom_id} was covered by {old.base.info.title}; under {to_base}: "
                              + "; ".join(r.message for r in failures))
    return items


def summarise(items: list[RebaseItem], old: KnowledgeBase, new: KnowledgeBase) -> str:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.finding] = counts.get(item.finding, 0) + 1
    moved = f"{old.base.info.title} (on {old.dcat.label}) -> {new.base.info.title} (on {new.dcat.label})"
    if not items:
        return f"{moved}: nothing is affected."
    return f"{moved}: " + ", ".join(f"{count} {finding.replace('_', ' ')}" for finding, count in sorted(counts.items())) + "."
