#!/usr/bin/env python3
"""Vendor every W3C DCAT version the tool knows, pinned to official sources, and derive
the DCAT class/property model of each version from its specification text.

For each DCAT version this writes ``backend/profile_extensioner/data/dcat/<id>/``:

  dcat.ttl     the namespace document of that version, UNMODIFIED (from w3c/dxwg)
  spec.html    the specification text of that version, UNMODIFIED
  model.json   generated: the classes of the specification, and for every class the
               properties the specification lists for it (RDF property, definition,
               range, domain, usage note). This is "what DCAT says applies to a class",
               including the terms DCAT reuses from DCTERMS, PROV, ODRL, FOAF, ...

and ``data/dcat/versions.yaml`` (identity, W3C status history, sources, SHA-256) plus
``data/dcat/history.json`` (per term: the versions that define it, deprecations).

Usage:
  python scripts/build_dcat_versions.py --dxwg /path/to/w3c/dxwg --dx-dcat /path/to/w3c/dx-dcat

Both checkouts must contain the commits named in VERSIONS (blob-less clones are fine).
Nothing is downloaded.
"""
from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "profile_extensioner" / "data" / "dcat"
DCAT = "http://www.w3.org/ns/dcat#"

# Every fact below is taken from the named file at the named commit (see "evidence").
VERSIONS = [
    {
        "id": "dcat-2014",
        "title": "Data Catalog Vocabulary (DCAT)",
        "label": "DCAT 2014",
        "tr": "https://www.w3.org/TR/2014/REC-vocab-dcat-20140116/",
        "status_history": [
            {"status": "W3C Recommendation", "date": "2014-01-16", "tr": "https://www.w3.org/TR/2014/REC-vocab-dcat-20140116/"},
        ],
        "rdf": {"repo": "w3c/dxwg", "repo_url": "https://github.com/w3c/dxwg", "commit": "ce5176c",
                "path": "dcat/rdf/dcat2014.ttl",
                "note": "The 2014 namespace document as W3C publishes it at https://www.w3.org/ns/dcat2014 "
                        "(dxwg commit ece469f 'align dcat2014.ttl with the version currently published'; ce5176c only "
                        "trims trailing spaces). It also carries terms of the 2013 drafts, marked owl:deprecated."},
        "spec": {"repo": "w3c/dx-dcat", "repo_url": "https://github.com/w3c/dx-dcat", "commit": "0171455",
                 "path": "TR/dcat_10.html", "status_line": "W3C Recommendation 16 January 2014"},
    },
    {
        "id": "dcat-2",
        "title": "Data Catalog Vocabulary (DCAT) - Version 2",
        "label": "DCAT 2",
        "tr": "https://www.w3.org/TR/2020/REC-vocab-dcat-2-20200204/",
        "status_history": [
            {"status": "W3C Candidate Recommendation", "date": "2019-10-03", "tr": "https://www.w3.org/TR/2019/CR-vocab-dcat-2-20191003/"},
            {"status": "W3C Recommendation", "date": "2020-02-04", "tr": "https://www.w3.org/TR/2020/REC-vocab-dcat-2-20200204/"},
        ],
        "rdf": {"repo": "w3c/dxwg", "repo_url": "https://github.com/w3c/dxwg", "commit": "e3ce507",
                "path": "dcat/rdf/dcat2.ttl",
                "note": "Last change 2021-10-13 (spelling; 2021-09-14 removed axioms that are not in the REC text). "
                        "The DCAT term set and every domain/range equal those of dcat/rdf/dcat.ttl at d45e1eb "
                        "(2019-10-17, the Candidate Recommendation period); verified with scripts/build_dcat_versions.py --compare."},
        "spec": {"repo": "w3c/dxwg", "repo_url": "https://github.com/w3c/dxwg", "commit": "7b7f10f",
                 "path": "dcat/index.html",
                 "status_line": "ReSpec source of 2020-02-03 ('Upstreaming tweaks applied to the REC'); verify against the REC text"},
    },
    {
        "id": "dcat-3",
        "title": "Data Catalog Vocabulary (DCAT) - Version 3",
        "label": "DCAT 3",
        "tr": "https://www.w3.org/TR/2024/REC-vocab-dcat-3-20240822/",
        "status_history": [
            {"status": "W3C Candidate Recommendation Snapshot", "date": "2024-01-18", "snapshot": "dcat/publication-snapshots/CR/Overview.html"},
            {"status": "W3C Proposed Recommendation", "date": "2024-06-13", "snapshot": "dcat/publication-snapshots/PR/Overview.html"},
            {"status": "W3C Recommendation", "date": "2024-08-22", "snapshot": "dcat/publication-snapshots/REC/Overview.html"},
        ],
        "rdf": {"repo": "w3c/dxwg", "repo_url": "https://github.com/w3c/dxwg", "commit": "ce5176c",
                "path": "dcat/rdf/dcat3.ttl",
                "note": "Content unchanged from f03a6dc (2023-02-02) to ce5176c (2024-10-16, trailing spaces), so it is the "
                        "RDF of the CR, PR and REC periods. Later edits (2026-06, issues 1626/1627) fix labels only and "
                        "are not used."},
        "spec": {"repo": "w3c/dxwg", "repo_url": "https://github.com/w3c/dxwg", "commit": "2bc58b9",
                 "path": "dcat/publication-snapshots/REC/Overview.html", "status_line": "W3C Recommendation 22 August 2024"},
        "extra_specs": [
            {"id": "pr", "repo": "w3c/dxwg", "commit": "2bc58b9", "path": "dcat/publication-snapshots/PR/Overview.html",
             "status_line": "W3C Proposed Recommendation 13 June 2024"},
        ],
    },
]

PREFIXES = {
    "dcat": DCAT, "dct": "http://purl.org/dc/terms/", "dcterms": "http://purl.org/dc/terms/",
    "dctype": "http://purl.org/dc/dcmitype/", "foaf": "http://xmlns.com/foaf/0.1/",
    "prov": "http://www.w3.org/ns/prov#", "odrl": "http://www.w3.org/ns/odrl/2/",
    "skos": "http://www.w3.org/2004/02/skos/core#", "vcard": "http://www.w3.org/2006/vcard/ns#",
    "locn": "http://www.w3.org/ns/locn#", "spdx": "http://spdx.org/rdf/terms#", "adms": "http://www.w3.org/ns/adms#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#", "owl": "http://www.w3.org/2002/07/owl#",
    "time": "http://www.w3.org/2006/time#", "sdo": "https://schema.org/", "schema": "http://schema.org/",
    "dqv": "http://www.w3.org/ns/dqv#", "geosparql": "http://www.opengis.net/ont/geosparql#",
    "gsp": "http://www.opengis.net/ont/geosparql#", "dcatap": "http://data.europa.eu/r5r/",
}
CURIE = re.compile(r"^([A-Za-z][\w-]*):([A-Za-z_][\w.-]*)$")


def git_show(repo: Path, commit: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True, check=True).stdout


def full_commit(repo: Path, commit: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", commit], capture_output=True, text=True, check=True).stdout.strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_of(fragment: str) -> str:
    fragment = re.sub(r"<!--.*?-->", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def expand(token: str) -> str | None:
    token = token.strip().strip(",;.")
    match = CURIE.match(token)
    if match and match.group(1) in PREFIXES:
        return PREFIXES[match.group(1)] + match.group(2)
    if token.startswith(("http://", "https://")) and not token.startswith(("https://www.w3.org/TR/", "http://www.w3.org/TR/")):
        return token
    return None


def iris_in(cell: str) -> list[str]:
    """IRIs named in a table cell: the CURIEs shown in <code>/<a> text, else namespace-looking hrefs."""
    found: list[str] = []
    for text in re.findall(r"<(?:code|a)\b[^>]*>(.*?)</(?:code|a)>", cell, flags=re.S):
        iri = expand(text_of(text))
        if iri and iri not in found:
            found.append(iri)
    if not found:
        for href in re.findall(r'href="([^"]+)"', cell):
            iri = expand(href)
            if iri and iri not in found:
                found.append(iri)
    return found


TABLE = re.compile(r"<table\b[^>]*>(.*?)</table>", re.S)
ROW = re.compile(r"<tr\b[^>]*>\s*<t[hd]\b[^>]*>(.*?)</t[hd]>\s*<t[hd]\b[^>]*>(.*?)</t[hd]>\s*</tr>", re.S)
HEADING = re.compile(r"<h[2-6]\b[^>]*>(.*?)</h[2-6]>", re.S)


RDFS_LITERAL = PREFIXES["rdfs"] + "Literal"


def extract_model(spec_html: str) -> dict:
    """Walk the specification in document order. A table whose first row is 'RDF Class:' opens a class;
    a table whose first row is 'RDF Property:' adds a property to the class that is open.

    A label may repeat inside one table (DCAT 3, Class: Data Service has two "Sub-class of" rows,
    dcat:Resource and dctype:Service, and two "Usage note" rows): every row is kept."""
    classes: dict[str, dict] = {}
    current: list[str] = []
    last_heading = ""
    events = sorted(
        [(m.start(), "h", m) for m in HEADING.finditer(spec_html)] + [(m.start(), "t", m) for m in TABLE.finditer(spec_html)],
        key=lambda item: item[0],
    )
    shared: list[tuple[str, dict]] = []          # (other domain class, property entry) for "Domain: A or B" rows
    for _, kind, match in events:
        if kind == "h":
            last_heading = text_of(match.group(1))
            if re.search(r"\bClass:", last_heading) is None and re.search(r"\bProperty:", last_heading) is None \
                    and re.match(r"^[\d.]+\s+[A-Z]", last_heading) and re.match(r"^\d+\.\s", last_heading):
                current = []          # a new top-level chapter closes the open class
            continue
        rows = [(text_of(label).rstrip(":").strip().lower(), value) for label, value in ROW.findall(match.group(1))]
        if not rows:
            continue
        head, head_value = rows[0]
        fields: dict[str, list[str]] = {}
        for label, value in rows[1:]:
            fields.setdefault(label, []).append(value)

        def first(key: str) -> str:
            return text_of((fields.get(key) or [""])[0])

        def joined(key: str) -> str:
            return " ".join(text_of(cell) for cell in fields.get(key) or [])

        def all_iris(*keys: str) -> list[str]:
            found: list[str] = []
            for key in keys:
                for cell in fields.get(key) or []:
                    found += [iri for iri in iris_in(cell) if iri not in found]
            return found

        if head == "rdf class":
            current = iris_in(head_value)
            for iri in current:
                entry = classes.setdefault(iri, {"label": re.sub(r"^[\d.]+\s*", "", last_heading).replace("Class:", "").strip(),
                                                 "definition": "", "subclass_of": [], "properties": []})
                entry["definition"] = entry["definition"] or first("definition")
                for sup in all_iris("sub class of", "subclass of", "sub-class of"):
                    if sup not in entry["subclass_of"]:
                        entry["subclass_of"].append(sup)
                entry["usage_note"] = entry.get("usage_note") or joined("usage note")
        elif head == "rdf property" and current:
            paths = iris_in(head_value)
            if not paths:
                continue
            label = re.sub(r"^[\d.]+\s*", "", last_heading).replace("Property:", "").strip()
            range_text = joined("range")
            ranges = all_iris("range")
            # "rdfs:Literal typed as xsd:X": the values are xsd:X literals (DCAT 3 dcat:byteSize, ...).
            if re.match(r"^rdfs:Literal\s+(typically\s+)?typed as\b", range_text) and len(ranges) > 1:
                ranges = [iri for iri in ranges if iri != RDFS_LITERAL]
            domain = all_iris("domain")
            for class_iri in current:
                for path in paths:
                    entry = classes[class_iri]
                    if any(existing["path"] == path for existing in entry["properties"]):
                        continue
                    record = {
                        "path": path, "label": label, "definition": first("definition"),
                        "range": ranges, "range_text": range_text, "domain": domain, "usage_note": joined("usage note"),
                    }
                    entry["properties"].append(record)
                    # "Domain: prov:Attribution or dcat:Relationship": the property applies to the other class too.
                    if class_iri in domain:
                        shared += [(other, record) for other in domain if other != class_iri]
    for other, record in shared:
        entry = classes.setdefault(other, {"label": other.rsplit("#", 1)[-1].rsplit("/", 1)[-1], "definition": "",
                                           "subclass_of": [], "properties": [], "from_domain": True})
        if not any(existing["path"] == record["path"] for existing in entry["properties"]):
            entry["properties"].append({**record, "from_domain": True})
    return {"classes": classes, "inverse_properties": extract_inverses(spec_html)}


def extract_inverses(spec_html: str) -> list[list[str]]:
    """The table of section "Use of inverse properties" (DCAT 3, section 7): [canonical, inverse] pairs."""
    start = spec_html.find('id="inverse-properties"')
    if start < 0:
        return []
    end = spec_html.find("</section>", start)
    pairs = []
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", spec_html[start:end], flags=re.S):
        cells = [iris_in(cell) for cell in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row, flags=re.S)]
        if len(cells) == 2 and len(cells[0]) == 1 and len(cells[1]) == 1:
            pairs.append([cells[0][0], cells[1][0]])
    return pairs


def rdf_terms(turtle: bytes) -> dict[str, dict]:
    from rdflib import Graph, URIRef
    from rdflib.namespace import OWL, RDF, RDFS

    graph = Graph()
    graph.parse(data=turtle, format="turtle")
    terms: dict[str, dict] = {}
    for subject in set(graph.subjects(RDF.type, None)) | set(graph.subjects(OWL.inverseOf, None)):
        if not isinstance(subject, URIRef) or not str(subject).startswith(DCAT) or str(subject) == DCAT:
            continue
        types = {str(o) for o in graph.objects(subject, RDF.type)}
        kind = "class" if types & {str(RDFS.Class), str(OWL.Class)} else "property"   # untyped inverses are properties
        terms[str(subject)] = {
            "kind": kind,
            "deprecated": any(str(value).lower() == "true" for value in graph.objects(subject, OWL.deprecated)),
            "inverse_of": sorted(str(o) for o in graph.objects(subject, OWL.inverseOf) if isinstance(o, URIRef)),
        }
    return terms


def build(dxwg: Path, dx_dcat: Path) -> None:
    repos = {"w3c/dxwg": dxwg, "w3c/dx-dcat": dx_dcat}
    manifest = {"note": "Generated by scripts/build_dcat_versions.py. Every DCAT version is kept: the files are the official "
                        "ones, unmodified. Do not edit by hand.", "namespace": DCAT, "versions": []}
    history: dict[str, dict] = {}
    for version in VERSIONS:
        target = OUT / version["id"]
        target.mkdir(parents=True, exist_ok=True)
        rdf = git_show(repos[version["rdf"]["repo"]], version["rdf"]["commit"], version["rdf"]["path"])
        spec = git_show(repos[version["spec"]["repo"]], version["spec"]["commit"], version["spec"]["path"])
        (target / "dcat.ttl").write_bytes(rdf)
        (target / "spec.html").write_bytes(spec)
        model = extract_model(spec.decode("utf-8"))
        extra = []
        for other in version.get("extra_specs", []):
            data = git_show(repos[other["repo"]], other["commit"], other["path"])
            name = f"spec-{other['id']}.html"
            (target / name).write_bytes(data)
            other_model = extract_model(data.decode("utf-8"))
            same = json.dumps(other_model, sort_keys=True) == json.dumps(model, sort_keys=True)
            extra.append({**{k: v for k, v in other.items() if k != "repo"}, "repo": other["repo"],
                          "commit": full_commit(repos[other["repo"]], other["commit"]), "file": name,
                          "sha256": sha256(data), "model_equals_main_spec": same})
            print(f"{version['id']}: {name} model {'equals' if same else 'DIFFERS FROM'} the main specification's model")
        terms = rdf_terms(rdf)
        model.update({"version": version["id"], "generated_from": "spec.html"})
        (target / "model.json").write_text(json.dumps(model, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        entry = {key: version[key] for key in ("id", "title", "label", "tr", "status_history")}
        entry["rdf"] = {**version["rdf"], "commit": full_commit(repos[version["rdf"]["repo"]], version["rdf"]["commit"]),
                        "file": f"{version['id']}/dcat.ttl", "sha256": sha256(rdf)}
        entry["spec"] = {**version["spec"], "commit": full_commit(repos[version["spec"]["repo"]], version["spec"]["commit"]),
                         "file": f"{version['id']}/spec.html", "sha256": sha256(spec)}
        if extra:
            entry["extra_specs"] = extra
        entry["model"] = {"file": f"{version['id']}/model.json",
                          "classes": len(model["classes"]),
                          "class_property_pairs": sum(len(c["properties"]) for c in model["classes"].values())}
        entry["dcat_terms"] = {"classes": sum(1 for t in terms.values() if t["kind"] == "class"),
                               "properties": sum(1 for t in terms.values() if t["kind"] == "property"),
                               "deprecated": sum(1 for t in terms.values() if t["deprecated"])}
        manifest["versions"].append(entry)
        for iri, info in terms.items():
            record = history.setdefault(iri, {"kind": info["kind"], "defined_in": [], "deprecated_in": [], "inverse_of": {}})
            record["defined_in"].append(version["id"])
            if info["deprecated"]:
                record["deprecated_in"].append(version["id"])
            if info["inverse_of"]:
                record["inverse_of"][version["id"]] = info["inverse_of"]
        print(f"{version['id']}: {entry['dcat_terms']} DCAT terms; model {entry['model']}")
    order = [version["id"] for version in VERSIONS]
    for record in history.values():
        current = [v for v in record["defined_in"] if v not in record["deprecated_in"]]
        record["introduced_in"] = current[0] if current else record["defined_in"][0]
        record["removed_after"] = record["defined_in"][-1] if record["defined_in"][-1] != order[-1] else None
        if not record["inverse_of"]:
            del record["inverse_of"]
    (OUT / "versions.yaml").write_text("# " + manifest.pop("note") + "\n" + yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
                                       encoding="utf-8")
    (OUT / "history.json").write_text(json.dumps({"order": order, "terms": dict(sorted(history.items()))}, indent=1) + "\n",
                                      encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dxwg", required=True, type=Path)
    parser.add_argument("--dx-dcat", required=True, type=Path)
    args = parser.parse_args(argv)
    build(args.dxwg, args.dx_dcat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
