"""Every base's official shapes graph is usable by a SHACL engine: one bare instance of every target class
validates without the engine rejecting the shapes (adversarial review: 2.1.0 range file, 3.0.1 DataService)."""
import pytest
from pyshacl import validate
from rdflib import BNode, Graph, URIRef
from rdflib.namespace import RDF, SH

from profile_extensioner.knowledge import list_base_profiles, load_base_profile


@pytest.mark.parametrize("base_id", [info.id for info in list_base_profiles()])
def test_a_bare_instance_of_every_target_class_validates(base_id):
    base = load_base_profile(base_id)
    shapes = base.shapes_graph()
    targets = set(shapes.objects(None, SH.targetClass)) | set(base.index.classes and map(URIRef, base.index.classes))
    data = Graph()
    for cls in targets:
        if isinstance(cls, URIRef):
            data.add((BNode(), RDF.type, cls))
    conforms, _, _ = validate(data, shacl_graph=shapes, inference="none", allow_warnings=True)
    assert conforms in (True, False)          # the engine accepted the shapes (it raises otherwise)
