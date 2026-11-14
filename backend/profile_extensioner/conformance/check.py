"""Does the extension still conform to the base profile it extends?

Two levels.

Profile level (static), one check per rule:
  C1  every constraint is a legal refinement of the base: added or tightened, never loosened
      (cardinality, range, node kind, value list, obligation level)
  C2  no constraint contradicts the base (data could not satisfy both)
  C3  minted terms live in the extension's own namespace and do not redefine existing terms
  C4  no term of a namespace the extension does not own is (re)defined; base terms are reused as they are
  C5  every element of the extension traces to at least one requirement atom
  C6  the compiled shapes are valid SHACL (SHACL-SHACL)
  C8  the DCAT state: every DCAT term the extension uses is a term of the DCAT version the base
      builds on (DCAT-AP 1.1: DCAT 2014; DCAT-AP 3.x: DCAT 3); deprecated or removed DCAT terms fail,
      terms of a later DCAT version (accepted by a human) are a warning

Instance level (empirical):
  C7  witness data: for every class the extension constrains, an instance that satisfies the
      extension's mandatory and recommended constraints is generated and validated with pySHACL
      against the extension shapes AND against the OFFICIAL base shapes. Data valid under the
      extension must be valid under the base.
"""
from __future__ import annotations

from datetime import date

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, SH, XSD

from ..conformance.refinement import compare_facets, compare_obligation
from ..contracts import ConformanceCheck, ConformanceItem, ConformanceReport
from ..engine.verify import check_shapes_valid
from ..knowledge.shacl_reader import ShapeFacets, read_shapes
from ..compile.model import ProfileView
from ..compile.shacl import compile_shacl_graph

SAMPLE_LITERALS = {
    str(XSD.integer): Literal(1, datatype=XSD.integer),
    str(XSD.nonNegativeInteger): Literal(1, datatype=XSD.nonNegativeInteger),
    str(XSD.positiveInteger): Literal(1, datatype=XSD.positiveInteger),
    str(XSD.decimal): Literal("1.0", datatype=XSD.decimal),
    str(XSD.double): Literal("1.0", datatype=XSD.double),
    str(XSD.boolean): Literal(True),
    str(XSD.date): Literal(date(2026, 1, 1)),
    str(XSD.dateTime): Literal("2026-01-01T00:00:00", datatype=XSD.dateTime),
    str(XSD.anyURI): Literal("https://example.org/x", datatype=XSD.anyURI),
    str(XSD.duration): Literal("P1Y", datatype=XSD.duration),
    str(XSD.gYear): Literal("2026", datatype=XSD.gYear),
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString": Literal("example", lang="en"),
}
SOURCES = {
    "C1": "DCAT-AP reuse guidelines: a profile may restrict, not relax, the base (derived rule; see docs/conformance.md)",
    "C2": "derived: constraints of base and extension must be satisfiable together",
    "C3": "DCAT-AP reuse guidelines: new terms in the profile's own namespace",
    "C4": "derived: reuse existing terms without redefining them",
    "C5": "this tool: every element traces to a requirement atom",
    "C6": "W3C SHACL, SHACL-SHACL",
    "C7": "derived: data valid under the extension is valid under the base",
    "C8": "W3C DCAT 3, section 4: a DCAT profile adds constraints to DCAT; the DCAT version is the one the base "
          "states it builds on (profile.yaml dcat_basis, data/dcat/)",
}


def dcat_state_check(view: ProfileView) -> ConformanceCheck:
    kb = view.kb
    dcat = kb.dcat
    later: list[ConformanceItem] = []
    outdated: list[ConformanceItem] = []
    for change in view.changes:
        used = [change.target_class, change.path, change.facets.range_class, change.super_class, change.sub_property_of]
        for iri in dict.fromkeys(value for value in used if value):
            status = kb.dcat_status(iri)
            if status == "later":
                since = dcat.introduced_in(iri) or ""
                later.append(ConformanceItem(
                    change_id=change.id, target_class=change.target_class, path=iri, status="later",
                    message=f"{kb.curie(iri)} is a term of {dcat.describe_version(since)} (decided by "
                            f"{change.decision.decided_by})",
                ))
            elif status in ("deprecated", "removed"):
                outdated.append(ConformanceItem(
                    change_id=change.id, target_class=change.target_class, path=iri, status=status,
                    message=f"{kb.curie(iri)} is {status} in {dcat.label}",
                ))
    basis = f"{dcat.describe_version()}, the DCAT that {kb.base.info.title} builds on"
    if not later and not outdated:
        return ConformanceCheck(id="C8", title="DCAT terms of the base's DCAT version", passed=True,
                                message=f"Every DCAT term the extension uses is a term of {basis}.", source=SOURCES["C8"])
    parts = []
    if outdated:
        parts.append(f"{len(outdated)} use(s) of a deprecated or removed DCAT term")
    if later:
        versions = sorted({item.message.split(" is a term of ")[1].split(" (")[0] for item in later})
        parts.append(f"{len(later)} use(s) of DCAT terms beyond {dcat.label} (from {', '.join(versions)})")
    return ConformanceCheck(
        id="C8", title="DCAT terms of the base's DCAT version", passed=False,
        severity="error" if outdated else "warning",
        message=f"{'; '.join(parts)}. The base builds on {basis}.", source=SOURCES["C8"], items=outdated + later,
    )


def _merged_shapes(view: ProfileView) -> Graph:
    graph = Graph()
    for triple in view.kb.base.shapes_graph():
        graph.add(triple)
    for triple in compile_shacl_graph(view, include_trace=False):
        graph.add(triple)
    return graph


def static_checks(view: ProfileView) -> tuple[list[ConformanceCheck], dict[str, int]]:
    kb, checks = view.kb, []
    loosened, conflicts, counts = [], [], {"added": 0, "tightened": 0, "unchanged": 0, "loosened": 0}
    for change in view.property_changes:
        base_shape = kb.base.shape_facets(change.target_class, change.path)
        # The base element may exist in the specification only (an obligation, no official shape, DCAT-AP 1.x):
        # its obligation still counts.
        in_base = base_shape is not None or kb.base.element(change.target_class, change.path) is not None
        comparison = compare_facets(base_shape, ShapeFacets.from_facets(change.facets, change.severity),
                                    inherit_missing=True, is_subclass=kb.is_subclass_of, compare_severity=False)
        deltas = list(comparison.facets)
        ob = compare_obligation(kb.base.obligation(change.target_class, change.path) if in_base else None,
                                change.facets.obligation)
        if ob:
            deltas.append(ob)
        status = "added" if not in_base else "tightened"
        for delta in deltas:
            item = ConformanceItem(target_class=change.target_class, path=change.path, change_id=change.id,
                                   facet=delta.facet, base_value=delta.base_value, new_value=delta.new_value,
                                   status=delta.status, message=delta.note)
            if delta.status == "loosened":
                loosened.append(item)
                status = "loosened"
            elif delta.status == "conflict":
                conflicts.append(item)
                status = "loosened"
        if in_base and status != "loosened" and not any(
                d.status in ("added", "tightened", "incomparable", "loosened", "conflict") for d in deltas):
            status = "unchanged"
        counts[status] += 1

    checks.append(ConformanceCheck(
        id="C1", title="Only legal refinements of the base", passed=not loosened, source=SOURCES["C1"],
        message="No constraint loosens the base." if not loosened else f"{len(loosened)} constraint(s) loosen the base.",
        items=loosened,
    ))
    checks.append(ConformanceCheck(
        id="C2", title="No contradiction with the base", passed=not conflicts, source=SOURCES["C2"],
        message="All constraints are satisfiable together with the base." if not conflicts
        else f"{len(conflicts)} constraint(s) cannot hold together with the base.", items=conflicts,
    ))

    bad_mints = []
    for change in view.changes:
        iri = change.target_class if change.kind == "mint_class" else change.path if change.kind == "mint_property" else None
        if iri and (not kb.is_minted(iri) or kb.term(iri) is not None):
            bad_mints.append(ConformanceItem(change_id=change.id, path=iri, message="minted outside the profile namespace or re-minting an existing term"))
    checks.append(ConformanceCheck(
        id="C3", title="New terms in the extension's own namespace", passed=not bad_mints, source=SOURCES["C3"],
        message=f"{sum(1 for c in view.changes if c.kind.startswith('mint'))} minted term(s), all in {view.project.profile_namespace}."
        if not bad_mints else "Some minted terms are misplaced.", items=bad_mints,
    ))

    redefined = []
    for change in view.property_changes:
        if change.kind != "mint_property" and kb.term(change.path) is None and not kb.is_minted(change.path):
            redefined.append(ConformanceItem(change_id=change.id, path=change.path, message="unknown term used as if it existed"))
    checks.append(ConformanceCheck(
        id="C4", title="Existing terms reused as they are", passed=not redefined, source=SOURCES["C4"],
        message="Every reused term exists in the vocabulary index." if not redefined else "Unknown terms are used.",
        items=redefined,
    ))

    untraced = [ConformanceItem(change_id=c.id, path=c.path, target_class=c.target_class, message="no requirement atom")
                for c in view.changes if not c.covers or any(
                    l.atom_id not in view.atoms or not view.atoms[l.atom_id].active for l in c.covers)]
    checks.append(ConformanceCheck(
        id="C5", title="Every element traces to a requirement", passed=not untraced, source=SOURCES["C5"],
        message="Every element names the atoms it covers." if not untraced else f"{len(untraced)} element(s) without a valid atom.",
        items=untraced,
    ))
    return checks, counts


def _value_for(facets: ShapeFacets, graph: Graph, depth: int, all_shapes, counter: list[int]):
    if facets.in_values:
        value = sorted(facets.in_values)[0]
        return URIRef(value) if not value.startswith('"') else Literal(value.strip('"'))
    if facets.datatypes:
        datatype = sorted(facets.datatypes)[0]
        if datatype in SAMPLE_LITERALS:
            return SAMPLE_LITERALS[datatype]
        return Literal("example") if datatype == str(XSD.string) else Literal("example", datatype=URIRef(datatype))
    if facets.classes:
        cls = sorted(facets.classes)[0]
        counter[0] += 1
        node = URIRef(f"https://example.org/witness/{counter[0]}")
        graph.add((node, RDF.type, URIRef(cls)))
        if depth < 3:
            _fill(node, cls, graph, depth + 1, all_shapes, counter)
        return node
    if facets.node_kind == "Literal":
        return Literal("example", lang="en")
    counter[0] += 1
    return URIRef(f"https://example.org/witness/{counter[0]}")


def _fill(node, cls: str, graph: Graph, depth: int, all_shapes, counter: list[int]) -> None:
    for (target, path), facets in all_shapes.elements.items():
        if target != cls or (facets.min_count or 0) < 1:
            continue
        for _ in range(facets.min_count or 1):
            graph.add((node, URIRef(path), _value_for(facets, graph, depth, all_shapes, counter)))


def witness_check(view: ProfileView) -> tuple[ConformanceCheck, str]:
    from pyshacl import validate

    merged = _merged_shapes(view)
    all_shapes = read_shapes(merged)
    data, counter = Graph(), [0]
    for target in view.target_classes():
        counter[0] += 1
        node = URIRef(f"https://example.org/witness/{counter[0]}")
        data.add((node, RDF.type, URIRef(target)))
        _fill(node, target, data, 0, all_shapes, counter)

    def run(shapes: Graph) -> tuple[bool, list[str]]:
        conforms, report, _ = validate(data, shacl_graph=shapes, inference="none", allow_warnings=True, advanced=False)
        messages = []
        for result in report.subjects(RDF.type, SH.ValidationResult):
            path = report.value(result, SH.resultPath)
            message = report.value(result, SH.resultMessage)
            messages.append(f"{view.kb.curie(str(path)) if path else '?'}: {message}")
        return bool(conforms), messages

    ext_ok, ext_messages = run(merged)
    base_ok, base_messages = run(view.kb.base.shapes_graph())
    items = [ConformanceItem(message=f"extension: {m}") for m in ext_messages[:20]] + \
            [ConformanceItem(message=f"base: {m}") for m in base_messages[:20]]
    if ext_ok and base_ok:
        message = f"A generated witness ({len(data)} triples) satisfies the extension and the official base shapes."
        passed, severity = True, "error"
    elif not ext_ok:
        message = "No valid witness could be generated for the extension; its constraints may be unsatisfiable or need values the generator cannot invent."
        passed, severity = False, "warning"
    else:
        message = "Data valid under the extension is INVALID under the base shapes."
        passed, severity = False, "error"
    return ConformanceCheck(id="C7", title="Witness data valid under extension and base", passed=passed,
                            severity=severity, message=message, source=SOURCES["C7"], items=items), data.serialize(format="turtle")


def check_conformance(view: ProfileView, shacl_text: str | None = None) -> ConformanceReport:
    checks, counts = static_checks(view)
    from ..compile.shacl import compile_shacl

    v6 = check_shapes_valid(shacl_text or compile_shacl(view))
    checks.append(ConformanceCheck(id="C6", title="Valid SHACL", passed=v6.passed, message=v6.message, source=SOURCES["C6"]))
    witness_turtle = ""
    try:
        c7, witness_turtle = witness_check(view)
    except Exception as exc:  # pyshacl failures must not hide the static result
        c7 = ConformanceCheck(id="C7", title="Witness data valid under extension and base", passed=False,
                              severity="warning", message=f"Witness validation could not run: {exc}", source=SOURCES["C7"])
    checks.append(c7)
    checks.append(dcat_state_check(view))
    errors = [c for c in checks if not c.passed and c.severity == "error"]
    warnings = [c for c in checks if not c.passed and c.severity == "warning"]
    verdict = "non_conformant" if errors else "conformant_with_warnings" if warnings else "conformant"
    summary = (
        f"{'Conforms' if not errors else 'Does NOT conform'} to {view.kb.base.info.title} "
        f"(on {view.kb.dcat.label}): "
        f"{counts['added']} element(s) added, {counts['tightened']} tightened, {counts['loosened']} loosened. "
        f"{len(errors)} failing rule(s), {len(warnings)} warning(s)."
    )
    _ = BNode
    return ConformanceReport(base_profile_id=view.kb.base.info.id, dcat_version=view.kb.dcat.id,  # type: ignore[arg-type]
                             verdict=verdict, summary=summary,
                             checks=checks, delta_counts=counts, witness_turtle=witness_turtle)
