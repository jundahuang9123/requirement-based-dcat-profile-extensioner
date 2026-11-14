"""Our DCAT models (data/dcat/*/model.json, extracted from the W3C specification texts) against the
Dataspecer team's DCAT application profiles (DSV), used as an independent oracle.

Fixtures: tests/fixtures/dap/dcat3-dap.dsv.ttl and dcat2-dap.dsv.ttl, from mff-uk/specifications @ 833685e
(`dcat-dap/dsv.ttl`, `dcat2-dap/dsv.ttl`; MIT, see tests/fixtures/dap/LICENSE). Every known difference is
listed below with the reason (docs/research/B3-dataspecer-update.md, section 3)."""
import json
from pathlib import Path

import pytest
from rdflib import Graph, Namespace

from profile_extensioner.knowledge import DATA_DIR

DSV = Namespace("https://w3id.org/dsv#")
FIXTURES = Path(__file__).parent / "fixtures" / "dap"
DCAT, DCT = "http://www.w3.org/ns/dcat#", "http://purl.org/dc/terms/"

# (class, property) pairs the DCAT text lists that the DAP lacks, with the reason.
ONLY_OURS = {
    "dcat-2": {
        # DCAT 2 lists both under Data Service; the DAP was made by "downgrading" the DCAT 3 one (B3 3.2).
        (DCAT + "DataService", DCT + "license"),
        (DCAT + "DataService", DCT + "accessRights"),
    },
    "dcat-3": set(),
}


def dap_pairs(path: Path) -> set[tuple[str, str]]:
    graph = Graph()
    graph.parse(path, format="turtle")
    pairs = set()
    for profile, prop in graph.subject_objects(DSV.property):
        for domain in graph.objects(profile, DSV.domain):
            for cls in graph.objects(domain, DSV["class"]):
                pairs.add((str(cls), str(prop)))
    return pairs


def our_pairs(version: str) -> set[tuple[str, str]]:
    model = json.loads((DATA_DIR / "dcat" / version / "model.json").read_text(encoding="utf-8"))
    return {(cls, prop["path"]) for cls, entry in model["classes"].items() for prop in entry["properties"]}


@pytest.mark.parametrize("version, fixture", [("dcat-3", "dcat3-dap.dsv.ttl"), ("dcat-2", "dcat2-dap.dsv.ttl")])
def test_every_pair_of_the_dcat_text_is_in_the_dataspecer_profile(version, fixture):
    ours, theirs = our_pairs(version), dap_pairs(FIXTURES / fixture)
    assert ours - theirs == ONLY_OURS[version]
    # and the other way round: everything they have, we have (DCAT 3: all 89 pairs)
    if version == "dcat-3":
        assert theirs <= ours


def test_repeated_rows_and_typed_literals_are_kept():
    model = json.loads((DATA_DIR / "dcat" / "dcat-3" / "model.json").read_text(encoding="utf-8"))["classes"]
    assert model[DCAT + "DataService"]["subclass_of"][0] == DCAT + "Resource"            # two "Sub-class of" rows
    size = next(p for p in model[DCAT + "Distribution"]["properties"] if p["path"] == DCAT + "byteSize")
    assert size["range"] == ["http://www.w3.org/2001/XMLSchema#nonNegativeInteger"]      # "rdfs:Literal typically typed as"
    roles = [p["path"] for p in model["http://www.w3.org/ns/prov#Attribution"]["properties"]]
    assert roles == [DCAT + "hadRole"]                                                  # "Domain: prov:Attribution or dcat:Relationship"
