"""Stage ``retrieve``: the reusable terms the proposer may choose from, per atom.

Retrieval bounds term choice: the proposer picks from what is retrieved here
(or mints, and then has to say why none of these fits). Four sources are
merged, in this order of trust:

1. elements the BASE profile already defines on the atom's class, scored in the
   wording the base uses for that class (they decide "covered by base" and
   "refine");
2. properties the DCAT version the base builds on lists for the class (in the
   wording of that DCAT specification) that the base does not profile there;
   DCAT-AP 3.x states that such a property is an optional field of the class;
3. properties from the vocabulary index, scored lexically and adjusted by
   whether their declared domain fits the class; DCAT terms that only a LATER
   DCAT version defines are ranked down and marked (the verifier's D1 sends
   them to a human);
4. a few classes, as possible ranges or as classes to bring into the profile.

Everything is deterministic and explained (``Candidate.why``).
"""
from __future__ import annotations

from ..contracts import Atom, AtomAssessment, Candidate
from ..iri import local_name
from ..knowledge import KnowledgeBase
from ..knowledge.vocab_index import tokenize

# Verbs and nouns that occur in almost every requirement and say nothing about WHICH
# information is needed. They are removed from the query (the full wording is still
# used as a fallback when too little is found without them).
GENERIC_WORDS = frozenset(tokenize(
    "state states name names indicate indicates provide provides give gives record records list lists "
    "identify identifies link links describe describes specify specifies include includes contain contains "
    "mention declare show tell document capture express carry make available able possible "
    "dataset datasets distribution distributions catalogue catalog data service resource metadata information "
    "kind kinds type types every each"
))
STRUCTURAL_VOCABULARIES = frozenset({"rdf", "rdfs", "owl", "sh", "xsd"})

BASE_ON_CLASS_BOOST = 1.6     # the base already constrains this path on the atom's class
DCAT_ON_CLASS_BOOST = 1.4     # the base's DCAT lists this path for the atom's class (the base does not profile it)
LATER_DCAT_FACTOR = 0.5       # a DCAT term only a later DCAT version defines
REMOVED_DCAT_FACTOR = 0.3     # a DCAT term only an earlier DCAT version defines
BASE_ELSEWHERE_BOOST = 1.15   # the base uses the term, on another class
DOMAIN_FIT_BOOST = 1.25       # the vocabulary declares a domain that fits the class
DOMAIN_MISFIT_FACTOR = 0.4    # the vocabulary declares a domain that does not fit
# Vocabularies made for a specific domain (legislation, software licences, rights policies, time,
# addresses) match generic requirement words by accident; they are offered, but ranked lower.
SPECIALISED_VOCABULARIES = {"eli": 0.4, "spdx": 0.4, "odrl": 0.5, "time": 0.6, "locn": 0.6, "vcard": 0.5}
# Reuse ladder: a base element on the atom's class that matches reasonably well is offered before
# vocabulary terms (reuse the base element > tighten it > reuse another term > mint).
BASE_FIRST_SHARE = 0.35
RANGE_MATCH_FACTOR = 0.8      # a base property found through its range class
MAX_CLASS_CANDIDATES = 3


def query_tokens(atom: Atom) -> tuple[list[str], list[str]]:
    """(focused tokens, all tokens) of an atom's statement. Generic requirement wording is dropped
    from the focused tokens unless nothing else is left."""
    everything = list(dict.fromkeys(tokenize(atom.statement)))
    focused = [token for token in everything if token not in GENERIC_WORDS]
    return focused or everything, everything


def _domain_fit(kb: KnowledgeBase, domain: list[str], resource_class: str | None) -> bool | None:
    """True/False when the term declares a domain and we know the class; None when it cannot be judged."""
    if not domain or not resource_class:
        return None
    return any(kb.is_subclass_of(resource_class, declared) for declared in domain)


def dcat_listing_note(kb: KnowledgeBase, resource_class: str, listed_on: str) -> str:
    """'DCAT 2014 lists it for dcat:Dataset; DCAT-AP 1.1 does not profile it there'."""
    where = kb.curie(listed_on) + (f" (and so for {kb.curie(resource_class)})" if listed_on != resource_class else "")
    if kb.dcat.basis.unlisted_dcat_properties == "optional":
        tail = f"{kb.base.info.title} does not list it, so it is an optional field there"
    else:
        tail = f"{kb.base.info.title} does not profile it there"
    return f"{kb.dcat.label} lists it for {where}; {tail}"


def dcat_status_note(kb: KnowledgeBase, iri: str) -> tuple[str, float]:
    """(reason, score factor) for a DCAT term that is not part of the DCAT version the base builds on."""
    status = kb.dcat_status(iri)
    if status == "later":
        since = kb.dcat.introduced_in(iri) or ""
        return (f"introduced in {kb.dcat.describe_version(since)}, after {kb.dcat.label} that {kb.base.info.title} "
                f"builds on: a human decides", LATER_DCAT_FACTOR)
    if status == "removed":
        return f"only in DCAT versions before {kb.dcat.label}", REMOVED_DCAT_FACTOR
    if status == "deprecated":
        return f"deprecated in {kb.dcat.label}", 1.0
    return "", 1.0


def retrieve_candidates(
    atom: Atom,
    assessment: AtomAssessment | None,
    kb: KnowledgeBase,
    *,
    top_k: int = 8,
    use_hints: bool = False,
) -> list[Candidate]:
    resource_class = assessment.resource_class if assessment else kb.base.class_for_subject(atom.subject)
    focused, everything = query_tokens(atom)
    scored: dict[str, Candidate] = {}

    # 1. Base elements on the atom's class, in the wording the base uses for that class.
    if resource_class:
        for element in kb.base.elements(resource_class):
            score, matched = kb.vocab.score_text(
                focused, label=element.label, name=local_name(element.path), definition=element.definition
            )
            if score <= 0:
                continue
            term = kb.term(element.path)
            scored[element.path] = Candidate(
                iri=element.path,
                curie=kb.curie(element.path),
                kind="property",
                label=element.label,
                definition=element.definition,
                vocabulary=kb.prefixes.prefix_of(element.path) or "",
                domain=list(term.domain) if term else [],
                range=[value for value in (element.facets.range_class, element.facets.range_datatype) if value],
                score=round(score * BASE_ON_CLASS_BOOST, 4),
                in_base_on_class=True,
                base_classes=kb.base.classes_using(element.path),
                base_facets=element.facets,
                matched=list(matched),
                why=f"base profile defines it on {kb.curie(resource_class)}; matched: {', '.join(matched)}",
            )

    # 2. Properties the base's DCAT lists for the class, which the base does not profile there.
    if resource_class:
        for listed in kb.dcat.properties_for(resource_class):
            if listed.path in scored or kb.base.element(resource_class, listed.path) is not None:
                continue
            score, matched = kb.vocab.score_text(
                focused, label=listed.label, name=local_name(listed.path),
                definition=" ".join(part for part in (listed.definition, listed.usage_note) if part),
            )
            if score <= 0:
                continue
            term = kb.term(listed.path)
            scored[listed.path] = Candidate(
                iri=listed.path, curie=kb.curie(listed.path), kind="property",
                label=listed.label or (term.label if term else ""),
                definition=listed.definition or (term.definition if term else ""),
                vocabulary=kb.prefixes.prefix_of(listed.path) or (term.vocabulary if term else ""),
                domain=list(term.domain) if term else [],
                range=list(listed.range) or (list(term.range) if term else []),
                score=round(score * DCAT_ON_CLASS_BOOST, 4), base_classes=kb.base.classes_using(listed.path),
                dcat_listed_on_class=True, dcat_status=kb.dcat_status(listed.path), matched=list(matched),
                why=f"{dcat_listing_note(kb, resource_class, listed.listed_on)}; matched: {', '.join(matched)}",
            )

    # 3. Properties of the vocabulary index.
    def add_property_hits(tokens: list[str], weight: float) -> None:
        for hit in kb.vocab.search(" ".join(tokens), kind="property", limit=top_k * 4):
            term = hit.term
            if term.vocabulary in STRUCTURAL_VOCABULARIES or term.iri in scored:
                continue
            score, reasons = hit.score * weight, [f"matched: {', '.join(hit.matched)}"]
            prior = SPECIALISED_VOCABULARIES.get(term.vocabulary)
            if prior is not None:
                score *= prior
                reasons.append(f"specialised vocabulary ({term.vocabulary})")
            used_on = kb.base.classes_using(term.iri)
            if used_on:
                score *= BASE_ELSEWHERE_BOOST
                reasons.append(f"used by the base on {', '.join(kb.curie(cls) for cls in used_on[:3])}")
            fit = _domain_fit(kb, term.domain, resource_class)
            if fit is True:
                score *= DOMAIN_FIT_BOOST
                reasons.append("declared domain fits the class")
            elif fit is False:
                score *= DOMAIN_MISFIT_FACTOR
                reasons.append(f"declared domain is {', '.join(kb.curie(d) for d in term.domain[:2])}")
            if term.deprecated and kb.dcat.status(term.iri) != "deprecated":
                reasons.append("deprecated")
            note, factor = dcat_status_note(kb, term.iri)
            if note:
                score *= factor
                reasons.append(note)
            deprecated = kb.base.deprecation(resource_class, term.iri) if resource_class else None
            if deprecated and deprecated.get("kind") == "deprecated":
                score *= REMOVED_DCAT_FACTOR
                replacement = deprecated.get("replacement")
                reasons.append(f"deprecated by {kb.base.info.title}" + (f": use {kb.curie(replacement)}" if replacement else ""))
            listed = kb.dcat.listed_for(resource_class, term.iri) if resource_class else None
            if listed is not None and kb.base.element(resource_class, term.iri) is None:
                score *= DCAT_ON_CLASS_BOOST
                reasons.append(dcat_listing_note(kb, resource_class, listed.listed_on))
            # The base may define the path on this very class in words that did not match the atom.
            on_class = kb.base.element(resource_class, term.iri) if resource_class else None
            if on_class is not None:
                score *= BASE_ON_CLASS_BOOST / BASE_ELSEWHERE_BOOST
                reasons.insert(0, f"base profile defines it on {kb.curie(resource_class)}")
            scored[term.iri] = Candidate(
                iri=term.iri, curie=kb.curie(term.iri), kind="property",
                label=on_class.label if on_class else term.label,
                definition=on_class.definition if on_class else term.definition,
                vocabulary=term.vocabulary, domain=list(term.domain), range=list(term.range),
                score=round(score, 4), in_base_on_class=on_class is not None, base_classes=used_on,
                base_facets=on_class.facets if on_class else None, matched=list(hit.matched),
                dcat_listed_on_class=listed is not None and on_class is None, dcat_status=kb.dcat_status(term.iri),
                why="; ".join(reasons),
            )

    add_property_hits(focused, 1.0)

    # 4. A few classes (possible ranges, or classes to bring into the profile).
    classes: list[Candidate] = []
    for hit in kb.vocab.search(" ".join(focused), kind="class", limit=MAX_CLASS_CANDIDATES * 3):
        term = hit.term
        if term.vocabulary in STRUCTURAL_VOCABULARIES or term.deprecated:
            continue
        in_base = kb.base.has_class(term.iri)
        prior = 1.0 if in_base else SPECIALISED_VOCABULARIES.get(term.vocabulary, 1.0)
        note, factor = dcat_status_note(kb, term.iri)
        classes.append(Candidate(
            iri=term.iri, curie=kb.curie(term.iri), kind="class", label=term.label, definition=term.definition,
            vocabulary=term.vocabulary,
            score=round(hit.score * (BASE_ELSEWHERE_BOOST if in_base else prior) * factor, 4),
            base_classes=[term.iri] if in_base else [], matched=list(hit.matched), dcat_status=kb.dcat_status(term.iri),
            why=f"matched: {', '.join(hit.matched)}" + ("; class of the base profile" if in_base else "")
                + (f"; {note}" if note else ""),
        ))
    classes = sorted(classes, key=lambda candidate: (-candidate.score, candidate.iri))[:MAX_CLASS_CANDIDATES]

    # A matching class often points at the property that leads to it: when the base already has a
    # property on the atom's class whose range is that class, offer the property too.
    if resource_class:
        for class_candidate in classes:
            for element in kb.base.elements(resource_class):
                if element.facets.range_class != class_candidate.iri:
                    continue
                via_range = round(class_candidate.score * RANGE_MATCH_FACTOR, 4)
                known = scored.get(element.path)
                if known is not None:
                    if via_range > known.score:
                        known.score = via_range
                        known.matched = sorted(set(known.matched) | set(class_candidate.matched))
                        known.why += f"; its range {class_candidate.curie} matched the atom"
                    continue
                term = kb.term(element.path)
                scored[element.path] = Candidate(
                    iri=element.path, curie=kb.curie(element.path), kind="property", label=element.label,
                    definition=element.definition, vocabulary=kb.prefixes.prefix_of(element.path) or "",
                    domain=list(term.domain) if term else [], range=[class_candidate.iri],
                    score=via_range, in_base_on_class=True,
                    base_classes=kb.base.classes_using(element.path), base_facets=element.facets,
                    matched=list(class_candidate.matched),
                    why=f"base profile defines it on {kb.curie(resource_class)}; its range {class_candidate.curie} "
                        f"matched the atom",
                )

    best = max((candidate.score for candidate in scored.values()), default=0.0)
    properties = sorted(scored.values(), key=lambda candidate: (
        0 if candidate.in_base_on_class and candidate.score >= BASE_FIRST_SHARE * best else 1,
        -candidate.score, candidate.iri,
    ))[:top_k]

    # Optional: vocabulary terms an upstream extraction observed. Off by default (answer-in-input risk).
    hinted: list[Candidate] = []
    if use_hints:
        known = {candidate.iri for candidate in properties + classes}
        for hint in atom.hints:
            iri = kb.expand(hint)
            term = kb.term(iri)
            if term is None or term.iri in known:
                continue
            hinted.append(Candidate(
                iri=term.iri, curie=kb.curie(term.iri), kind=term.kind, label=term.label, definition=term.definition,
                vocabulary=term.vocabulary, domain=list(term.domain), range=list(term.range), score=0.0,
                base_classes=kb.base.classes_using(term.iri), why="observed upstream (hint)",
            ))

    candidates = properties + classes + hinted
    for rank, candidate in enumerate(candidates, start=1):
        candidate.rank = rank
    return candidates
