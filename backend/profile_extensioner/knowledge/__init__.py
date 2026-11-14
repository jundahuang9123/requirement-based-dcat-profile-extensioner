"""The symbolic knowledge base: vocabulary index + base profile + the project's own namespace."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from ..contracts import DcatBasis, Term
from ..iri import MINT_PREFIX, Prefixes, is_absolute_iri, is_valid_local_name
from .base_profile import DATA_DIR, BaseProfile, latest_base_profile_id, list_base_profiles, load_base_profile
from .dcat_state import (
    DCAT_NS, DcatProperty, DcatState, dcat_rdf_path, latest_dcat_version, list_dcat_versions, load_dcat_state,
)
from .vocab_index import SearchHit, VocabularyIndex, VocabularyInfo, terms_from_graph

__all__ = [
    "DATA_DIR", "DCAT_NS", "BaseProfile", "DcatProperty", "DcatState", "KnowledgeBase", "SearchHit",
    "VocabularyIndex", "VocabularyInfo", "latest_base_profile_id", "latest_dcat_version", "list_base_profiles",
    "list_dcat_versions", "load_base_profile", "load_dcat_state", "load_knowledge_base",
]


@dataclass
class KnowledgeBase:
    """Everything symbolic a run may consult. One instance per project (cheap: the heavy parts are shared)."""

    vocab: VocabularyIndex
    base: BaseProfile
    prefixes: Prefixes
    profile_namespace: str
    profile_prefix: str
    dcat: DcatState            # the W3C DCAT version the base builds on

    def curie(self, iri: str | None) -> str:
        return self.prefixes.compact(iri)

    def expand(self, value: str | None) -> str | None:
        """Expand a CURIE or a ``NEW:localName`` marker; absolute IRIs pass through; None if not expandable."""
        if not value:
            return None
        value = value.strip()
        if value.startswith(f"{MINT_PREFIX}:"):
            local = value.split(":", 1)[1].strip()
            return f"{self.profile_namespace}{local}" if is_valid_local_name(local) else None
        if is_absolute_iri(value):
            return value
        return self.prefixes.expand(value)

    def is_mint_marker(self, value: str | None) -> bool:
        return bool(value) and value.strip().startswith(f"{MINT_PREFIX}:")

    def is_minted(self, iri: str | None) -> bool:
        """True for an IRI in the profile's own namespace."""
        return bool(iri) and iri.startswith(self.profile_namespace)

    def term(self, iri: str | None) -> Term | None:
        return self.vocab.get(iri)

    def is_subclass_of(self, sub: str, sup: str) -> bool:
        return self.vocab.is_subclass_of(sub, sup)

    def dcat_status(self, iri: str | None) -> str:
        """``DcatState.status`` for this base: a later DCAT term the base itself already uses is
        ``adopted`` (the base made that choice; DCAT-AP 1.2.1's shapes use DCAT 2's dcat:startDate)."""
        status = self.dcat.status(iri)
        if status == "later" and iri and self.base.uses_term(iri):
            return "adopted"
        return status


def dcat_state_for(base: BaseProfile, data_dir: Path | None = None) -> DcatState:
    """The DCAT state of a base. A base without ``dcat_basis`` is taken to build on the newest DCAT."""
    root = data_dir or DATA_DIR
    basis = base.info.dcat or DcatBasis(dcat=latest_dcat_version(root).id,
                                       notes=["profile.yaml names no DCAT version; the newest one is assumed"])
    return load_dcat_state(basis, root)


def _dcat_terms(state: DcatState, root: Path) -> list:
    """The DCAT terms as the pinned version defines them, plus the terms only later versions define
    (marked ``later``, so that the verifier can name the version that introduced them)."""
    from rdflib import Graph

    by_version: dict[str, list[Term]] = {}
    for version in state.order:
        path = dcat_rdf_path(root, version)
        if not path.exists():
            continue
        graph = Graph()
        graph.parse(path, format="turtle")
        by_version[version] = terms_from_graph(graph, DCAT_NS, "dcat", source=f"data/dcat/{version}/dcat.ttl")
    terms: dict[str, Term] = {}
    for term in by_version.get(state.id, []):
        terms[term.iri] = term
    for version in reversed(state.order):          # a later term is described as its newest version describes it
        if not state.is_later(version):
            continue
        for term in by_version.get(version, []):
            terms.setdefault(term.iri, term)
    for version in state.order:                    # terms only earlier versions define
        for term in by_version.get(version, []):
            terms.setdefault(term.iri, term)
    for term in terms.values():
        term.dcat_status = state.status(term.iri)
        term.dcat_since = state.introduced_in(term.iri) or ""
        if term.dcat_status == "deprecated":
            term.deprecated = True
    return list(terms.values())


@lru_cache(maxsize=32)
def _shared_index(base_profile_id: str, data_dir: str, excluded: tuple[str, ...]) -> VocabularyIndex:
    root = Path(data_dir) if data_dir else DATA_DIR
    index = VocabularyIndex.load(root / "vocab", exclude_namespaces=excluded)
    base = load_base_profile(base_profile_id, Path(data_dir) if data_dir else None)
    if not any(DCAT_NS.startswith(namespace) for namespace in excluded):
        state = dcat_state_for(base, root)
        index.add_terms(_dcat_terms(state, root), overwrite=True)
        index.register_vocabulary(VocabularyInfo(
            prefix="dcat", namespace=DCAT_NS, title=state.version.title, source=state.version.tr,
            version=state.id, licence="W3C Document License", file=f"dcat/{state.id}/dcat.ttl",
        ))
    base_terms = [
        term for term in base.terms()
        if not any(term.iri.startswith(namespace) for namespace in excluded)
    ]
    index.add_terms(base_terms)
    return index


def load_knowledge_base(
    base_profile_id: str,
    *,
    profile_namespace: str,
    profile_prefix: str,
    exclude_namespaces: Sequence[str] = (),
    data_dir: Path | None = None,
) -> KnowledgeBase:
    """Assemble the knowledge base for one project.

    ``exclude_namespaces`` hides whole namespaces from the vocabulary index (the
    held-out-answer rule of benchmark runs). The base profile itself is never hidden.
    """
    base = load_base_profile(base_profile_id, data_dir)
    index = _shared_index(base_profile_id, str(data_dir or ""), tuple(sorted(exclude_namespaces)))
    prefixes = Prefixes(base.prefixes.as_dict())
    prefixes.bind(profile_prefix, profile_namespace)
    return KnowledgeBase(
        vocab=index, base=base, prefixes=prefixes,
        profile_namespace=profile_namespace, profile_prefix=profile_prefix,
        dcat=dcat_state_for(base, data_dir),
    )
