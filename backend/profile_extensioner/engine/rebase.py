"""Rebase: move an extension onto another base profile, and so possibly onto another DCAT version.

A DCAT-AP release builds on one W3C DCAT state (DCAT-AP 1.1: DCAT 2014; 2.x: DCAT 2; 3.x: DCAT 3).
When the base of an extension moves (a new DCAT-AP release, or a different one), every change is
looked at again against the new base and the new DCAT:

* does the new base now define the element itself (the change may be redundant), drop it, or
  constrain it differently;
* is a DCAT term the change uses now part of the base's DCAT, no longer part of it, or outdated;
* does the new base deprecate a term (DCAT-AP 3.x: dct:hasVersion -> dcat:hasVersion);
* does a minted term now have a counterpart in the new base or its DCAT;
* does an atom the old base covered stay covered.

The findings are a review queue with a default suggestion each (keep, withdraw, replace, review,
repropose). Nothing a human decided is overwritten: a machine-decided change with a finding that
needs a decision goes to ``needs_review``; a human-decided change keeps its decision and carries
the finding as a note. The pipeline then re-verifies every change against the new base.
"""
from __future__ import annotations

from typing import Iterable

from ..contracts import OBLIGATION_RANK, AtomAssessment, ProfileChange, RebaseItem
from ..iri import local_name
from ..knowledge import KnowledgeBase


def _adds_nothing(change: ProfileChange, base_facets) -> bool:
    """True when the change asks for nothing beyond what the base element already says."""
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


def _facet_text(facets) -> str:
    parts = [facets.obligation]
    parts.append(f"{facets.min_count or 0}..{'n' if facets.max_count is None else facets.max_count}")
    if facets.range_class or facets.range_datatype:
        parts.append(local_name(facets.range_class or facets.range_datatype))
    return "; ".join(parts)


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
        if local_name(iri).lower() == name or (label and term is not None and term.label.strip().lower() == label):
            return iri
    return None


def analyse_rebase(
    changes: Iterable[ProfileChange],
    assessments: Iterable[AtomAssessment],
    old: KnowledgeBase,
    new: KnowledgeBase,
) -> list[RebaseItem]:
    items: list[RebaseItem] = []
    to_base = new.base.info.title
    for change in changes:
        if change.decision.status in ("superseded", "rejected"):
            continue
        target, path = change.target_class, change.path

        # 1. the element itself, in the old and the new base
        if path and not change.is_class_change:
            old_element, new_element = old.base.element(target, path), new.base.element(target, path)
            if new_element is not None and old_element is None:
                redundant = _adds_nothing(change, new_element.facets)
                items.append(RebaseItem(
                    change_id=change.id, term=path, finding="now_in_base",
                    severity="warning" if redundant else "info", suggestion="withdraw" if redundant else "keep",
                    message=f"{to_base} defines {new.curie(path)} on {new.curie(target)} itself "
                            f"({_facet_text(new_element.facets)})"
                            + ("; the change adds nothing beyond it." if redundant else "; the change now tightens it."),
                ))
            elif old_element is not None and new_element is None:
                items.append(RebaseItem(
                    change_id=change.id, term=path, finding="base_dropped", severity="info", suggestion="keep",
                    message=f"{to_base} does not define {new.curie(path)} on {new.curie(target)}; the change is now an addition.",
                ))
            elif old_element is not None and new_element is not None and \
                    _facet_text(old_element.facets) != _facet_text(new_element.facets):
                items.append(RebaseItem(
                    change_id=change.id, term=path, finding="base_changed", severity="warning", suggestion="review",
                    message=f"The base constraint on {new.curie(path)} changed: {_facet_text(old_element.facets)} "
                            f"({old.base.info.title}) -> {_facet_text(new_element.facets)} ({to_base}).",
                ))
            deprecated = new.base.deprecation(target, path)
            if deprecated and deprecated.get("kind") == "deprecated":
                replacement = deprecated.get("replacement") or None
                items.append(RebaseItem(
                    change_id=change.id, term=path, finding="deprecated_by_base", severity="error",
                    suggestion="replace" if replacement else "review", replacement=replacement,
                    message=f"{to_base} deprecates {new.curie(path)} on {new.curie(target)}"
                            + (f"; use {new.curie(replacement)}." if replacement else f": {deprecated.get('message')}"),
                ))

        # 2. the DCAT terms the change uses, in the old and the new DCAT
        for iri in dict.fromkeys(v for v in (target, path, change.facets.range_class) if v and new.dcat.is_dcat(v)):
            before, after = old.dcat_status(iri), new.dcat_status(iri)
            if before == after:
                continue
            if before == "later" and after in ("current", "adopted"):
                items.append(RebaseItem(
                    change_id=change.id, term=iri, finding="dcat_now_current", severity="info", suggestion="keep",
                    message=f"{new.curie(iri)} is part of {new.dcat.label}, the DCAT {to_base} builds on "
                            f"(it was later than {old.dcat.label}).",
                ))
            elif after == "later":
                items.append(RebaseItem(
                    change_id=change.id, term=iri, finding="dcat_now_later", severity="warning", suggestion="review",
                    message=f"{new.curie(iri)} is not defined by {new.dcat.label}, the DCAT {to_base} builds on "
                            f"(introduced in {new.dcat.describe_version(new.dcat.introduced_in(iri))}).",
                ))
            elif after in ("deprecated", "removed"):
                replacement = new.dcat.replacement_for(iri)
                items.append(RebaseItem(
                    change_id=change.id, term=iri, finding="dcat_outdated", severity="error",
                    suggestion="replace" if replacement else "review", replacement=replacement,
                    message=f"{new.curie(iri)} is {after} in {new.dcat.label}"
                            + (f"; use {new.curie(replacement)}." if replacement else "."),
                ))

        # 3. a minted term with a counterpart in the new base or its DCAT
        if change.kind in ("mint_property", "mint_class"):
            counterpart = _counterpart(change, new)
            if counterpart:
                items.append(RebaseItem(
                    change_id=change.id, term=change.path or change.target_class, finding="mint_now_reusable",
                    severity="warning", suggestion="replace", replacement=counterpart,
                    message=f"{new.curie(change.path or change.target_class)} was minted; {to_base} or "
                            f"{new.dcat.label} offers {new.curie(counterpart)}.",
                ))

        # 4. the target class
        if not new.is_minted(target) and old.base.has_class(target) and not new.base.has_class(target):
            items.append(RebaseItem(
                change_id=change.id, term=target, finding="class_not_in_base", severity="warning", suggestion="review",
                message=f"{new.curie(target)} is not a class of {to_base}.",
            ))

    # 5. atoms the old base covered
    for assessment in assessments:
        if assessment.disposition != "covered_by_base":
            continue
        lost = [ref for ref in assessment.covered_by
                if (ref.path and new.base.element(ref.target_class, ref.path) is None)
                or (not ref.path and not new.base.has_class(ref.target_class))]
        if lost:
            names = ", ".join(f"{new.curie(ref.path)} on {new.curie(ref.target_class)}" if ref.path
                              else new.curie(ref.target_class) for ref in lost)
            items.append(RebaseItem(
                atom_id=assessment.atom_id, term=lost[0].path or lost[0].target_class, finding="covered_claim_lost",
                severity="warning", suggestion="repropose",
                message=f"{assessment.atom_id} was covered by {old.base.info.title} through {names}; "
                        f"{to_base} does not define {'it' if len(lost) == 1 else 'them'}.",
            ))
    return items


def summarise(items: list[RebaseItem], old: KnowledgeBase, new: KnowledgeBase) -> str:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.finding] = counts.get(item.finding, 0) + 1
    moved = (f"{old.base.info.title} (on {old.dcat.label}) -> {new.base.info.title} (on {new.dcat.label})")
    if not items:
        return f"Rebased {moved}: no change is affected."
    return f"Rebased {moved}: " + ", ".join(f"{count} {finding.replace('_', ' ')}" for finding, count in sorted(counts.items())) + "."
