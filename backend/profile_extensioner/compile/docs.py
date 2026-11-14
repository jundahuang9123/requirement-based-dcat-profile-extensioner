"""Human-readable outputs: the profile documentation and the traceability matrix."""
from __future__ import annotations

import csv
import io
from typing import Sequence

from ..contracts import AtomAssessment, AtomCoverage, ProfileChange
from ..engine.verbalise import facets_text, verbalise_change
from .model import ProfileView


def trace_rows(view: ProfileView, assessments: Sequence[AtomAssessment], coverage: dict[str, AtomCoverage],
               all_changes: Sequence[ProfileChange]) -> list[dict[str, str]]:
    """One row per (atom, element). Atoms without an element get one row that says why."""
    kb, rows = view.kb, []
    by_atom: dict[str, list[ProfileChange]] = {}
    for change in all_changes:
        if change.decision.status == "superseded":
            continue
        for atom_id in change.atom_ids:
            by_atom.setdefault(atom_id, []).append(change)
    assessed = {a.atom_id: a for a in assessments}
    for atom_id, atom in view.atoms.items():
        assessment = assessed.get(atom_id)
        changes = by_atom.get(atom_id, [])
        if not changes:
            covered = ", ".join(kb.curie(ref.path) for ref in (assessment.covered_by if assessment else []) if ref.path)
            rows.append({
                "atom_id": atom_id, "statement": atom.statement, "modality": atom.modality,
                "coverage": coverage.get(atom_id, "unaddressed"),
                "disposition": assessment.disposition if assessment else "",
                "element": covered and f"(base) {covered}", "change_kind": "", "constraints": "",
                "reason": assessment.reason if assessment else "", "status": "", "change_id": "",
            })
            continue
        for change in changes:
            link = next((l for l in change.covers if l.atom_id == atom_id), None)
            element = kb.curie(change.target_class) + (f" . {kb.curie(change.path)}" if change.path else "")
            rows.append({
                "atom_id": atom_id, "statement": atom.statement, "modality": atom.modality,
                "coverage": coverage.get(atom_id, ""), "disposition": assessment.disposition if assessment else "",
                "element": element, "change_kind": change.kind,
                "constraints": facets_text(change.facets, kb) if change.path else "",
                "reason": link.reason if link else change.rationale, "status": change.decision.status,
                "change_id": change.id,
            })
    return rows


def trace_csv(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return buffer.getvalue()


def compile_documentation(view: ProfileView, rows: list[dict[str, str]], conformance_summary: str = "") -> str:
    kb, project = view.kb, view.project
    lines = [
        f"# {project.profile_title or project.name}",
        "",
        f"An extension of **{kb.base.info.title}** generated from {len(view.atoms)} requirement atoms.",
        f"New terms live in `{project.profile_prefix}:` = <{project.profile_namespace}>.",
        "",
    ]
    if project.signoff and project.signoff.by.startswith("rule:"):
        lines += [f"**Released automatically, without human review** ({project.signoff.at}): {project.signoff.note}.", ""]
    elif project.signoff:
        lines += [f"Released by {project.signoff.by} on {project.signoff.at}. {project.signoff.note}".strip(), ""]
    else:
        lines += ["**Draft:** not yet signed off by a human reviewer.", ""]
    if project.rebases:
        lines += ["## Base history", ""]
        lines += [f"- {report.at[:10]}: {report.summary} ({report.by})" for report in project.rebases]
        lines.append("")
    lines += ["## DCAT state", "", kb.dcat.summary(kb.base.info.title)]
    if kb.dcat.basis.unlisted_dcat_properties == "optional":
        lines.append(f"By its own rule, a DCAT property that {kb.base.info.title} does not list for a class is an "
                     f"optional field of that class.")
    for item in kb.dcat.basis.evidence[:2]:
        lines.append(f"> {item.get('quote', '')} ({item.get('file', '')})")
    for note in kb.dcat.basis.notes:
        lines.append(f"Note: {note}")
    later: dict[str, set[str]] = {}
    for change in view.changes:
        for iri in (change.target_class, change.path, change.facets.range_class):
            if iri and kb.dcat_status(iri) == "later":
                later.setdefault(kb.curie(iri), set()).add(
                    "a human reviewer" if change.decision.decided_by.startswith("human:") else "the automatic policy")
    if later:
        lines.append(f"This extension uses terms of a later DCAT version than {kb.dcat.label}: "
                     + "; ".join(f"{term} (accepted by {' and '.join(sorted(who))})" for term, who in sorted(later.items()))
                     + ".")
    lines.append("")
    if conformance_summary:
        lines += ["## Conformance to the base", "", conformance_summary, ""]
    for target in view.target_classes():
        label = kb.base.class_label(target) if kb.base.has_class(target) else kb.curie(target)
        lines += [f"## {label} (`{kb.curie(target)}`)", ""]
        for change in [c for c in view.changes if c.target_class == target]:
            lines.append(f"- {verbalise_change(change, kb)}")
            for link in change.covers:
                lines.append(f"  - covers **{link.atom_id}**: {link.reason}" + (f' ("{link.evidence_quote}")' if link.evidence_quote else ""))
            for j in change.facet_justifications:
                lines.append(f"  - {j.facet}: {j.base_value or 'not set'} -> {j.new_value} ({j.status or 'n/a'}): {j.reason}")
        lines.append("")
    lines += ["## Requirement coverage", "", "| Atom | Coverage | Element | Reason |", "|---|---|---|---|"]
    for row in rows:
        reason = row["reason"].replace("|", "/").replace("\n", " ")[:160]
        lines.append(f"| {row['atom_id']} | {row['coverage']} | {row['element'] or '-'} | {reason} |")
    return "\n".join(lines) + "\n"
