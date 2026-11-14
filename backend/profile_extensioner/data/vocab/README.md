# Vendored vocabularies (vocabulary index)

Machine-readable copies of the vocabularies DCAT-AP extensions draw on, flattened to
Turtle by `scripts/vendor_vocabularies.py`. `MANIFEST.json` records for each file the
source URL, source version/commit, SHA-256 of the source and of the copy, the triple
count and the licence **as stated by the source**.

Licences marked `verify:` were not stated inside the RDF file itself; they were taken
from the publisher's documentation and must be checked before this tool is
redistributed with them. Retrieval down-weights vocabularies made for specific domains
(ELI, SPDX, ODRL, OWL-Time, LOCN, vCard); see `engine/retrieve.py`.

DCAT is not in this directory. Every W3C DCAT version (2014, 2, 3) is kept under
`data/dcat/`, unmodified, together with its specification text; a project's index holds
the DCAT version its base profile builds on (see `data/dcat/README.md`).
