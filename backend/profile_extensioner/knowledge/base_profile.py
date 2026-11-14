"""The base profile an extension is built on.

A base profile is a directory under ``data/base-profiles/<id>/``:

    profile.yaml      identity, source and licence, which shape files to read, plain-word subjects
    shacl/*.ttl       the OFFICIAL shapes of the profile, unmodified
    obligations.yaml  optional: mandatory / recommended / optional per (class, property), taken
                      from the specification text (SHACL carries only the mandatory ones)

The constraints come from the official shapes, so "the base says X" always
means "the published shapes say X".
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from rdflib import Graph, URIRef

from ..contracts import BaseClass, BaseElement, BaseProfileInfo, DcatBasis, Term
from ..iri import Prefixes, local_name, words_of
from .shacl_reader import ShapeFacets, ShapeIndex, load_graph, read_shapes

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# Plain words an atom may use for its subject -> local name of the class. Profile-specific
# words can be added in profile.yaml under ``subjects``.
DEFAULT_SUBJECTS: dict[str, str] = {
    "dataset": "dcat:Dataset",
    "data set": "dcat:Dataset",
    "distribution": "dcat:Distribution",
    "file": "dcat:Distribution",
    "catalogue": "dcat:Catalog",
    "catalog": "dcat:Catalog",
    "data catalogue": "dcat:Catalog",
    "data catalog": "dcat:Catalog",
    "data service": "dcat:DataService",
    "service": "dcat:DataService",
    "catalogue record": "dcat:CatalogRecord",
    "catalog record": "dcat:CatalogRecord",
    "record": "dcat:CatalogRecord",
    "dataset series": "dcat:DatasetSeries",
    "series": "dcat:DatasetSeries",
    "agent": "foaf:Agent",
    "publisher": "foaf:Agent",
    "organisation": "foaf:Agent",
    "organization": "foaf:Agent",
}


class BaseProfile:
    def __init__(
        self,
        info: BaseProfileInfo,
        index: ShapeIndex,
        shapes: Graph,
        *,
        obligations: dict[tuple[str, str], str] | None = None,
        class_obligations: dict[str, str] | None = None,
        class_labels: dict[str, str] | None = None,
        subjects: dict[str, str] | None = None,
        main_classes: list[str] | None = None,
        prefixes: Prefixes | None = None,
    ) -> None:
        self.info = info
        self.index = index
        self._shapes = shapes
        self._obligations = obligations or {}
        self._class_obligations = class_obligations or {}
        self._class_labels = class_labels or {}
        self._subjects = {key.lower(): value for key, value in (subjects or {}).items()}
        self.main_classes = main_classes or []
        self.prefixes = prefixes or Prefixes()
        # (class, property) pairs and classes the specification lists but the official shapes do not
        # constrain (DCAT-AP 1.1: 14 pairs, e.g. dcat:keyword on dcat:Dataset, recommended).
        self._spec_only = {key for key in self._obligations if key not in index.elements}
        self._spec_classes = ({cls for cls, _ in self._obligations} | set(self._class_obligations)) - set(index.classes)
        self.info.class_count = len(index.classes) + len(self._spec_classes)
        self.info.element_count = len(index.elements) + len(self._spec_only)

    # -- loading ------------------------------------------------------------

    @classmethod
    def load(cls, base_profile_id: str, data_dir: Path | None = None) -> "BaseProfile":
        root = (data_dir or DATA_DIR) / "base-profiles" / base_profile_id
        config_path = root / "profile.yaml"
        if not config_path.exists():
            raise KeyError(f"unknown base profile: {base_profile_id}")
        config: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        prefixes = Prefixes(config.get("prefixes") or {})
        # The base's shapes graph: the constraint shapes and the range shapes (2.1.x publish their class ranges
        # in a separate file). Files listed under shapes.not_loaded are vendored but unusable (3.0.1 ranges.ttl).
        shape_files = [root / name for name in (config.get("shapes") or {}).get("constraints", [])] + \
            [root / name for name in (config.get("shapes") or {}).get("ranges", [])]
        shapes = load_graph(shape_files)
        if config.get("implicit_class_targets"):
            # SHACL implicit class targets need the shape IRI to be an rdfs:Class; the 1.1 files omit that triple.
            # Added in memory only: the vendored files stay byte-identical to the official ones.
            from rdflib.namespace import RDF, RDFS, SH

            for shape in set(shapes.subjects(RDF.type, SH.NodeShape)):
                if isinstance(shape, URIRef) and (shape, SH.property, None) in shapes and (shape, SH.targetClass, None) not in shapes:
                    shapes.add((shape, RDF.type, RDFS.Class))
        index = read_shapes(shapes)

        obligations: dict[tuple[str, str], str] = {}
        class_obligations: dict[str, str] = {}
        class_labels: dict[str, str] = {}
        obligations_file = root / str(config.get("obligations") or "obligations.yaml")
        if obligations_file.exists():
            data = yaml.safe_load(obligations_file.read_text(encoding="utf-8")) or {}
            for class_curie, entry in (data.get("classes") or {}).items():
                class_iri = prefixes.expand(class_curie) or class_curie
                if entry.get("label"):
                    class_labels[class_iri] = entry["label"]
                if entry.get("obligation"):
                    class_obligations[class_iri] = entry["obligation"]
                for path_curie, level in (entry.get("properties") or {}).items():
                    obligations[(class_iri, prefixes.expand(path_curie) or path_curie)] = level

        subjects = dict(DEFAULT_SUBJECTS)
        subjects.update(config.get("subjects") or {})
        dsv_index: dict = {}
        if config.get("dsv_index") and (root / config["dsv_index"]).exists():
            import json

            dsv_index = json.loads((root / config["dsv_index"]).read_text(encoding="utf-8"))
        release = config.get("release") or {}
        basis = config.get("dcat_basis") or {}
        source = config.get("source") or {}
        raw_root = ""
        if str(source.get("repository", "")).startswith("https://github.com/") and source.get("commit"):
            raw_root = (str(source["repository"]).replace("https://github.com/", "https://raw.githubusercontent.com/")
                        .rstrip("/") + f"/{source['commit']}/")
        loaded_names = {Path(name).name for name in (config.get("shapes") or {}).get("constraints", [])
                        + (config.get("shapes") or {}).get("ranges", [])}
        shape_urls = [raw_root + item["path"] for item in source.get("files") or []
                      if raw_root and "!/" not in item["path"] and Path(item["path"]).name in loaded_names]
        for mirror in source.get("mirrors") or []:      # the same file, byte for byte, published as plain RDF
            repository = str(mirror.get("repository", ""))
            if repository.startswith("https://github.com/") and mirror.get("commit"):
                shape_urls.append(repository.replace("https://github.com/", "https://raw.githubusercontent.com/")
                                  .rstrip("/") + f"/{mirror['commit']}/{mirror['path']}")
        shape_archives = [raw_root + item["path"] for item in source.get("files") or []
                          if raw_root and str(item["path"]).endswith(".zip")]
        release_dir = next((str(Path(item["path"]).parent) for item in source.get("files") or []
                            if str(item["path"]).startswith("releases/")), "")
        release_url = str(config.get("homepage") or "") or (
            f"{str(source.get('repository', '')).rstrip('/')}/tree/{source.get('commit')}/{release_dir.split('!')[0]}"
            if source.get("repository") and source.get("commit") and release_dir else "")
        dcat_info = None
        if basis.get("dcat"):
            from .dcat_state import list_dcat_versions

            dcat_info = next((v for v in list_dcat_versions(data_dir or DATA_DIR) if v.id == basis["dcat"]), None)
        info = BaseProfileInfo(
            id=str(config.get("id") or base_profile_id),
            title=str(config.get("title") or base_profile_id),
            version=str(config.get("version") or ""),
            description=str(config.get("description") or ""),
            homepage=str(config.get("homepage") or ""),
            licence=str(config.get("licence") or ""),
            shape_files=[str(path.relative_to(root)) for path in shape_files],
            release_date=str(release.get("date") or ""),
            shape_urls=shape_urls,
            shape_archives=shape_archives,
            release_url=release_url,
            release_status=str(release.get("status") or ""),
            dcat=DcatBasis(
                dcat=str(basis["dcat"]),
                label=dcat_info.label if dcat_info else "",
                tr=dcat_info.tr if dcat_info else "",
                cited_as=str(basis.get("cited_as") or ""),
                cited_url=str(basis.get("cited_url") or ""),
                dcat_status_at_release=str(basis.get("dcat_status_at_release") or ""),
                unlisted_dcat_properties=basis.get("unlisted_dcat_properties") or "not_stated",
                evidence=[{key: str(value) for key, value in item.items()} for item in basis.get("evidence") or []],
                notes=[str(note) for note in basis.get("notes") or []],
            ) if basis.get("dcat") else None,
        )
        loaded = cls(
            info, index, shapes,
            obligations=obligations,
            class_obligations=class_obligations,
            class_labels=class_labels,
            subjects={word: prefixes.expand(curie) or curie for word, curie in subjects.items()},
            main_classes=[prefixes.expand(curie) or curie for curie in config.get("main_classes") or []],
            prefixes=prefixes,
        )
        loaded.dsv_index = dsv_index
        loaded.deprecated = _read_deprecations([root / name for name in (config.get("shapes") or {}).get("deprecated", [])])
        return loaded

    # (class, path) -> {"replacement": IRI or "", "message": text}: the URIs the release deprecates
    # (DCAT-AP 2.x/3.x deprecateduris.ttl: sh:message "replace dct:hasVersion with dcat:hasVersion").
    deprecated: dict[tuple[str, str], dict[str, str]] = {}

    def deprecation(self, target_class: str | None, path: str | None) -> dict[str, str] | None:
        """The base's deprecation of ``path`` on the class (or on any class when ``target_class`` is None)."""
        if not path:
            return None
        if target_class is not None and (target_class, path) in self.deprecated:
            return self.deprecated[(target_class, path)]
        return next((info for (cls, used), info in self.deprecated.items() if used == path and target_class is None), None)

    dsv_index: dict = {}

    def dsv_class_profile(self, class_iri: str) -> str | None:
        """IRI of the base's DSV class profile for ``class_iri`` (None when no DSV of the base is bundled)."""
        return (self.dsv_index.get("classes") or {}).get(class_iri)

    def dsv_property_profile(self, class_iri: str, path: str) -> str | None:
        return (self.dsv_index.get("properties") or {}).get(f"{class_iri} {path}")

    def dsv_application_profile(self) -> str | None:
        return self.dsv_index.get("application_profile")

    # -- classes ------------------------------------------------------------

    def has_class(self, iri: str | None) -> bool:
        return bool(iri) and (iri in self.index.classes or iri in self._spec_classes)

    def is_spec_only(self, target_class: str, path: str) -> bool:
        """The specification lists (class, path) with an obligation, but no official shape constrains it."""
        return (target_class, path) in self._spec_only

    def class_label(self, iri: str) -> str:
        return self._class_labels.get(iri) or self.index.classes.get(iri, None) and self.index.classes[iri].label or " ".join(
            words_of(local_name(iri))
        ).capitalize()

    def classes(self) -> list[BaseClass]:
        known = set(self.index.classes) | self._spec_classes
        ordered = [iri for iri in self.main_classes if iri in known]
        ordered += sorted(iri for iri in known if iri not in ordered)
        return [
            BaseClass(
                iri=iri,
                label=self.class_label(iri),
                definition=self.index.classes[iri].description if iri in self.index.classes else "",
                obligation=self._class_obligations.get(iri, "unknown"),  # type: ignore[arg-type]
            )
            for iri in ordered
        ]

    def class_for_subject(self, subject: str | None) -> str | None:
        """Map an atom's plain-word subject to a class of this profile (None if there is no match)."""
        if not subject:
            return None
        word = " ".join(subject.lower().split())
        candidates = [word]
        if word.endswith("s"):
            candidates.append(word[:-1])
        for candidate in candidates:
            iri = self._subjects.get(candidate)
            if iri and self.has_class(iri):
                return iri
        for iri in list(self.index.classes) + sorted(self._spec_classes):   # fall back to the class's label or local name
            names = {self.class_label(iri).lower(), " ".join(words_of(local_name(iri)))}
            if any(candidate in names for candidate in candidates):
                return iri
        return None

    # -- elements -----------------------------------------------------------

    def obligation(self, target_class: str, path: str) -> str:
        level = self._obligations.get((target_class, path))
        if level:
            return level
        facets = self.index.elements.get((target_class, path))
        if facets is not None and (facets.min_count or 0) >= 1:
            return "mandatory"
        return "unknown"

    def shape_facets(self, target_class: str, path: str) -> ShapeFacets | None:
        return self.index.elements.get((target_class, path))

    def element(self, target_class: str, path: str) -> BaseElement | None:
        facets = self.index.elements.get((target_class, path))
        if facets is None:
            if (target_class, path) not in self._spec_only:
                return None
            from ..contracts import Facets

            return BaseElement(
                target_class=target_class, path=path,
                facets=Facets(obligation=self.obligation(target_class, path)),  # type: ignore[arg-type]
                label=" ".join(words_of(local_name(path))),
                source="specification text (no official SHACL shape)",
            )
        return BaseElement(
            target_class=target_class,
            path=path,
            facets=facets.to_facets(self.obligation(target_class, path)),
            label=facets.names[0] if facets.names else " ".join(words_of(local_name(path))),
            definition=facets.descriptions[0] if facets.descriptions else "",
            severity=facets.severity,  # type: ignore[arg-type]
            source=facets.shape_ids[0] if facets.shape_ids else "",
        )

    def elements(self, target_class: str | None = None) -> list[BaseElement]:
        keys = sorted(key for key in set(self.index.elements) | self._spec_only
                      if target_class is None or key[0] == target_class)
        return [element for key in keys if (element := self.element(*key)) is not None]

    def classes_using(self, path: str) -> list[str]:
        found = list(self.index.classes_using(path))
        found += sorted(cls for cls, used in self._spec_only if used == path and cls not in found)
        return found

    def uses_term(self, iri: str) -> bool:
        return (iri in self.index.classes or iri in self._spec_classes
                or any(path == iri for (_, path) in set(self.index.elements) | self._spec_only))

    def namespaces(self) -> set[str]:
        from ..iri import namespace_of

        return ({namespace_of(iri) for iri in set(self.index.classes) | self._spec_classes}
                | {namespace_of(path) for (_, path) in set(self.index.elements) | self._spec_only})

    # -- as terms for the vocabulary index ------------------------------------

    def terms(self) -> list[Term]:
        """Every class and property the profile uses, described in the profile's own words.

        These top up the vocabulary index, so a term the base uses is always
        retrievable even when its vocabulary file is not vendored.
        """
        terms: dict[str, Term] = {}
        for iri, info in self.index.classes.items():
            terms[iri] = Term(
                iri=iri, kind="class", label=self.class_label(iri), definition=info.description,
                vocabulary=self.prefixes.prefix_of(iri) or "", source=f"base profile {self.info.id}",
            )
        for iri in self._spec_classes:
            terms.setdefault(iri, Term(
                iri=iri, kind="class", label=self.class_label(iri), vocabulary=self.prefixes.prefix_of(iri) or "",
                source=f"base profile {self.info.id} (specification text)",
            ))
        for _, path in sorted(self._spec_only):
            terms.setdefault(path, Term(
                iri=path, kind="property", label=" ".join(words_of(local_name(path))),
                vocabulary=self.prefixes.prefix_of(path) or "", source=f"base profile {self.info.id} (specification text)",
            ))
        for (target_class, path), facets in self.index.elements.items():
            term = terms.get(path)
            if term is None:
                term = terms[path] = Term(
                    iri=path, kind="property",
                    label=facets.names[0] if facets.names else " ".join(words_of(local_name(path))),
                    definition=facets.descriptions[0] if facets.descriptions else "",
                    vocabulary=self.prefixes.prefix_of(path) or "", source=f"base profile {self.info.id}",
                    property_type="datatype" if facets.datatypes or facets.node_kind == "Literal" else
                    ("object" if facets.classes else "unknown"),
                )
            for value in sorted(facets.classes | facets.datatypes):
                if value not in term.range:
                    term.range.append(value)
        return list(terms.values())

    # -- shapes for validation ----------------------------------------------

    def shapes_graph(self) -> Graph:
        """The official constraint shapes (a copy is NOT made: do not mutate)."""
        return self._shapes


def _read_deprecations(files: list[Path]) -> dict[tuple[str, str], dict[str, str]]:
    import re

    from rdflib.namespace import SH

    graph = load_graph([path for path in files if path.exists()]) if files else Graph()
    found: dict[tuple[str, str], dict[str, str]] = {}
    for shape, target in graph.subject_objects(SH.targetClass):
        for prop in graph.objects(shape, SH.property):
            path = graph.value(prop, SH.path)
            message = str(graph.value(prop, SH.message) or "")
            if not isinstance(path, URIRef):
                continue
            match = re.search(r"replace (?:property )?(\S+) with (\S+)", message)
            replacement = ""
            if match:
                curie = match.group(2).strip(".")
                prefix, _, local = curie.partition(":")
                namespaces = {str(p): str(n) for p, n in graph.namespaces()}
                replacement = f"{namespaces[prefix]}{local}" if prefix in namespaces and local else ""
            if not match and "inverse property" not in message:
                continue
            found[(str(target), str(path))] = {"replacement": replacement, "message": message,
                                               "kind": "inverse" if not match else "deprecated"}
    return found


def _release_key(info: BaseProfileInfo) -> tuple:
    version = tuple(int(part) if part.isdigit() else 0 for part in info.version.split("."))
    return (info.release_date or "", version)


def list_base_profiles(data_dir: Path | None = None) -> list[BaseProfileInfo]:
    """Every vendored base profile, oldest release first; the newest one is marked ``is_latest``."""
    root = (data_dir or DATA_DIR) / "base-profiles"
    if not root.exists():
        return []
    infos = [load_base_profile(path.parent.name, data_dir).info.model_copy() for path in root.glob("*/profile.yaml")]
    infos.sort(key=_release_key)
    if infos:
        latest = infos[-1].id
        infos = [info.model_copy(update={"is_latest": info.id == latest}) for info in infos]
    return infos


def latest_base_profile_id(data_dir: Path | None = None) -> str:
    """The default base of a new extension: the newest DCAT-AP release (which builds on the newest DCAT)."""
    infos = list_base_profiles(data_dir)
    if not infos:
        raise KeyError("no base profiles are vendored")
    return infos[-1].id


@lru_cache(maxsize=64)
def _load_cached(base_profile_id: str, data_dir: str) -> BaseProfile:
    return BaseProfile.load(base_profile_id, Path(data_dir) if data_dir else None)


def load_base_profile(base_profile_id: str, data_dir: Path | None = None) -> BaseProfile:
    """Load (and cache) a base profile. The result is shared: treat it as read-only."""
    return _load_cached(base_profile_id, str(data_dir or ""))
