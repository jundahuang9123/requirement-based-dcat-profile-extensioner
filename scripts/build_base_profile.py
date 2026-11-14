#!/usr/bin/env python3
"""Build a base-profile directory from a checkout of the official SEMICeu/DCAT-AP repository.

For one release it
  * copies the official SHACL files UNMODIFIED (and records their SHA-256),
  * reads the obligation level (mandatory / recommended / optional) of every
    property from the "quick reference" table of the release's specification
    HTML, because the SHACL files only carry the mandatory ones (sh:minCount),
  * writes profile.yaml (identity, source commit, licence, shape files).

Usage:
  python scripts/build_base_profile.py --semic-repo /path/to/DCAT-AP --release 3.0.1

The output goes to backend/profile_extensioner/data/base-profiles/dcat-ap-<release>/.
Nothing is downloaded: the repository checkout is the only input.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from profile_extensioner.iri import Prefixes  # noqa: E402

# Which files of a release hold the constraint shapes, and which hold range-only shapes; where the
# obligation levels are stated ("rdf": the vann:usageNote of every property in the release RDF;
# "html": the quick-reference table of the HTML specification); whether the shapes use implicit
# class targets (shape IRI = class IRI). Every SEMIC release that ships SHACL is listed.
RELEASE_FILES = {
    "1.1": {"zip": "shacl-201706.zip", "constraints": ["shacl-201706/dcat-ap.shapes.ttl"], "ranges": [],
            "obligations": "rdf", "implicit": True,
            # the same file, byte for byte, as resolvable RDF (SEMIC's own SHACL repository; sha256 checked)
            "mirrors": [{"repository": "https://github.com/SEMICeu/dcat-ap_shacl",
                         "commit": "c9683b174edab5933bf8f9ef48bde2c4c29b8fbc", "path": "shacl/dcat-ap.shapes.ttl",
                         "same_as": "shacl-201706/dcat-ap.shapes.ttl"}]},
    "1.2": {"zip": "dcat-ap_1.2_shacl.zip", "constraints": ["dcat-ap_1.2_shacl/dcat-ap.shapes.ttl"], "ranges": [],
            "obligations": "rdf", "implicit": True},
    "1.2.1": {"constraints": ["dcat-ap_1.2.1_shacl_shapes.ttl"], "ranges": [], "obligations": "rdf"},
    "2.0.0": {"constraints": ["dcat-ap_2.0.0_shacl_shapes.ttl"], "ranges": [], "obligations": "rdf",
              "deprecated": ["dcat-ap_2.0.0_shacl_deprecateduris.ttl"]},
    "2.0.1": {"constraints": ["dcat-ap_2.0.1_shacl_shapes.ttl"], "ranges": [], "obligations": "rdf",
              "deprecated": ["dcat-ap_2.0.1_shacl_deprecateduris.ttl"]},
    "2.1.0": {"constraints": ["dcat-ap_2.1.0_shacl_shapes.ttl"], "ranges": ["dcat-ap_2.1.0_shacl_range.ttl"],
              "obligations": "rdf", "deprecated": ["dcat-ap_2.1.0_shacl_deprecateduris.ttl"]},
    "2.1.1": {"constraints": ["dcat-ap_2.1.1_shacl_shapes.ttl"], "ranges": ["dcat-ap_2.1.1_shacl_range.ttl"],
              "obligations": "rdf", "deprecated": ["dcat-ap_2.1.1_shacl_deprecateduris.ttl"]},
    "3.0.0": {"constraints": ["shacl/dcat-ap-SHACL.ttl"], "ranges": [], "obligations": "html",
              "deprecated": ["html/shacl/deprecateduris.ttl"]},
    # shacl/ranges.ttl of 3.0.1 is vendored but NOT loaded: 206 sh:property nodes without sh:path, so a SHACL
    # engine rejects it (pySHACL: "not a well-formed SHACL PropertyShape"); dcat-ap-SHACL.ttl has the ranges.
    "3.0.1": {"constraints": ["shacl/dcat-ap-SHACL.ttl"], "ranges": [], "not_loaded": ["shacl/ranges.ttl"],
              "obligations": "html", "deprecated": ["html/shacl/deprecateduris.ttl"]},
}
MAIN_CLASSES = ["dcat:Catalog", "dcat:Dataset", "dcat:Distribution", "dcat:DataService",
                "dcat:DatasetSeries", "dcat:CatalogRecord"]

# The W3C DCAT state each DCAT-AP release builds on, as the release itself states it. "dcat" names a
# directory of data/dcat/ (every DCAT version is vendored there). "dcat_status_at_release" is the
# W3C status DCAT had on the release date (from data/dcat/versions.yaml status_history).
# "unlisted_dcat_properties": what the release says about DCAT properties it does not list for a class.
DCAT_BASIS = {
    "1.1": {
        "release": {"date": "2015-10-23", "status": "Final",
                    "evidence": "releases/1.1/dcat-ap_1.1.pdf, cover ('Date: 2015-10-23') and document metadata ('Status Final')"},
        "dcat_basis": {
            "dcat": "dcat-2014",
            "cited_as": "W3C. Data Catalog Vocabulary (DCAT). W3C Recommendation 16 January 2014. "
                        "http://www.w3.org/TR/2014/REC-vocab-dcat-20140116/",
            "dcat_status_at_release": "W3C Recommendation (2014-01-16)",
            "evidence": [
                {"file": "releases/1.1/dcat-ap_1.1.pdf", "section": "1.4 The DCAT specification",
                 "quote": "The specification of the Data Catalog Vocabulary (DCAT) was published by W3C as a W3C "
                          "Recommendation on 16 January 2014. The DCAT Application Profile defined in this document is "
                          "based on this officially published version."},
            ],
            "notes": ["The class table of section 4 links the DCAT classes to the Working Draft of 12 March 2013 "
                      "(http://www.w3.org/TR/2013/WD-vocab-dcat-20130312/), not to the Recommendation."],
            "unlisted_dcat_properties": "not_stated",
        },
    },
    "1.2": {'release': {'date': '2018-11-08', 'status': 'Completed', 'evidence': "releases/1.2/DCAT_AP_1.2.pdf, document metadata ('Release date')"}, 'dcat_basis': {'dcat': 'dcat-2014', 'cited_as': 'W3C. Data Catalog Vocabulary (DCAT). W3C Recommendation 16 January 2014.', 'dcat_status_at_release': 'W3C Recommendation (2014-01-16); DCAT 2 was a Working Draft (verify)', 'evidence': [{'file': 'releases/1.2/DCAT_AP_1.2.pdf', 'section': '1 Introduction (The DCAT specification)', 'quote': 'The DCAT Application Profile defined in this document is based on the specification of the Data Catalog Vocabulary (DCAT) of 16 January 2014.'}], 'notes': [], 'unlisted_dcat_properties': 'not_stated'}},
    "1.2.1": {'release': {'date': '2019-05-28', 'status': 'Completed', 'evidence': "releases/1.2.1/DCAT_AP_1.2.1.pdf, document metadata ('Release date')"}, 'dcat_basis': {'dcat': 'dcat-2014', 'cited_as': 'W3C. Data Catalog Vocabulary (DCAT). W3C Recommendation 16 January 2014.', 'dcat_status_at_release': 'W3C Recommendation (2014-01-16); DCAT 2 was a Working Draft (verify)', 'evidence': [{'file': 'releases/1.2.1/DCAT_AP_1.2.1.pdf', 'section': '1 Introduction (The DCAT specification)', 'quote': 'The DCAT Application Profile defined in this document is based on the specification of the Data Catalog Vocabulary (DCAT) of 16 January 2014.'}], 'notes': [], 'unlisted_dcat_properties': 'not_stated'}},
    "2.0.0": {'release': {'date': '2019-11-20', 'status': 'Completed', 'evidence': "releases/2.0.0/DCAT_AP_2.0.0.pdf, document metadata ('Release date')"}, 'dcat_basis': {'dcat': 'dcat-2', 'cited_as': 'Data Catalog Vocabulary (DCAT) - Version 2, W3C Candidate Recommendation 03 October 2019 (https://www.w3.org/TR/2019/CR-vocab-dcat-2-20191003/)', 'dcat_status_at_release': 'W3C Candidate Recommendation (2019-10-03); DCAT 2 became a W3C Recommendation on 2020-02-04', 'evidence': [{'file': 'releases/2.0.0/DCAT_AP_2.0.0.pdf', 'section': '1 Introduction (The DCAT specification)', 'quote': 'The DCAT Application Profile defined in this document is based on the specification of the Data Catalog Vocabulary (DCAT) of 16 January 2014, and the Data Catalog Vocabulary (DCAT) - Version 2, W3C Candidate Recommendation 03 October 2019.'}], 'notes': ['Also cites the DCAT of 16 January 2014; DCAT 2 keeps the 2014 terms in the same namespace, so DCAT 2 is pinned.', 'Built on the Candidate Recommendation of DCAT 2; data/dcat/dcat-2 holds the REC, whose DCAT term set and domains/ranges equal the CR-period RDF (see data/dcat/versions.yaml).'], 'unlisted_dcat_properties': 'not_stated'}},
    "2.0.1": {'release': {'date': '2020-06-08', 'status': 'Under Development (as stated in the document metadata; verify)', 'evidence': "releases/2.0.1/DCAT_AP_2.0.1.pdf, document metadata ('Release date')"}, 'dcat_basis': {'dcat': 'dcat-2', 'cited_as': 'Data Catalog Vocabulary (DCAT) - Version 2, W3C Recommendation 04 February 2020', 'dcat_status_at_release': 'W3C Recommendation (2020-02-04)', 'evidence': [{'file': 'releases/2.0.1/DCAT_AP_2.0.1.pdf', 'section': '1 Introduction (The DCAT specification)', 'quote': 'The DCAT Application Profile defined in this document is based on the specification of the Data Catalog Vocabulary (DCAT) of 16 January 2014, and the Data Catalog Vocabulary (DCAT) - Version 2, W3C Recommendation 04 February 2020.'}], 'notes': ['Also cites the DCAT of 16 January 2014; DCAT 2 keeps the 2014 terms in the same namespace, so DCAT 2 is pinned.'], 'unlisted_dcat_properties': 'not_stated'}},
    "2.1.0": {'release': {'date': '2021-11-25', 'status': 'Under Development (as stated in the document metadata; verify)', 'evidence': "releases/2.1.0/dcat-ap_2.1.0.pdf, document metadata ('Release date')"}, 'dcat_basis': {'dcat': 'dcat-2', 'cited_as': 'Data Catalog Vocabulary (DCAT) - Version 2, W3C Recommendation 04 February 2020', 'dcat_status_at_release': 'W3C Recommendation (2020-02-04)', 'evidence': [{'file': 'releases/2.1.0/dcat-ap_2.1.0.pdf', 'section': '1 Introduction (The DCAT specification)', 'quote': 'The DCAT Application Profile defined in this document is based on the specification of the Data Catalog Vocabulary (DCAT) of 16 January 2014, and the Data Catalog Vocabulary (DCAT) - Version 2, W3C Recommendation 04 February 2020.'}, {'file': 'releases/2.1.0/dcat-ap_2.1.0.pdf', 'quote': 'Any property that is mentioned in DCAT applicable to a class but not explicitly is listed DCAT-AP is considered an optional field for DCAT-AP for that class.'}], 'notes': ['Also cites the DCAT of 16 January 2014; DCAT 2 keeps the 2014 terms in the same namespace, so DCAT 2 is pinned.'], 'unlisted_dcat_properties': 'optional'}},
    "2.1.1": {'release': {'date': '2022-06-24', 'status': 'Completed', 'evidence': "releases/2.1.1/dcat-ap_2.1.1.pdf, document metadata ('Release date')"}, 'dcat_basis': {'dcat': 'dcat-2', 'cited_as': 'Data Catalog Vocabulary (DCAT) - Version 2, W3C Recommendation 04 February 2020', 'dcat_status_at_release': 'W3C Recommendation (2020-02-04)', 'evidence': [{'file': 'releases/2.1.1/dcat-ap_2.1.1.pdf', 'section': '1 Introduction (The DCAT specification)', 'quote': 'The DCAT Application Profile defined in this document is based on the specification of the Data Catalog Vocabulary (DCAT) of 16 January 2014, and the Data Catalog Vocabulary (DCAT) - Version 2, W3C Recommendation 04 February 2020.'}, {'file': 'releases/2.1.1/dcat-ap_2.1.1.pdf', 'quote': 'Any property that is mentioned in DCAT applicable to a class but not explicitly is listed DCAT-AP is considered an optional field for DCAT-AP for that class.'}], 'notes': ['Also cites the DCAT of 16 January 2014; DCAT 2 keeps the 2014 terms in the same namespace, so DCAT 2 is pinned.'], 'unlisted_dcat_properties': 'optional'}},
    "3.0.0": {
        "release": {"date": "2024-06-14", "status": "SEMIC Recommendation",
                    "evidence": "releases/3.0.0/index.html: 'This application profile has the status SEMIC Recommendation "
                                "published at 2024-06-14.'"},
        "dcat_basis": {
            "dcat": "dcat-3",
            "cited_as": "[[vocab-dcat-3]] (W3C DCAT Version 3)",
            "dcat_status_at_release": "W3C Proposed Recommendation (2024-06-13); it became a W3C Recommendation on 2024-08-22",
            "evidence": [
                {"file": "releases/3.0.0/index.html",
                 "quote": "The Application Profile specified in this document is based on the specification of the Data "
                          "Catalog Vocabulary (DCAT) [[vocab-dcat-3]] developed under the responsibility of the [[[DXWG]]] "
                          "(DXWG) at W3C."},
                {"file": "releases/3.0.0/index.html",
                 "quote": "Any property that is mentioned in DCAT applicable to a class but not explicitly is listed DCAT-AP "
                          "is considered an optional field for DCAT-AP for that class."},
            ],
            "notes": ["releases/3.0.0/html/shacl/imports.ttl imports https://www.w3.org/ns/dcat2.ttl (the DCAT 2 RDF), "
                      "although the text is based on DCAT 3."],
            "unlisted_dcat_properties": "optional",
        },
    },
    "3.0.1": {
        "release": {"date": "2025-07-10", "status": "SEMIC Draft Specification (as stated in the release text; verify)",
                    "evidence": "releases/3.0.1/index.html: 'This application profile has the status SEMIC Draft "
                                "Specification published at 2025-07-10.'"},
        "dcat_basis": {
            "dcat": "dcat-3",
            "cited_as": "[[vocab-dcat-3]] (W3C DCAT Version 3)",
            "dcat_status_at_release": "W3C Recommendation (2024-08-22)",
            "evidence": [
                {"file": "releases/3.0.1/index.html",
                 "quote": "The Application Profile specified in this document is based on the specification of the Data "
                          "Catalog Vocabulary (DCAT) [[vocab-dcat-3]] developed under the responsibility of the [[[DXWG]]] "
                          "(DXWG) at W3C."},
                {"file": "releases/3.0.1/index.html",
                 "quote": "Any property that is mentioned in DCAT applicable to a class but not explicitly is listed DCAT-AP "
                          "is considered an optional field for DCAT-AP for that class."},
            ],
            "notes": ["releases/3.0.1/html/shacl/imports.ttl imports https://www.w3.org/ns/dcat2.ttl (the DCAT 2 RDF), "
                      "although the text is based on DCAT 3."],
            "unlisted_dcat_properties": "optional",
        },
    },
}
DCAT_CLASSES = {  # classes of each DCAT version (data/dcat/<id>/model.json), to keep main_classes in-version
    "dcat-2014": {"dcat:Catalog", "dcat:Dataset", "dcat:Distribution", "dcat:CatalogRecord"},
    "dcat-2": {"dcat:Catalog", "dcat:Dataset", "dcat:Distribution", "dcat:DataService", "dcat:CatalogRecord"},
    "dcat-3": {"dcat:Catalog", "dcat:Dataset", "dcat:Distribution", "dcat:DataService", "dcat:DatasetSeries",
               "dcat:CatalogRecord"},
}


# The DCAT URL each release's own basis footnote cites (1.x: the dated 2014 REC; 2.0.0: the dated CR;
# 2.0.1/2.1.x: the undated DCAT 2 URL; 3.x: [[vocab-dcat-3]], the undated DCAT 3 URL).
CITED_URLS = {
    "1.1": "http://www.w3.org/TR/2014/REC-vocab-dcat-20140116/",
    "1.2": "http://www.w3.org/TR/2014/REC-vocab-dcat-20140116/",
    "1.2.1": "http://www.w3.org/TR/2014/REC-vocab-dcat-20140116/",
    "2.0.0": "https://www.w3.org/TR/2019/CR-vocab-dcat-2-20191003/",
    "2.0.1": "https://www.w3.org/TR/vocab-dcat-2/",
    "2.1.0": "https://www.w3.org/TR/vocab-dcat-2/",
    "2.1.1": "https://www.w3.org/TR/vocab-dcat-2/",
    "3.0.0": "https://www.w3.org/TR/vocab-dcat-3/",
    "3.0.1": "https://www.w3.org/TR/vocab-dcat-3/",
}


def dcat_blocks(release: str) -> str:
    """The release/dcat_basis blocks of profile.yaml, as YAML text."""
    basis = {**DCAT_BASIS[release], "dcat_basis": {**DCAT_BASIS[release]["dcat_basis"], "cited_url": CITED_URLS[release]}}
    return ("# The W3C DCAT state this release builds on (scripts/build_base_profile.py DCAT_BASIS).\n"
            + yaml.safe_dump({"release": basis["release"], "dcat_basis": basis["dcat_basis"]}, sort_keys=False,
                             allow_unicode=True, width=110))


def main_classes_for(release: str) -> list[str]:
    allowed = DCAT_CLASSES[DCAT_BASIS[release]["dcat_basis"]["dcat"]]
    return [curie for curie in MAIN_CLASSES if curie in allowed]


def update_dcat_basis(profile_path: Path, release: str) -> None:
    """Rewrite only the release/dcat_basis blocks and main_classes of an existing profile.yaml."""
    import re as _re

    text = profile_path.read_text(encoding="utf-8")
    text = _re.sub(r"# The W3C DCAT state this release builds on.*\Z", "", text, flags=_re.S).rstrip() + "\n"
    classes = "".join(f"- {curie}\n" for curie in main_classes_for(release))
    text = _re.sub(r"main_classes:\n(?:- [^\n]+\n)+", "main_classes:\n" + classes, text)
    profile_path.write_text(text + dcat_blocks(release), encoding="utf-8")


def strip_tags(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def read_quick_reference(spec_html: str) -> list[dict[str, str]]:
    """Rows of the quick-reference table: class label, class IRI, obligation, property label, property IRI."""
    start = spec_html.index('id="table-quickoverview"')
    table = spec_html[start: spec_html.index("</table>", start)]
    rows = []
    for row in re.findall(r"<tr>\s*(<td>.*?)</tr>", table, flags=re.S):
        cells = re.findall(r"<td>(.*?)</td>", row, flags=re.S)
        if len(cells) != 5:
            continue
        class_label, class_iri, obligation, property_label, property_iri = (strip_tags(cell) for cell in cells)
        if not property_iri or obligation.lower() not in {"mandatory", "recommended", "optional"}:
            continue
        rows.append({
            "class_label": class_label, "class_iri": class_iri, "obligation": obligation.lower(),
            "property_label": property_label, "property_iri": property_iri,
        })
    return rows


CLASS_LABELS = {   # class labels of the release RDF ("Data Catalogue - description"), any case
    "Data Catalogue": "dcat:Catalog", "Catalogue": "dcat:Catalog", "Catalogue Record": "dcat:CatalogRecord",
    "Dataset": "dcat:Dataset", "Distribution": "dcat:Distribution", "Agent": "foaf:Agent",
    "Category Scheme": "skos:ConceptScheme", "Category": "skos:Concept", "Licence Document": "dct:LicenseDocument",
    "Checksum": "spdx:Checksum", "Identifier": "adms:Identifier", "Period of Time": "dct:PeriodOfTime",
    "Data Service": "dcat:DataService", "Location": "dct:Location", "Relationship": "dcat:Relationship",
}


# Typos in the property IRIs of the release RDF files (releases/<r>/dcat-ap_<r>.rdf), corrected to the
# IRIs the release's PDF specification names (checked: 1.1, 1.2, 2.0.0, 2.0.1 and 2.1.1 PDFs write
# dcat:contactPoint, dct:accrualPeriodicity, dcat:mediaType, dcat:servesDataset, prov:..., locn:geometry,
# time:hasBeginning / time:hasEnd). The shapes use the correct IRIs, so without these corrections the
# properties lose their obligation level. Typos INSIDE the official shapes (2.0.x/2.1.0
# "http://data.europa.eu/r5ravailability", 2.x "dcterms:licence" on DataService and
# "http://purl.org/dc/elements/1.1/isReferencedBy") are left as published: the shapes stay unmodified.
NAMESPACE_ERRATA = {
    "https://www.w3.org/ns/dcat#": "http://www.w3.org/ns/dcat#",
    "https://www.w3.org/ns/prov#": "http://www.w3.org/ns/prov#",
    "https://www.w3.org/ns/locn#": "http://www.w3.org/ns/locn#",
    "https://www.w3.org/TR/owl-time/#time:": "http://www.w3.org/2006/time#",
    "http://www.w3.org/2006/time/": "http://www.w3.org/2006/time#",
}
TERM_ERRATA = {
    "http://purl.org/dc/terms/acrualPeriodicity": "http://purl.org/dc/terms/accrualPeriodicity",  # PDF: dct:accrualPeriodicity
    "http://purl.org/dc/terms/mediaType": "http://www.w3.org/ns/dcat#mediaType",               # PDF: dcat:mediaType
    "http://www.w3.org/ns/dcat#servesdataset": "http://www.w3.org/ns/dcat#servesDataset",      # PDF: dcat:servesDataset
}


# Obligations a release's PDF states but its RDF omits (no vann:usageNote), so they are added here, with
# the section that states them. Checked in the 2.0.0, 2.0.1, 2.1.0 and 2.1.1 PDFs (sections 4.1.3 and 4.3.2,
# and Annex I "Quick reference of classes and properties").
OBLIGATION_SUPPLEMENTS = {
    release: [
        {"class": "dcat:Catalog", "property": "dct:creator", "obligation": "optional",
         "source": "PDF 4.1.3 Optional properties for Catalogue; Annex I"},
        {"class": "dcat:DataService", "property": "dcat:endpointDescription", "obligation": "recommended",
         "source": "PDF 4.3.2 Recommended properties for Data Service; Annex I"},
    ]
    for release in ("2.0.0", "2.0.1", "2.1.0", "2.1.1")
}


def correct_iri(iri: str) -> str:
    for wrong, right in NAMESPACE_ERRATA.items():
        if iri.startswith(wrong):
            iri = right + iri[len(wrong):]
            break
    return TERM_ERRATA.get(iri, iri)


def read_obligations_rdf(rdf_text: str, corrections: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    """DCAT-AP 1.x and 2.x state obligations in each property's vann:usageNote ("Mandatory property. ...")
    and the class in its rdfs:label ("Data Catalogue - description"). Corrected IRIs are appended to
    ``corrections``."""
    rows = []
    for block in re.findall(r'<rdf:Description rdf:about="([^"]+)">(.*?)</rdf:Description>', rdf_text, flags=re.S):
        about, body = block
        note = re.search(r"<vann:usageNote[^>]*>\s*(Mandatory|Recommended|Optional) property", body)
        label = re.search(r"<rdfs:label[^>]*>([^<]+)</rdfs:label>", body)
        if not note or not label or " - " not in label.group(1):
            continue
        class_label, property_label = (part.strip() for part in label.group(1).split(" - ", 1))
        class_curie = {key.lower(): value for key, value in CLASS_LABELS.items()}.get(class_label.lower())
        if class_curie is None:
            print(f"warning: unknown class label {class_label!r} for {about}", file=sys.stderr)
            continue
        rows.append({"class_label": class_label, "class_iri": Prefixes().expand(class_curie), "obligation": note.group(1).lower(),
                     "property_label": property_label, "property_iri": correct_iri(about)})
        if correct_iri(about) != about and corrections is not None:
            corrections.append({"class": class_curie, "from": about, "to": correct_iri(about)})
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--semic-repo", type=Path, help="checkout of github.com/SEMICeu/DCAT-AP")
    parser.add_argument("--dcat-basis-only", action="store_true",
                        help="only rewrite the DCAT basis (release, dcat_basis, main_classes) of an existing profile.yaml")
    parser.add_argument("--release", required=True, choices=sorted(RELEASE_FILES))
    parser.add_argument("--out", type=Path, default=ROOT / "backend" / "profile_extensioner" / "data" / "base-profiles")
    args = parser.parse_args(argv)
    if args.dcat_basis_only:
        update_dcat_basis(args.out / f"dcat-ap-{args.release}" / "profile.yaml", args.release)
        print(f"dcat-ap-{args.release}: DCAT basis {DCAT_BASIS[args.release]['dcat_basis']['dcat']}")
        return 0
    if args.semic_repo is None:
        parser.error("--semic-repo is required")

    release_dir = args.semic_repo / "releases" / args.release
    files = RELEASE_FILES[args.release]
    target = args.out / f"dcat-ap-{args.release}"
    (target / "shacl").mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "-C", str(args.semic_repo), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=False).stdout.strip()

    sources = []
    if files.get("zip"):
        import zipfile

        archive = release_dir / files["zip"]
        sources.append({"path": f"releases/{args.release}/{files['zip']}", "sha256": sha256(archive)})
        with zipfile.ZipFile(archive) as bundle:
            for relative in files["constraints"] + files["ranges"]:
                member = bundle.read(relative)
                (target / "shacl" / Path(relative).name).write_bytes(member)
                sources.append({"path": f"releases/{args.release}/{files['zip']}!/{relative}",
                                "sha256": hashlib.sha256(member).hexdigest()})
    else:
        for relative in files["constraints"] + files["ranges"] + files.get("not_loaded", []) + files.get("deprecated", []):
            source = release_dir / relative
            shutil.copyfile(source, target / "shacl" / source.name)
            sources.append({"path": f"releases/{args.release}/{relative}", "sha256": sha256(source)})
    corrections: list[dict[str, str]] = []
    if files["obligations"] == "rdf":
        spec_path = release_dir / f"dcat-ap_{args.release}.rdf"
        rows = read_obligations_rdf(spec_path.read_text(encoding="utf-8"), corrections)
    else:
        spec_path = release_dir / "index.html"
        rows = read_quick_reference(spec_path.read_text(encoding="utf-8"))
    prefixes = Prefixes()
    supplements = OBLIGATION_SUPPLEMENTS.get(args.release, [])
    present = {(row["class_iri"], row["property_iri"]) for row in rows}
    for item in supplements:
        key = (prefixes.expand(item["class"]), prefixes.expand(item["property"]))
        if key not in present:
            rows.append({"class_label": item["class"], "class_iri": key[0], "obligation": item["obligation"],
                         "property_label": item["property"], "property_iri": key[1]})
    classes: dict[str, dict] = {}
    for row in rows:
        entry = classes.setdefault(prefixes.compact(row["class_iri"]), {"label": row["class_label"], "properties": {}})
        entry["properties"][prefixes.compact(row["property_iri"])] = row["obligation"]
    counts = {level: sum(1 for row in rows if row["obligation"] == level) for level in ("mandatory", "recommended", "optional")}

    header = (
        f"# Obligation level of every property of DCAT-AP {args.release}, per class.\n"
        f"# Generated by scripts/build_base_profile.py from the "
        f"{'usage notes' if files['obligations'] == 'rdf' else 'quick-reference table'} of\n"
        f"# releases/{args.release}/{spec_path.name} (SEMICeu/DCAT-AP @ {commit[:12]}, sha256 {sha256(spec_path)[:16]}...).\n"
        f"# {counts['mandatory']} mandatory, {counts['recommended']} recommended, {counts['optional']} optional. Do not edit by hand.\n"
        + "".join(f"# corrected IRI ({item['class']}): {item['from']} -> {item['to']}\n" for item in corrections)
        + "".join(f"# added from the PDF ({item['class']} {item['property']}: {item['obligation']}): {item['source']}\n"
                  for item in supplements)
    )
    (target / "obligations.yaml").write_text(
        header + yaml.safe_dump({"classes": classes}, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    profile = {
        "id": f"dcat-ap-{args.release}",
        "title": f"DCAT-AP {args.release}",
        "version": args.release,
        "description": "DCAT Application Profile for data portals in Europe (SEMIC).",
        "homepage": f"https://semiceu.github.io/DCAT-AP/releases/{args.release}/" if files["obligations"] == "html" else "",
        "licence": "CC-BY-4.0",
        "source": {
            "repository": "https://github.com/SEMICeu/DCAT-AP",
            "commit": commit,
            "files": sources + [{"path": f"releases/{args.release}/{spec_path.name}", "sha256": sha256(spec_path)}],
        },
        "shapes": {
            "constraints": [f"shacl/{Path(name).name}" for name in files["constraints"]],
            "ranges": [f"shacl/{Path(name).name}" for name in files["ranges"]],
            # Deprecated URIs the release names (sh:message "replace X with Y"); not used as constraints.
            "deprecated": [f"shacl/{Path(name).name}" for name in files.get("deprecated", [])],
            # Vendored but not loaded (see RELEASE_FILES for the reason).
            "not_loaded": [f"shacl/{Path(name).name}" for name in files.get("not_loaded", [])],
        },
        "obligations": "obligations.yaml",
        "main_classes": main_classes_for(args.release),
    }
    mirrors = []
    for mirror in files.get("mirrors", []):
        vendored = target / "shacl" / Path(mirror["same_as"]).name
        mirrors.append({**mirror, "sha256": sha256(vendored)})
    if mirrors:
        profile["source"]["mirrors"] = mirrors
    if (target / "dsv-index.json").exists():
        # DSV of this release published by the Dataspecer team; extensions point at its profiles (dsv:profileOf).
        profile["dsv_index"] = "dsv-index.json"
    if files.get("implicit"):
        # 1.1 and 1.2 shapes use implicit class targets (shape IRI = class IRI) without typing the IRI as a class.
        profile["implicit_class_targets"] = True
    (target / "profile.yaml").write_text(
        "# Generated by scripts/build_base_profile.py. The shape files are the official ones, unmodified.\n"
        + yaml.safe_dump(profile, sort_keys=False, allow_unicode=True) + dcat_blocks(args.release),
        encoding="utf-8",
    )
    print(f"{target}: {len(classes)} classes, {len(rows)} properties {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
