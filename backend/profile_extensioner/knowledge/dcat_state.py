"""The W3C DCAT state a base profile builds on.

Every DCAT version is vendored under ``data/dcat/<id>/`` (scripts/build_dcat_versions.py):

    dcat.ttl     the namespace document of that version, unmodified
    spec.html    the specification text of that version, unmodified
    model.json   the classes of the specification and, per class, the properties the
                 specification lists for it (DCAT's own terms and the DCTERMS, PROV, ODRL,
                 FOAF ... terms DCAT reuses)

plus ``versions.yaml`` (W3C status history, sources, hashes) and ``history.json`` (per
DCAT term: the versions that define it and the ones that deprecate it).

A base profile names the version it builds on in ``profile.yaml`` (``dcat_basis``); the
DCAT-AP releases state it themselves (DCAT-AP 1.1: the DCAT Recommendation of 2014;
DCAT-AP 3.x: DCAT 3). ``DcatState`` answers, for that pinned version:

* does a DCAT term exist in it, or only in a later version, or is it deprecated there;
* which properties DCAT lists for a class (inherited along DCAT's own class hierarchy:
  in DCAT 2 and 3 a Dataset is a Cataloged Resource, a Catalog is a Dataset);
* which properties are DCAT's inverse properties (DCAT 3, section 7: "MAY be used only
  in addition to ..., MUST NOT be used to replace them").
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..contracts import DcatBasis, DcatVersionInfo

DCAT_NS = "http://www.w3.org/ns/dcat#"
DCAT_DIR_NAME = "dcat"

# Replacements the DCAT texts name for terms of the 2013/2014 drafts that are deprecated in the
# 2014 namespace document (data/dcat/dcat-2014/dcat.ttl, rdfs:comment "This term has been deprecated").
DEPRECATED_REPLACEMENTS = {
    DCAT_NS + "size": DCAT_NS + "byteSize",
    DCAT_NS + "bytes": DCAT_NS + "byteSize",
}


@dataclass
class DcatProperty:
    """A property the DCAT specification lists for a class."""

    path: str
    label: str = ""
    definition: str = ""
    range: list[str] = field(default_factory=list)
    range_text: str = ""
    domain: list[str] = field(default_factory=list)
    usage_note: str = ""
    listed_on: str = ""          # the class whose section lists it (may be a superclass of the asked class)


class DcatState:
    """The DCAT version a base builds on, with the history of every DCAT term across versions."""

    def __init__(
        self,
        versions: list[DcatVersionInfo],
        history: dict[str, dict[str, Any]],
        models: dict[str, dict[str, Any]],
        basis: DcatBasis,
    ) -> None:
        self.versions = versions
        self.order = [version.id for version in versions]
        if basis.dcat not in self.order:
            raise KeyError(f"unknown DCAT version {basis.dcat!r}; known: {', '.join(self.order)}")
        self.basis = basis
        self.version = next(version for version in versions if version.id == basis.dcat)
        self._history = history
        self._models = models
        model = models.get(basis.dcat) or {}
        self._classes: dict[str, dict[str, Any]] = model.get("classes") or {}
        self._inverses = {inverse: canonical for canonical, inverse in model.get("inverse_properties") or []}

    # -- versions ------------------------------------------------------------

    @property
    def id(self) -> str:
        return self.version.id

    @property
    def label(self) -> str:
        return self.version.label

    def version_info(self, version_id: str) -> DcatVersionInfo | None:
        return next((version for version in self.versions if version.id == version_id), None)

    def describe_version(self, version_id: str | None = None) -> str:
        """'DCAT 2 (W3C Recommendation 2020-02-04)'."""
        info = self.version_info(version_id or self.id)
        if info is None:
            return version_id or ""
        final = next((s for s in reversed(info.status_history) if s.get("status") == "W3C Recommendation"),
                     info.status_history[-1] if info.status_history else {})
        return f"{info.label} ({final.get('status', '')} {final.get('date', '')})".replace(" ()", "").strip()

    def is_later(self, version_id: str) -> bool:
        return version_id in self.order and self.order.index(version_id) > self.order.index(self.id)

    def summary(self, base_title: str = "") -> str:
        """One sentence for prompts, documentation and the workbench."""
        subject = base_title or "The base profile"
        status = f"; DCAT's status then: {self.basis.dcat_status_at_release}" if self.basis.dcat_status_at_release else ""
        return f"{subject} builds on W3C {self.describe_version()}{status}."

    # -- terms ---------------------------------------------------------------

    @staticmethod
    def is_dcat(iri: str | None) -> bool:
        return bool(iri) and iri.startswith(DCAT_NS) and len(iri) > len(DCAT_NS)

    def defined_in(self, iri: str) -> list[str]:
        return list((self._history.get(iri) or {}).get("defined_in") or [])

    def introduced_in(self, iri: str) -> str | None:
        record = self._history.get(iri)
        return record.get("introduced_in") if record else None

    def status(self, iri: str | None) -> str:
        """For a DCAT term, relative to the pinned version:

        ``current``     defined in the pinned version
        ``deprecated``  defined in the pinned version and deprecated there
        ``later``       not in the pinned version; a later version defines it
        ``removed``     only earlier versions define it
        ``unknown``     in the DCAT namespace, but no version defines it
        ``""``          not a DCAT term
        """
        if not self.is_dcat(iri):
            return ""
        record = self._history.get(iri or "")
        if not record:
            return "unknown"
        if self.id in record.get("defined_in", []):
            return "deprecated" if self.id in record.get("deprecated_in", []) else "current"
        if any(self.is_later(version) for version in record.get("defined_in", [])):
            return "later"
        return "removed"

    def replacement_for(self, iri: str) -> str | None:
        return DEPRECATED_REPLACEMENTS.get(iri)

    # -- the class / property model of the pinned version ----------------------

    def classes(self) -> list[str]:
        return list(self._classes)

    def has_class(self, iri: str | None) -> bool:
        return bool(iri) and iri in self._classes

    def class_label(self, iri: str) -> str:
        return str((self._classes.get(iri) or {}).get("label") or "")

    def _model_classes(self, version: str | None) -> dict[str, dict[str, Any]]:
        if version is None or version == self.id:
            return self._classes
        return (self._models.get(version) or {}).get("classes") or {}

    def superclasses(self, class_iri: str, version: str | None = None) -> list[str]:
        """DCAT's own class hierarchy (from the specification's 'Sub class of' rows), nearest first;
        of the pinned version unless ``version`` names another one."""
        classes = self._model_classes(version)
        seen: list[str] = []
        frontier = [class_iri]
        while frontier:
            current = frontier.pop(0)
            for parent in (classes.get(current) or {}).get("subclass_of") or []:
                if parent not in seen and parent != class_iri:
                    seen.append(parent)
                    frontier.append(parent)
        return seen

    def properties_for(self, class_iri: str | None, version: str | None = None) -> list[DcatProperty]:
        """Every property the specification lists for the class or for one of its DCAT superclasses
        (pinned version, or ``version``)."""
        if not class_iri:
            return []
        classes = self._model_classes(version)
        result: dict[str, DcatProperty] = {}
        for owner in [class_iri] + self.superclasses(class_iri, version):
            for entry in (classes.get(owner) or {}).get("properties") or []:
                if entry["path"] in result:
                    continue
                result[entry["path"]] = DcatProperty(
                    path=entry["path"], label=entry.get("label", ""), definition=entry.get("definition", ""),
                    range=list(entry.get("range") or []), range_text=entry.get("range_text", ""),
                    domain=list(entry.get("domain") or []), usage_note=entry.get("usage_note", ""), listed_on=owner,
                )
        return list(result.values())

    def listed_for(self, class_iri: str | None, path: str, version: str | None = None) -> DcatProperty | None:
        return next((prop for prop in self.properties_for(class_iri, version) if prop.path == path), None)

    def classes_listing(self, path: str, version: str | None = None) -> list[str]:
        """The classes whose section lists ``path`` directly (pinned version, or ``version``)."""
        return [iri for iri, entry in self._model_classes(version).items()
                if any(prop["path"] == path for prop in entry.get("properties") or [])]

    def inverse_canonical(self, path: str) -> str | None:
        """For an inverse property of the pinned DCAT (DCAT 3 section 7), the property it inverts."""
        return self._inverses.get(path)

    def inverse_pairs(self) -> list[tuple[str, str]]:
        return [(canonical, inverse) for inverse, canonical in self._inverses.items()]

    def terms_in(self, version_id: str) -> list[str]:
        return [iri for iri, record in self._history.items() if version_id in record.get("defined_in", [])]


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------


def dcat_dir(data_dir: Path) -> Path:
    return data_dir / DCAT_DIR_NAME


@lru_cache(maxsize=4)
def _load_catalogue(root: str) -> tuple[tuple[DcatVersionInfo, ...], dict, dict]:
    base = Path(root)
    manifest = yaml.safe_load((base / "versions.yaml").read_text(encoding="utf-8")) or {}
    raw_versions = manifest.get("versions") or []
    versions = []
    for index, entry in enumerate(raw_versions):
        versions.append(DcatVersionInfo(
            id=entry["id"], label=entry.get("label") or entry["id"], title=entry.get("title", ""), tr=entry.get("tr", ""),
            status_history=[{key: str(value) for key, value in status.items()} for status in entry.get("status_history") or []],
            is_latest=index == len(raw_versions) - 1,
        ))
    history = json.loads((base / "history.json").read_text(encoding="utf-8")).get("terms") or {}
    models = {}
    for version in versions:
        path = base / version.id / "model.json"
        models[version.id] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return tuple(versions), history, models


def list_dcat_versions(data_dir: Path) -> list[DcatVersionInfo]:
    versions, _, _ = _load_catalogue(str(dcat_dir(data_dir)))
    return list(versions)


def latest_dcat_version(data_dir: Path) -> DcatVersionInfo:
    return list_dcat_versions(data_dir)[-1]


def load_dcat_state(basis: DcatBasis, data_dir: Path) -> DcatState:
    versions, history, models = _load_catalogue(str(dcat_dir(data_dir)))
    info = next((version for version in versions if version.id == basis.dcat), None)
    if info is not None:
        basis = basis.model_copy(update={"label": basis.label or info.label, "tr": basis.tr or info.tr})
    return DcatState(list(versions), history, models, basis)


def dcat_rdf_path(data_dir: Path, version_id: str) -> Path:
    return dcat_dir(data_dir) / version_id / "dcat.ttl"
