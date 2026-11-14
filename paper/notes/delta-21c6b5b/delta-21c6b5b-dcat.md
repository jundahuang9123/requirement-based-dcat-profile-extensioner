# Delta 5ffd56e -> 21c6b5b, area "dcat": DCAT state, bases, conformance, compilation

Old: worktree `main-wt` (5ffd56e). New: worktree `main-wt2` (21c6b5b). Commits in the range (`git log 5ffd56e..21c6b5b`):
9321951, 40a5d5d, a3d8098 ("Close the paper session's NEW-3..NEW-10 findings"), 913bea2 ("... imports that resolve"),
21c6b5b ("... shapes"). `B/` = `backend/profile_extensioner/`, `BP/` = `B/data/base-profiles/`, `DD/` = `B/data/dcat/`.
Every anchor is at 21c6b5b unless marked `@5ffd56e`.

**Evidence.** (code) read in the source; (probe) offline, in memory, `python -B`, `PYTHONDONTWRITEBYTECODE=1`, mock
provider, synthetic changes or `examples/materials-testing-lab` only, run on both worktrees (scripts in
`scratchpad/probes-dcat/p1..p19`); (recorded) a statement in a vendored file I could not check against its source.
No network was used: whether an `owl:imports` URL resolves and whether the 1.1 mirror is byte-identical **remotely** are
`verify` items. No benchmark material was opened. Both worktrees are unchanged (`git status --porcelain`).

---

## 1. What changed

### 1.1 DCAT models (extractor fix) and the Dataspecer oracle
- `scripts/build_dcat_versions.py:165-246` `extract_model`: repeated row labels are kept as lists (DCAT 3 "Class: Data
  Service" has two "Sub-class of" rows and two "Usage note" rows); "rdfs:Literal (typically) typed as xsd:X" gives
  range `xsd:X` only; a "Domain: A or B" row attaches the property to the other class too (`from_domain`).
- Effect on `DD/*/model.json` (diff): `dcat:DataService` gets `subclass_of [dcat:Resource, dctype:Service]` (DCAT 2 and
  3); `prov:Attribution` is a new class with `dcat:hadRole`; `dcat:byteSize`, `dcat:spatialResolutionInMeters`,
  `dcat:temporalResolution` lose the extra `rdfs:Literal`; usage notes are complete.
- Counts (probe p11, re-extraction in memory equals `model.json` for all three versions; DCAT 3 PR text = REC text):
  dcat-2014 6 classes / 44 pairs (unchanged), dcat-2 **13 / 76** (was 12/75), dcat-3 **15 / 89** (was 14/88);
  `DD/versions.yaml:72-73,121-122`.
- Oracle (probe p1; `tests/test_dcat_model_vs_dap.py:79-111`; fixtures `tests/fixtures/dap/*.dsv.ttl`, MIT,
  mff-uk/specifications @ 833685e): **DCAT 3: ours 89 = theirs 89, all shared** (5ffd56e: 88 of 89, missing
  `prov:Attribution dcat:hadRole`). **DCAT 2: all 74 DAP pairs in ours**, plus 2 pairs only ours
  (`dcat:DataService dct:license`, `dct:accessRights`), allow-listed with a reason (5ffd56e: 73 of 74 shared). The
  oracle compares (class, property) pairs only; the hierarchy and ranges are pinned by three asserts
  (`tests/test_dcat_model_vs_dap.py:114-120`), and the DAP's range simplifications (B3 doc §3.1 groups G1, G3-G5)
  still differ by design.
- Side effect (probe p10): DataService now inherits dcat:Resource's listed properties, so the retrieval rung of
  "properties the base's DCAT lists for the class but the base does not profile" grew: 2.x **23 -> 41** (DataService
  +18), 3.x **107 -> 131** (DataService +23, prov:Attribution +1); 1.x stays **0**.

### 1.2 DCAT state API
- `B/knowledge/dcat_state.py:162-205`: `superclasses`, `properties_for`, `listed_for`, `classes_listing` take an
  optional `version` (default: the pinned one). Used by D1 to place a later term by the version that introduced it
  (`B/engine/verify.py:264-283`). `status()` is unchanged (`:127-146`).

### 1.3 Bases (`BP/*/profile.yaml`, `obligations.yaml`, `B/knowledge/base_profile.py`)
- **Range shapes loaded** for 2.1.0/2.1.1 (`base_profile.py:93-97`; `BP/dcat-ap-2.1.0/profile.yaml:23-24`). 3.0.1's
  `ranges.ttl` moves to `shapes.not_loaded` (`BP/dcat-ap-3.0.1/profile.yaml:23-27`): 206 of its 297 `sh:property`
  nodes have no `sh:path` (probe p5; reason in `scripts/build_base_profile.py:60-63`).
- **In-memory repair** (`base_profile.py:106-115`, recorded in `BaseProfileInfo.shape_fixes`,
  `B/contracts.py:274`): every `sh:property` link to a node without `sh:path` is dropped. Probe p2: only 2.1.0 (1 link,
  an empty `sh:property [ ]` on `r5r:PeriodOfTime_Shape` in the range file) and 3.0.1 (2 links on
  `dcat:DataServiceShape`). Probe p5: pySHACL 0.40.2 raises "not a well-formed SHACL PropertyShape" on both raw files
  once a focus node reaches the shape. The vendored files still match their recorded sha256 (probe p2, all bases).
- **Hashes:** 1.1 and 1.2 now also record the sha256 of the shape file inside the zip
  (`BP/dcat-ap-1.1/profile.yaml:14-15`, `BP/dcat-ap-1.2/profile.yaml:14-15`); both equal the vendored files (probe p2).
- **Mirror:** 1.1 records SEMICeu/dcat-ap_shacl @ c9683b1 `shacl/dcat-ap.shapes.ttl`, `same_as` the zip member, with the
  same sha256 (`BP/dcat-ap-1.1/profile.yaml:18-23`). That sha256 is computed from the vendored file; the
  `verified: true` that `--verify-mirrors` writes (`scripts/build_base_profile.py:394-408`) is absent. The byte
  identity of the remote file is stated in a comment (`:42-43`, "checked ... 2026-11-14") and the commit message only.
- **Cited DCAT URL** `dcat_basis.cited_url` (`B/contracts.py:247`; `scripts/build_base_profile.py:151-168`): 1.x
  `http://www.w3.org/TR/2014/REC-vocab-dcat-20140116/`, 2.0.0 the dated DCAT 2 CR, 2.0.1-2.1.1 `.../TR/vocab-dcat-2/`,
  3.x `.../TR/vocab-dcat-3/` (the undated URL the release cites as `[[vocab-dcat-3]]`; recorded).
- **Obligations supplemented** (`scripts/build_base_profile.py:245-256, 343-349, 363-364`): 2.0.0, 2.0.1, 2.1.0, 2.1.1
  add `dcat:Catalog dct:creator` optional (PDF 4.1.3, Annex I) and `dcat:DataService dcat:endpointDescription`
  recommended (PDF 4.3.2, Annex I), recorded as "added from the PDF" (`BP/dcat-ap-2.0.0/obligations.yaml:30-31`, 2.1.1
  `:9-10`). Table rows 19/28/60 -> **19/29/61** (`paper/inputs/tool-facts-main-21c6b5b.txt:18-21`). The PDFs are not
  vendored (recorded).
- **Unknown obligations left** (probe p4; tool facts `:17-21`): 1.2.1 **2** (`dct:PeriodOfTime dcat:startDate/endDate`),
  2.0.0 **3**, 2.0.1 **3** (`dcat:DataService dcterms:licence`, `dcat:Dataset dc:isReferencedBy`,
  `dcat:Distribution r5r"availability"` without `#`), 2.1.0 **2**, 2.1.1 **1** (`dc:isReferencedBy`). Shape IRIs left as
  published. 1.1, 1.2, 3.x: 0.
- **1.1 header** now lists its three IRI corrections (`BP/dcat-ap-1.1/obligations.yaml:5-7`).
- Unhandled SHACL constructs (tool facts): 2.1.0 8 -> 9, 2.1.1 13 -> 14 (the range file's `sh:node` on
  `r5r:Relationship_Shape dct:relation`), 3.0.1 1 -> 0. Classes and elements per base unchanged.
- `base_profile.py:369-370`: the base's per-class shape ranges are no longer copied into the index term's declared
  range. Affected (probe p15): 3.x `dcatap:applicableLegislation`; 2.0.x `dcterms:licence`, `r5r"availability"`.
- Caches sized for nine bases (`B/knowledge/__init__.py:145`, `base_profile.py:433`).

### 1.4 KnowledgeBase (`B/knowledge/__init__.py`)
- `base_deprecation` (`:83-94`): a base deprecation also applies to subclasses of the declaring class; used by D2
  (`B/engine/verify.py:257-262`) and retrieval (`B/engine/retrieve.py:188`).
- `for_model` / `neutral` (`:38-56`): minted terms as `NEW:localName` (probe p14; blind-runs area, noted only).
- Index unchanged: 926 to 933 terms per base, 12 vocabularies, 60 DCAT terms (tool facts `:2, 6-14`).

### 1.5 Conformance (`B/conformance/check.py`, `refinement.py`)
- **C1/counts** (`check.py:125-150`): an element the base's specification lists without a shape counts as in the base;
  its obligation is compared (test `tests/test_dcat_state.py:270-283`).
- **C2** (`refinement.py:168-173`): a class range against a literal range (datatype or `sh:nodeKind sh:Literal`) is a
  `range_kind` conflict. Shared by V3, the delta and C2. Probe p6: 3.0.1 Dataset `dct:publisher` + `xsd:string`, and
  `dct:title` + class `foaf:Agent`: C2 pass @5ffd56e, **C2 error** @21c6b5b. Not covered: a base IRI/blank-node kind
  without a class (3.0.1 `dcat:accessURL`) against a datatype passes C1/C2 (probe p8); V2 and C7 catch it.
- **C7** (`check.py:195-276`):
  - 10 more sample datatypes (`:49-58`): `xsd:hexBinary` no longer warns (probe p6);
  - at depth 3 an existing instance of the class is reused, closing cycles (`:206-211`); `Dataset dct:isPartOf
    dcat:Dataset` mandatory: warning -> pass (probe p17);
  - `sh:node` of an `sh:or` of classes gives an instance of the first alternative, **not filled** (`:218-224`;
    `B/knowledge/shacl_reader.py:257-264`);
  - the witness is validated against the **extension's own shapes**, then the base alone, then both together only when
    both pass (`:260-263`). The branch "valid under the extension, INVALID under the base" (error) can now fire
    (`:266-274`). See N1: it fires on generator gaps.
- C3-C6 and C8 unchanged in logic (C8 at `:74-109` names who decided a later term).

### 1.6 Compilation
- SHACL (`B/compile/shacl.py:33-46`): `owl:imports` the official shape files as raw RDF at the pinned commit
  (`BaseProfileInfo.shape_urls`, built at `base_profile.py:142-157`); 1.2 has none and gets `rdfs:seeAlso` its zip;
  `dcterms:conformsTo` the release page (homepage, 3.x only) and `cited_url`. Probe p3:

  | Base | owl:imports | rdfs:seeAlso | DCAT URL in dct:conformsTo |
  |---|---|---|---|
  | 1.1 | 1 (SEMIC's dcat-ap_shacl copy) | - | dated 2014 REC (http) |
  | 1.2 | 0 | the zip | dated 2014 REC (http) |
  | 1.2.1, 2.0.1 | 1 | - | 2014 REC / undated DCAT 2 |
  | 2.0.0 | 1 | - | dated DCAT 2 CR |
  | 2.1.0, 2.1.1 | 2 (shapes + range shapes) | - | undated DCAT 2 |
  | 3.0.0, 3.0.1 | 1 | - | release page + undated DCAT 3 |

  pySHACL does not follow `owl:imports` by default, so C6/C7 stay offline.
- DSV (`B/compile/linkml_dsv.py:130-145`): `prof:isProfileOf` = the base's DSV (3.0.1), else the release URL at the
  commit (GitHub tree, 1.x/2.x) or the homepage (3.0.0); never relative. `dct:conformsTo` the shape URLs (or the
  zip), the homepage and the DCAT URL; a `dct:description` names release date and DCAT state.
- Docs (`B/compile/docs.py:69-70, 87-96`): an automatic release is labelled "Released automatically, without human
  review"; each later-DCAT term says "accepted by a human reviewer" or "the automatic policy".
- Delta (`B/compile/model.py:65-75`): base element = shape or specification-only element; a lowered obligation is
  `loosened`. Still never `unchanged`.

### 1.7 Docs
`docs/conformance.md:29-32, 44, 51`; `docs/dcat-versions.md:129-151, 161, 181-185, 261-265`; `docs/design.md:23-35`.
Stale: see N2, N3.

---

## 2. The tool session's claims (dcat area)

| Claim | Verdict | Evidence |
|---|---|---|
| DCAT model extractor fixed | confirmed | `scripts/build_dcat_versions.py:165-246`; model.json reproducible in memory (probe p11) |
| Checked against Dataspecer's DCAT 2/3 DSVs: 89/89 pairs for DCAT 3 | confirmed | probe p1; `tests/test_dcat_model_vs_dap.py:105-111`. DCAT 2: 74/74 of theirs plus 2 allow-listed pairs of ours. Pairs only |
| owl:imports resolves for 8 of 9 bases | partly | present for 8 of 9 (probe p3; `B/compile/shacl.py:33-39`); resolution not checked offline (verify) |
| 1.1 imports through SEMIC's byte-identical dcat-ap_shacl copy | partly | imported (probe p3); recorded hashes equal (`BP/dcat-ap-1.1/profile.yaml:14-23`), but no `verified: true` and no remote check here (verify) |
| 1.2 names its zip | confirmed | SHACL `rdfs:seeAlso` (`shacl.py:37-39`), DSV `dct:conformsTo` (`linkml_dsv.py:136-137`); not imported |
| Two official shape files have links a SHACL engine rejects (2.1.0 range file, 3.0.1 DataService), repaired in memory only | confirmed | probe p5, p2; `base_profile.py:106-115`; files unmodified (sha256) |
| C2 catches a class range against a literal range | confirmed | `refinement.py:168-173`; probe p6; `tests/test_conformance_every_base.py:54-59`. Gap: IRI node kinds (N6) |
| PDF-stated obligations missing from the 2.x RDF supplemented and recorded | confirmed | `scripts/build_base_profile.py:245-256`; obligations.yaml headers; tool facts `:18-21`; PDF not vendored (verify) |
| (commit) per-class base ranges not taken as declared ranges | confirmed | `base_profile.py:369-370`; probe p15 |
| (commit) C7 closes cycles, handles sh:or classes and more XSD types, validates the extension's own shapes first | confirmed, with a regression | `check.py:49-58, 206-224, 260-274`; N1 |
| (commit) DCAT rung respects hidden namespaces | confirmed | `B/engine/retrieve.py:138-139` |
| (implicit) synthetic demo still conformant | confirmed | probe p13: "Conforms to DCAT-AP 3.0.1 (on DCAT 3): 1 added, 4 tightened, 0 loosened. 0 failing, 0 warnings" at both commits |

---

## 3. New issues at 21c6b5b

**N1 (high confidence, high impact on E4).** C7 now reports false errors, which make the verdict `non_conformant` and
block release (`B/engine/pipeline.py:174-176`), when the witness generator, not the extension, leaves a node the base
constrains unfilled. The extension's own shapes pass, the base fails, and `check.py:266-274` reports "Data valid under the
extension is INVALID under the base shapes". Probes p6, p7, p17 (warnings at 5ffd56e, errors at 21c6b5b):
- any change on `dcat:CatalogRecord` (even `dct:language` optional) or `dcat:Relationship` under 2.0.0, 2.0.1, 2.1.0,
  2.1.1. The mandatory `foaf:primaryTopic` (`sh:node :DcatResource_Shape`, an `sh:or` of classes) gets a bare
  `dcat:Catalog` (`check.py:218-224`), which lacks the Catalog's mandatory properties;
- `dcat:Catalog dct:hasPart` mandatory -> `dcat:Catalog` under 1.1, 2.1.1, 3.0.0 and 3.0.1: a node at the depth limit with no
  earlier instance of its class (`check.py:212-217`).
Tests miss it: `tests/test_conformance_every_base.py:46-51` covers Dataset, Distribution and Catalog only, and asserts
only that C7 ran. `docs/conformance.md:74-75` still says such cases "give a warning, not a failure".

**N2 (medium, doc/code).** `docs/conformance.md:50` (C7) says (a) base + extension and (b) base alone; the code checks
the extension alone, the base alone, then both together (`check.py:260-263`). `docs/conformance.md:45` (C2) does not list
the class-vs-literal rule. `docs/conformance.md:69-71` says an incomparable range is "reported as incomparable
(warning)", but conformance counts it `tightened` with no item (B2).

**N3 (low, doc).** `docs/dcat-versions.md:23-24` still gives the spec models as 12/75 (DCAT 2) and 14/88 (DCAT 3), but
`DD/versions.yaml:72-73,121-122` gives 13/76 and 15/89. The extractor fix and the DSV oracle are documented only in
`docs/research/B3-dataspecer-update.md` §3 and `tests/fixtures/dap/README.md`.

**N4 (low, provenance).** The 1.1 mirror's remote byte identity is not recorded in the data (no `verified: true`,
`BP/dcat-ap-1.1/profile.yaml:18-23` vs `scripts/build_base_profile.py:404-405`). The resolvability of the nine bases'
`owl:imports` targets was not checked offline.

**N5 (low-medium).** The in-memory repairs do not travel with the artefact. A validator that follows the delta's
`owl:imports` loads the official 2.1.0 range file and 3.0.1 `dcat-ap-SHACL.ttl`, which pySHACL rejects once a
`dct:PeriodOfTime` (2.1.0) or a `dcat:DataService` (3.0.1) is validated (probe p5).

**N6 (low).** C2's range-kind rule (`refinement.py:169-171`) ignores IRI/blank-node kinds without a class. Probe p8:
3.0.1 Distribution `dcat:accessURL` (`sh:nodeKind sh:BlankNodeOrIRI`) + `xsd:string` passes C1/C2. V2 errors at
verification (probe p18) and C7 errors.

**N7 (info).** The rung-2 pool grew through `DataService ⊑ Resource` (section 1.1). No paper number is affected.

**N8 (info).** Base-only properties lost their index range (section 1.3), so V2 checks no range for them.

---

## 4. README tool issues in this area (status at 21c6b5b)

| Id | Status | Evidence at 21c6b5b |
|---|---|---|
| B1 | changed | `xsd:hexBinary` fixed (`check.py:49-58`); range narrowing (publisher -> foaf:Organization) and `dcat:keyword` min 2 still warn, and so do a value-list member without its class (probes p6, p16); the error branch now fires, also falsely (N1) |
| B2 | still present | `check.py:136-150`; `refinement.py:152-156`; probe p6 (incomparable -> tightened, no item) |
| B3 | fixed (mostly) | imports for 8 of 9 bases, 1.2 seeAlso (`shacl.py:33-41`); isProfileOf absolute (`linkml_dsv.py:130-133`); resolution verify |
| B4 (NEW-3) | fixed | `check.py:125-136`; `model.py:65-75`; `tests/test_dcat_state.py:270-283` |
| B5 (NEW-4) | changed (partly fixed) | 2 supplements per 2.x; unknown now 2/3/3/2/1 (probe p4; tool facts `:17-21`); the shape typos remain |
| B6 | still present (partly) | `shacl.py:84` always Violation; identical refinement: delta tightened vs conformance unchanged (probe p7); lowered obligation now loosened in both |
| B7 | still present | `model.py:21-31`; `shacl.py:59`; `linkml_dsv.py:177`; `docs.py:100-104` |
| B8 | still present | `linkml_dsv.py:180`; probe p19 (one node with two `dsv:profileOf`) |
| B9 | still present | probe p9 (conformant); `check.py:163-182` |
| B10 | still present (delta part) | `refinement.py:217-218`; `model.py:75`; merge part: engine area |
| B11 | still present | no pattern facet in `refinement.py:83-221` |
| B12 | still present | probe p9 (`dcterms:rightsHolder` + foaf:Organization: V2 error); `vocab_index.py` unchanged |
| B13 | still present | probe p9 (1.1: V2 warning only; 3.0.1: D1 error) |
| B14 (NEW-6) | fixed | `verify.py:264-283`; `tests/test_dcat_state.py:286-292` |
| B15 (NEW-7) | fixed | `knowledge/__init__.py:83-94`; `verify.py:257`; `retrieve.py:188`; `tests/test_dcat_state.py:295-300` (intended scope still verify) |
| B16 | still present | `retrieve.py:217-232`, `:162` |
| B17 | still present | `retrieve.py:28-30` vs `:57-62` |
| B18 | fixed | `base_profile.py:93-97`; 3.0.1 `not_loaded` (`profile.yaml:26-27`); `docs/conformance.md:29-32` |
| B20 (NEW-10) | changed | the cited URL: 2.0.0 the CR; 3.0.0 the undated DCAT 3 URL as cited (`shacl.py:43-45`; `build_base_profile.py:151-163`) |
| C5 | still present | `README.md:95` "70 tests"; 170 pass (`paper/inputs/tests-main-21c6b5b-2026-11-14.txt:5`) |
| C6 (NEW-5) | fixed | `docs.py:87-96` |
| C7 (NEW-8) | fixed | `docs/conformance.md:42-51` (the C8 row is inside the table) |
| C8 (NEW-9) | fixed | `BP/dcat-ap-1.1/obligations.yaml:5-7` |
| C11 | still present | `pyproject.toml:26-27,32-33` (no `cli.py`, data undeclared); `linkml_dsv.py:10-11` stale; `LEGACY_CHANGE_TYPE` unused (`contracts.py:740`); `llm/registry.py:81-90` |
| E list | all still hold | V2 union domains (probe p12); 1.1: 0 unknown (probe p4); 404 (`api/app.py:168-173`); declared base (`api/app.py:253-260`); README nine releases (`README.md:39-41,112`) |

---

## 5. Paper impact

Respecting the ground rules: numbers only from files; `verify` where offline checks end; no test-case or reference
content; repository names only in `% src:` comments. Development runs 1-3 stay as they were.

| # | File:line | Current (short) | Replacement fact | Anchor @21c6b5b |
|---|---|---|---|---|
| 1 | 03-problem.tex:25-26 | "pairs a DCAT-AP release with the DCAT version ... DCAT 2014 for 1.1 and DCAT 3 for 3.0.1" | holds; update src | `B/contracts.py:240-253`; `BP/dcat-ap-1.1/profile.yaml:43`; `BP/dcat-ap-3.0.1/profile.yaml:44` |
| 2 | 03-problem.tex:27-29 | "merged from the official SHACL shapes ... A pair the specification lists without a shape has only an obligation." | holds; may add "(2.1.x: with their range shapes)" and that V3, C1 and the delta compare a specification-only obligation | `base_profile.py:93-97, 76-81`; `check.py:125-136`; `model.py:65-75` |
| 3 | 03-problem.tex:30-31 | "From 2.1.0 on, a property DCAT lists ... optional there" | holds; src `retrieve.py:134-158` (was 134-156) | `BP/dcat-ap-2.1.0/profile.yaml:54` |
| 4 | 03-problem.tex:32 | "926 to 933 terms ... 12 other vocabularies and all 60" | numbers hold; src -> tool-facts-main-21c6b5b | `paper/inputs/tool-facts-main-21c6b5b.txt:2,6-14`; `knowledge/__init__.py:113-162` |
| 5 | 03-problem.tex:100 (src) | "B/compile/model.py:52-78 (added, tightened or loosened; never unchanged)" | `model.py:52-81`; spec-only base element counts as base; lowered obligation = loosened | `model.py:65-75` |
| 6 | 03-problem.tex:116-117 | "node kinds shrink and obligations rise, but a datatype never changes" | add: "and a range never switches between resources and literals"; src comment "unchanged since 2b92d77" is wrong now | `refinement.py:168-173` |
| 7 | 03-problem.tex:117-118 (src) | C3/C4 `check.py:149-168`; C8 `:64-99`; D1-D3 `verify.py:219-283` | `check.py:163-182`; `:74-109`; `verify.py:224-293`; `contracts.py:619` | as stated |
| 8 | 03-problem.tex:119-120 (src) | "the base-only branch of C7 cannot fire" | wrong: C7 checks the extension's own shapes first, so that branch fires (N1); text holds | `check.py:260-274`; `shacl.py:27-46` |
| 9 | 04-pipeline.tex:37-39 | "(x1.4; the 1.x bases have none) ... terms the base deprecates are down-weighted too" | holds (1.x pool 0, probe p10); may add "on the class or a superclass" | `retrieve.py:41, 134-158, 188`; `knowledge/__init__.py:83-94` |
| 10 | 04-pipeline.tex:75-78 | "conformsTo names the dated Recommendation ... owl:imports names the release page for the 3.0.x bases and is absent for the others" | "The delta's dcterms:conformsTo names the DCAT text the base release cites (for 2.0.0 the Candidate Recommendation) and, for 3.0.x, the release page. Its owl:imports names the official shape files at the pinned commit for eight of the nine bases (1.1 through a byte-identical copy SEMIC publishes separately); 1.2 publishes its shapes only in an archive, which the delta names instead." + \verify{imports resolve; 1.1 copy byte-identical} | `shacl.py:33-46`; `base_profile.py:142-157`; `BP/dcat-ap-1.1/profile.yaml:18-23`; `scripts/build_base_profile.py:151-163` |
| 11 | 04-pipeline.tex:78-81 | "a DSV profile that, on a 3.0.1 base, profiles Dataspecer's DSV" | holds; optional: "and names the base release and its DCAT" | `linkml_dsv.py:130-145` |
| 12 | 04-pipeline.tex:85-88 | "validates it ... against base and extension and against the base alone. It warns when no valid witness results" | "validates it with pySHACL without inference against the extension's shapes, against the base alone and, when both hold, against both. It warns when the witness fails the extension, and fails at error level when it satisfies the extension but not the base, which also happens when the generator leaves a node the base constrains unfilled (Sect. 8)." | `check.py:195-276`, esp. `:206-224, 260-274`; probes p7, p17 |
| 13 | 04-pipeline.tex:83-85 (src) | `check.py:5-21, 111-177, 250-266, 254-255, 64-99`; `verify.py:536-549` | `check.py:3-21, 121-192, 279-305, 283-284, 74-109`; `verify.py:572-585` | as stated |
| 14 | 04-pipeline.tex:104-105 | "unmodified and hashed\verify{1.1 and 1.2 record only the zip file's hash}. The 98 tests pass" | "unmodified and hashed (for 1.1 and 1.2 the archive and the shape file in it); two shape files are repaired in memory when loaded, and one range file is kept but not loaded. The 170 tests pass without a model." Drop the \verify | `BP/dcat-ap-1.1/profile.yaml:11-17`; `BP/dcat-ap-1.2/profile.yaml:11-17`; `base_profile.py:106-115`; `BP/dcat-ap-3.0.1/profile.yaml:26-27`; `paper/inputs/tests-main-21c6b5b-2026-11-14.txt:5` |
| 15 | 08-discussion.tex:8 (comment) | "the owl:imports caveat (Sect. 4.3)" | the caveat is now: 1.2 named, not imported; resolution verify; the in-memory repairs do not travel (N5) | `shacl.py:33-39`; probe p5 |
| 16 | 08-discussion.tex:38 (src) | `retrieve.py:215-230` | holds (B16); `retrieve.py:217-232` | |
| 17 | 08-discussion.tex:39 (src) | tool-facts-main-5ffd56e.txt:2-3 | `tool-facts-main-21c6b5b.txt:2-3` (same numbers) | |
| 18 | 08-discussion.tex:77-78 | "it also warns on legal refinements and at its depth limit, so a warning is a lead, not a defect" | "it still warns on some legal refinements (a range narrowed to a subclass, a minimum above one for a literal, a value-list member without its class), and it now fails at error level when the generator leaves a node the base constrains unfilled (classes reached through an alternative, nodes at its depth limit), so neither a C7 warning nor a C7 error proves a defect." | `check.py:196-198, 206-224, 266-274`; probes p6, p7, p16, p17 |
| 19 | 08-discussion.tex:80 | "an incomparable range counts as tightened" | holds | `refinement.py:152-156, 217-218`; `check.py:136-150` |
| 20 | 08-discussion.tex:81-82 | "C1 compares obligations only where the base has a shape, and some obligations of the 1.2.1 to 2.1.1 bases are unknown" | "C1 also compares the obligations the specification states without a shape, but one to three obligations per base of the 1.2.1 to 2.1.1 bases remain unknown, where the official shapes name a property the specification does not list; there conformance can miss a loosening." | `check.py:125-136`; `paper/inputs/tool-facts-main-21c6b5b.txt:17-21`; probe p4 |
| 21 | 08-discussion.tex:83 | \todo{tool: align C1 with V3 (Q22)} | remove: done at 21c6b5b | `tests/test_dcat_state.py:270-283` |
| 22 | 08-discussion.tex:84 | "C8 is narrower than D1--D3" | holds | `check.py:74-109`; `verify.py:224-293` |
| 23 | 11-appendix.tex:107-110 (D1) | "a DCAT property without a declared domain on a class the base's DCAT does not list it for" | "... on a class the base's DCAT (for a later term: the DCAT that introduced it) does not list it for" | `verify.py:236-250, 264-283` |
| 24 | 11-appendix.tex:111-113 (D2) | "a term the base or the base's DCAT deprecates" | "a term the base deprecates on the class or a superclass, or the base's DCAT deprecates" | `verify.py:251-262`; `knowledge/__init__.py:83-94` |
| 25 | 11-appendix.tex:114 (D3 src) | `verify.py:274-280`; `dcat_state.py:81,198-200` | `verify.py:284-290`; `dcat_state.py:207-212`; 11 pairs unchanged | |
| 26 | 11-appendix.tex:140-142 (C1) | "a loosened facet or obligation, where the base has a shape" | "a loosened facet or obligation, also against an obligation the specification states without a shape" | `check.py:121-156` |
| 27 | 11-appendix.tex:143-145 (C2) | "crossing bounds, another datatype, disjoint node kinds or value lists" | add "a class range against a literal range" | `check.py:157-161`; `refinement.py:116,128,133,166,172,184,202` |
| 28 | 11-appendix.tex:146-157 (src) | C3 `:149-158`, C4 `:160-168`, C5 `:170-177`, C6 `:254-255`, `verify.py:536-549` | C3 `:163-172`, C4 `:174-182`, C5 `:184-191`, C6 `:283-284`, `verify.py:572-585` | |
| 29 | 11-appendix.tex:158-161 (C7) | "none, as its base-only branch cannot fire; warning: the witness fails base and extension ... or does not run" | "the witness satisfies the extension's shapes but not the base's (also when the generator leaves a node the base constrains unfilled); warning: the witness fails the extension's shapes, or the check does not run" | `check.py:260-276, 285-291` |
| 30 | 11-appendix.tex:162-164 (C8) | "warning: a later one" | holds; optional "(accepted by a person or allowed by the setting)" | `check.py:74-109`; `docs/conformance.md:51` |
| 31 | 12-appendix-cd.tex:118 (G3-S09) | "the delta does not import the base shapes" | "the delta imports the base shapes for eight of the nine bases; one release publishes them only in an archive, which the delta names" + verify (resolution). The star may go | `shacl.py:33-39` |
| 32 | 12-appendix-cd.tex:119 (G3-S10) | "C7's branch for data only the base rejects cannot fire" | "C7's branch for data only the base rejects now fires, also on gaps of the witness generator" | `check.py:260-274`; N1 |
| 33 | 06-setup.tex:75 | "C7 warnings by cause" | "C7 warnings and errors by cause" (C7 errors can now come from the generator) | N1 |
| 34 | 07-results.tex:87 | "\res{test}{FP}{c7warnings} C7 warnings" | consider a slot for C7 errors (or failures) | N1 |
| 35 | 10-statements.tex:5 | "(unmodified, with their licenses and hashes)" | holds for the files; optional "two shape files are repaired in memory when loaded" | `base_profile.py:106-115` |
| 36 | 05-benchmark.tex:11-13 (src) | "one of the nine the tool holds", src FACTS5:15-23 | holds; `tool-facts-main-21c6b5b.txt:15-23` | |
| 37 | README.md:73 | "... nine bases with class/element/obligation counts, 98 tests \| tool-facts-main-5ffd56e.txt" | "... 170 tests \| inputs/tool-facts-main-21c6b5b.txt; inputs/tests-main-21c6b5b-2026-11-14.txt" (2.x obligation rows now 19/29/61) | tool facts `:17-21`; tests `:5` |
| 38 | README.md:108 | open marker "04-pipeline.tex:105: 1.1 and 1.2 record only the zip file's hash" | resolved (see row 14) | `BP/dcat-ap-1.1/profile.yaml:14-15` |
| 39 | README.md:235 (Q3) | "At 5ffd56e the tool ships all nine DCAT-AP releases" | unchanged at 21c6b5b | `BP/*/profile.yaml` |
| 40 | README.md:351-370, 380-386, 395-401 | B/C/E rows | per section 4; add a "Fixed at 21c6b5b" list (B3, B4, B14, B15, B18, C6, C7, C8; B1, B5, B20 in part) and N1-N6 as new rows | section 4 |

---

## 6. Probes (scratchpad/probes-dcat)

p1 DAP pairs (both commits). p2/p3 per-base imports, fixes, hashes, compiled SHACL/DSV links. p4 unknown obligations,
unhandled constructs. p5 shape files pySHACL rejects; 206 pathless nodes in 3.0.1 ranges.ttl. p6/p7 conformance on
synthetic changes (C1, C2, C7, counts, delta), every base x 5 classes. p8 C2 gap. p9 B9, B12, B13. p10 rung-2 pool sizes.
p11 model re-extraction. p12 `dcat:hadRole` V2. p13 synthetic demo conformance. p14 `NEW:` rendering. p15 base-only
ranges. p16/p17 value lists, cycles, depth limit. p18 V2/V3 on range kinds. p19 DSV IRI collision.
