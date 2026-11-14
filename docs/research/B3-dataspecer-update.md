# B3. Dataspecer update: activity, DCAT/DCAT-AP as DSV, base-version change, publications

Research input for **requirement-based-dcat-profile-extensioner**. It extends [B1](B1-dataspecer.md) and does not repeat it. It answers six questions:

1. What the Dataspecer group did in 2026.
2. Which DCAT and DCAT-AP versions they publish as DSV, and whether we can reuse them.
3. How their DCAT 2 and DCAT 3 "Default Application Profiles" compare with our extracted `model.json`.
4. Whether refinement or conformance checking appeared since B1.
5. Which papers exist, verified against primary pages.
6. What to reuse, implement, or claim.

A dedicated section (5) answers the coordinator's extra question: **how Dataspecer handles a profile whose base or profiled vocabulary changes version** ("swap the base"). It also gives a migration-review spec for our tool.

Nothing in any Dataspecer repository was executed. Every statement comes from reading source, data or git history, or from scripts written for this study.

## 0. Sources, markers, headline findings

| Tag | Repository, local path | Commit read | How fetched | Content |
|---|---|---|---|---|
| `DS/` | dataspecer/dataspecer, `/home/user/refs/dataspecer__dataspecer` | `ece634b8c52539339e95d6815b85650787a35fc7` (2026-11-12), `main` | `git fetch` 2026-11-14. **`origin/main` is still `ece634b`.** The clone was shallow (1 commit); deepened with `--shallow-since=2025-12-01` to 972 commits. All 86 remote branches (`main` and 85 others) were fetched into `refs/remotes/origin/*`; the clone config was not changed. | Monorepo |
| `DS:<branch>` | same | branch tips as listed in 1.3 | same | Unmerged work |
| `SPEC/` | mff-uk/specifications, `/home/user/refs/mff-uk__specifications` | `833685ef1f5efc845e8901c4ac43e68e0a8b1c98` (2026-06-30), **unchanged since B1** | Unshallowed (91 commits). The full tree was listed with `git ls-tree -r` (no sparse filter). Files were read with `git show 833685e:<path>`. | 5 Dataspecer specifications |
| `DSV/` | mff-uk/data-specification-vocabulary, `/home/user/refs/mff-uk__data-specification-vocabulary` | `5c1d6555755f641179022aadb250e17474fc36a4` (2026-04-02), **unchanged since B1** | Unshallowed (124 commits) | DSV 1.0.1, DSV-DAP 1.0.1 |
| `SEMIC/` | SEMICeu/DCAT-AP, `/home/user/refs/SEMICeu__DCAT-AP` | `4470b8e` (2026-06-16) | already local | Official DCAT-AP 2.1.1 and 3.0.1 SHACL |
| `OURS/` | our repository | `2b92d77` plus the **uncommitted working tree** as read on 2026-11-14 (it changed while this study ran; line numbers can drift, so function names are given too) | local | `data/dcat/*`, `engine/rebase.py` (untracked), `knowledge/dcat_state.py` (untracked), and others |
| web | Search-index records of primary pages: dblp.org, link.springer.com, ceur-ws.org, journals.sagepub.com, ieeexplore.ieee.org, sciencedirect.com, dspace.cuni.cz | 2026-11-14 | WebSearch. **Direct fetches of dblp.org and link.springer.com are blocked by this session's network allow-list**, and the GitHub REST API returned 403 for these repositories, so PR and issue pages were not read. | Publications (section 6) |

Markers, as in B1: **(inferred)** = my conclusion, not stated by the source. **verify:** = not confirmed. Line numbers refer to the commits above.

Experiments are scripts of mine, run with rdflib 7.6.0 and Python 3.11 (`python -I`). They live in `/tmp/claude-0/-home-user-visual-profile-editor/b471f26b-782a-5ee3-bb4a-223b051d6027/scratchpad/rbdpe/research/artefacts/verify-b3/`. That is scratch space, so it may be cleared; every result they gave is reproduced in this report.

| Script | What it does |
|---|---|
| `jsonld_meta.py` | Reads the embedded JSON-LD of each `index.html`: titles, `isProfileOf`, resources |
| `dsv_summary.py` | Counts profiles; lists `dsv:profileOf` target namespaces; finds DCAT-3-only terms (via our `history.json`) |
| `dap_vs_model.py` | Compares a DAP DSV with our `model.json`: (class, property) pairs, ranges, subclasses. Outputs are in `cmp_dcat3.json` and `cmp_dcat2.json`. |
| `ap_vs_semic.py` | Resolves a DCAT-AP DSV through its DAP (effective cardinality = intersection along `dsv:profileOf`). Compares it with SEMIC's official SHACL. |
| `dsv_version_diff.py` | IRI-keyed diff of two DSV versions: the input of Dataspecer's evolution review |
| `direct_terms.py` | Terms a DSV profiles directly, outside its base |
| `bucket.py` | Groups commit subjects by keyword |

### 0.1 Ten findings

1. **No commits after B1 and no releases.** `dataspecer/main` still ends at `ece634b`. The specifications and DSV repositories have not changed since June and April 2026. There were 967 commits on `main` in 2026 (to 2026-11-12) and no tags or releases. Most of the year went into two things: **change propagation ("evolution")**, merged 2026-08-10 and improved until 2026-11-11, and **controlled vocabularies** (section 1).
2. **"Swap the base" exists, and it is the B1 "history / change propagation" feature, triggered by *Reload*.** In the manager the user reloads an imported specification or vocabulary and **edits its URL**, for example `dcat2.ttl` to `dcat3.ttl`, or `dcat2-dap/` to `dcat-dap/`. The backend diffs old against new and records the operations on a pending **evolution branch**. The history app turns them into typed review items for every dependent profile. Severities are `automatic`, `decision` and `attention`; each item has preselected choices. The user then accepts the upstream update wholesale together with the selected reactions. This is exactly the ISWC 2026 demo scenario (DCAT 2 to DCAT 3; DCAT-AP 2.1.1 to "3.0.1") (`DS/www/content/en/papers/iswc2026.md:25-43,66-72,119-127`; section 5).
3. **The propagation is keyed by entity IRI and ignores four kinds of change.** It ignores requirement levels and class roles (tags are not inherited and have no decision kind). It ignores datatype-range changes, `owl:deprecated`, and renames (a rename shows as delete plus create). It also never checks that a kept override is still a legal refinement (5.3).
4. **mff-uk/specifications publishes five specifications** (2.1):
   - DCAT 2 DAP (`dcat2-dap/`);
   - DCAT 3 DAP (`dcat-dap/`);
   - DCAT-AP 2.1.1 (`dcat-ap2/`);
   - DCAT-AP 3.0.1 (`dcat-ap/`);
   - DCAT-AP HVD 3.0.0 (`dcat-ap-hvd/`).

   Nothing is published for DCAT 2014, DCAT-AP 1.x, 2.0.x, 2.1.0, or 3.0.0 as such. The two 2.x files are, in the repository's own words, demonstration files "created by 'downgrading'" the 3.x ones (`SPEC/README.md:21-22`).
5. **Versions share IRIs.** DCAT 2 DAP and DCAT 3 DAP are both `https://mff-uk.github.io/specifications/dcat-dap#`. DCAT-AP 2.1.1 and 3.0.1 are both `https://mff-uk.github.io/specifications/dcat-ap#` (`SPEC/*/dsv.ttl:15`). The DCAT version a DCAT-AP release builds on is encoded only in the HTML JSON-LD (`isProfileOf` URL of the DAP page, which names `dcat2.ttl` or `dcat3.ttl`) and in the title. It is not in `dsv.ttl`. **A `dsv:profileOf` IRI therefore does not identify the base version.** Our compiler must also emit the base specification URL (7, B2).
6. **`dcat-ap2` (2.1.1) is usable only with a deviation list.** Against SEMIC's 2.1.1 SHACL (the same file our 2.1.1 base vendors, sha256 `467ace…`):
   - 106 of 109 (class, property) pairs match;
   - 7 cardinalities differ;
   - `dct:hasVersion` and `owl:versionInfo` on Dataset are missing;
   - `Dataset.publisher` is mandatory instead of recommended.

   The control, `dcat-ap` (3.0.1) against SEMIC 3.0.1, matches 131 of 131 pairs with only 2 cardinality differences (2.3).
7. **The DAPs are a good oracle for our DCAT models.** DCAT 3 DAP contains all 88 of our (class, property) pairs plus one extra. DCAT 2 DAP contains 73 of our 75. The cross-check found **two defects on our side**:
   - `dcat:DataService` loses its `dcat:Resource` superclass because repeated table rows overwrite each other (`OURS/scripts/build_dcat_versions.py`, `extract_model`, `fields = {label: value ...}`);
   - "rdfs:Literal typed as xsd:X" ranges are kept as two ranges.

   It also found **five defects on their side**, for example `prov:wasGeneratedBy` ranging over `prov:Entity`, and DCAT 2 DAP carrying DCAT 3 ranges (section 3).
8. **No refinement, conformance or `dsv:InvalidTermProfile` work** appeared on `main` or on any of the other 85 branches. The evolution review even defaults to "keep own value" for a cardinality override that the new base may have made illegal (section 4).
9. **LLM work exists only outside the product.** There is an ER 2024 paper with an LLM domain-modelling assistant (verified), and a 2026 master thesis on LLM-based "automated data specification adjustment in Dataspecer" with RAG and MCP (verified). The repository has no LLM code, apart from an unmerged branch that links to an external "slovniky-AI" assistant (1.3, 6).
10. **Our working tree already has a rebase** (`OURS/backend/profile_extensioner/engine/rebase.py`, `Pipeline.rebase`). It detects more than Dataspecer: requirement levels, DCAT deprecation and term status, minted-to-reusable, and lost coverage claims. It is less staged than Dataspecer's: the base switches at once, there are no per-item choices with ready edits, no dependencies, no batch apply and no cancel. Section 5.9 specifies the gap.

## 1. Recent activity (Q1)

### 1.1 dataspecer/dataspecer `main`, 2026-01-01 to 2026-11-12

| Measure | Value | Evidence |
|---|---|---|
| Commits (committer date) | 967. By month: Jan 151, Feb 49, Mar 51, Apr 51, May 70, Jun 91, Jul 138, Aug 61, Sep 137, Oct 142, Nov 26 | `git log --since=2026-01-01 origin/main` |
| Authors | Štěpán Stenchlák 400, Evgenia Blajer 269, Petr Škoda 182, `copilot-swe-agent[bot]` 89, Jakub Klímek 27 | same |
| Merges | 88 merge commits. 24 are "Merge pull request" merges; the PR numbers run from #1388 to #1584. The rest are direct branch merges. | `git log --merges` |
| Releases and tags | None in 2026. The only tag is `jan-janda-project` (2023-03-11). Deployment is by Docker image per branch, e.g. `ghcr.io/dataspecer/ws:branch-iswc2026` (`DS/www/content/en/papers/iswc2026.md:16-20`). | `git ls-remote --tags` |
| PR and issue pages | Not readable: the GitHub API answered 403 in this session. PR numbers and titles come from merge commits. | |

Keyword buckets of the 967 subjects (rough, `bucket.py`):
- controlled vocabularies 123;
- evolution, history and reload 117;
- infrastructure 82;
- CME and diagram 71;
- DSV and profiles 58;
- operations and LDES 47;
- structures 30;
- documentation 29;
- SHACL 16;
- other 389.

### 1.2 Features added on `main` in 2026

| Area | What | When, evidence |
|---|---|---|
| **Change propagation ("evolution")** | History app, model diff, evolution branches, review screen | First steps: "Basic model diff" 2026-06-24 `6e0f27ec2`; "Proof of concept history app" `9cc843eba`; "Evolution proof of concept" 2026-06-29 `fb9ef95b9`. **Merge of branch `evolution` 2026-08-10 `8a0a42ad7`** (97 commits, 392 files). Follow-ups in the `dia` merge 2026-10-12 `c9e123cb2` (24 commits): "Reload of cached models", "Evolution related functionality improvement". Later: "Reload RDFS model" 2026-10-30 `d56bea623`; "Allow reload of cached vocabularies" 2026-11-02 `aacc1cca0`; "Reload now creates and removes models" 2026-11-11 `1c239399f`; "Fix diff" 2026-11-11 `c8635c84d`. Section 5. |
| Controlled vocabularies | CV model; CV manager UI (multilingual titles); CV assignments with qualifiers; CV SHACL ("emit shacl rdf with pattern & severity" 2026-09-23 `70b660d35`); CV documentation; CVs in the structure editor; the CV catalogue embedded in `dsv.ttl` ("embed the catalog into dsv.ttl" 2026-09-23 `1e9e38564`) | PRs #1522 (2026-07-04), #1542 (08-18), #1555 (10-03), #1556 (10-04), #1560 (10-07), #1576 (10-23), mostly Evgenia Blajer. B1 3.3 noted that the CV DSV terms are unpublished placeholders; that still holds. |
| DSV | `dsv:reusedAsProperty` support (PR #1461, 2026-03-17); "Application profile type" and "Fix default cardinality to undefined" (2026-10-12); `profileSpecializationAsSubClassOf` in the UI (PR #1584, 2026-10-29); DSV import tests (2026-09-02 `6bd1746df`) | B1 covers the resulting behaviour at `ece634b` |
| Operations and versioning | Edits as operations (undo and redo via operations, `CreateProjectOperation`); "Use operations for import" 2026-08-06 `f52804518`; "Ldes make IRIs more deterministic" 2026-09-09 `e5c7bbd8d`; "Add low level ops to model store" 2026-11-11 `506f26ae3`. History routes: `/transactions/apply`, `/transactions/branches`, `/transactions/branches/:branchId`, `/transactions/log/:range` (`DS/services/backend/src/main.ts:109-112`). | |
| Infrastructure | Prisma replaced by Kysely with own migrations (2026-09-09 `968496e50`); multi-platform Docker (PR #1460); PIM layer removed (PR #1582, 2026-10-30, 149 files); Bun upgrade (2026-11-11) | |
| CME and documentation | catalog-v3 (2026-03-23); colours and a generalization dialog (2026-10-08); automatic layout when a specification has no diagram (2026-11-05 `6f2671e84`); regexes and examples in documentation, customizable default configuration (2026-11-04); diff in the template editor (2026-09-30) | |
| Geo | WKT and GML in XSD and XSLT, Simple Features datatypes (merge `dev/geo` 2026-05-12 `a4cddef90`) | |
| Czech OFN vocabularies | Import of OFN vocabularies by IRI list | `DS/services/backend/src/routes/import.ts:701-720` |
| AI-assisted *development* | 89 commits by the GitHub Copilot coding agent; `.github/copilot-instructions.md` (PR #1393, 2026-01-21). This is a working practice, not a product feature. | |
| AI and LLM *product features* | **None on `main`.** A whole-word search of all `.ts` and `.tsx` files on `main` for `llm`, `openai`, `anthropic`, `ollama`, `gpt-4` and "large language model" gave no hits. A search of all 86 branches for MCP server code (`modelcontextprotocol`, `McpServer`) gave none either. | 1.3 |

### 1.3 Branches not merged into `main` (tips)

| Branch | Tip | What it adds | Relevance |
|---|---|---|---|
| `feature/project-AI-vocabularies-connection` | 2026-10-16 `c528de33a` (2 commits, Pavol Rajczy) | A header button "AI · Domain map" that links to an external app `VITE_SLOVNIKY_AI` (`/domain-areas?package-iri=…`), and a new model type `KNOWLEDGE_BASE` ("Knowledge base for the vocabulary") created by the vocabulary wizard (`applications/conceptual-model-editor/src/header/domain-map-link.tsx`, `packages/core-v2/src/model/known-models.ts`) | The only AI hook. The assistant lives outside the repository. verify: whether that app is public. |
| `git-integration` | 2026-07-26 `3d88ba890` (962 unique commits, RadStr) | GitHub and GitLab providers: create repo, commit, pull. Merge states with a diff editor for conflict resolution; publication through a GitHub Action; issue labels; SSH keys; OAuth. Packages `packages/git`, `packages/git-node` (READMEs on the branch). | Collaboration and versioning, not on `main` |
| `add-authentication-via-authJS` | 2025-08-26 | Authentication | Not on `main`; `main` still registers no authentication middleware (B1 0.2) |
| `app-generator` | 2026-09-18 | Application generator with user and technical documentation | Not relevant |
| `controlled-vocabularies*` (9 branches) | 2026-09-23 to 2026-11-11 | Continuing CV work | |
| `dev/model-store`, `feature/api-v3-proposal`, `sstenchlak/dev`, `iswc2026` | 2026-05 to 2026-11 | Model-store auto-save; API v3 proposal; URL fixes. `iswc2026` (tip 2026-07-26) has no commits of its own; it is fully contained in `main`. | |

### 1.4 mff-uk/specifications and DSV in 2026

- `SPEC/`, 2026:
  - 2026-01-09: DCAT-DAP and DCAT-AP template, DSV and SHACL updates; **"Add DCAT-AP-HVD"** `667ddb3`.
  - 2026-03-30: "Update … DSV (prop reuse)" ×4.
  - 2026-04-02: DCAT-DAP and HVD fixes.
  - 2026-06-22: ELI hotfix, referencing dataspecer issue 1504.
  - **2026-06-29: "Add DCAT2-DAP"** `7fbb328`.
  - 2026-06-30: "DCAT2-DAP: Fix invalid IRI" `d1beabf`, and **"Add DCAT-AP 2.1.1"** `833685e`.

  All commits are by Jakub Klímek.
- `DSV/`, 2026: 2026-01-09 "DSV 1.0.1" `145710a`, "DSV-DAP 1.0.1" `37f4782`, and "Add DSV and DSV-DAP 1.0.0 version explicitly" `f6b1d0c`; 2026-04-02 template and DSV updates. Nothing since. Licence CC BY 4.0 (`DSV/LICENSE:1`). `DSV/CITATION.cff` names Klímek, Stenchlák and Škoda, version 1.0.0, released 2025-05-13.

### 1.5 Changed since `ece634b`

**Nothing on `main`.** `origin/main == ece634b` after the fetch on 2026-11-14. All B1 statements about `main` stand. New since B1 are only facts that B1 did not study:
- the full branch landscape (1.3);
- the depth of the evolution feature (section 5);
- the two 2.x demonstration specifications, which were already in `SPEC/` at `833685e` but outside B1's sparse checkout (section 2).

## 2. DCAT and DCAT-AP published as DSV (Q2)

### 2.1 Full tree listing of `SPEC/` at `833685e`

`git ls-tree -r origin/main` lists `LICENSE`, `README.md`, `assets/images/ds-import.gif` and five directories. Each directory holds:
- `dsv.ttl`;
- `shacl.ttl`;
- `index.html` (ReSpec with embedded JSON-LD);
- `generator-configuration.ttl`;
- one or two SVG diagrams;
- `export.zip` or `dataspecer.zip` (the complete Dataspecer project).

| Path | Title (`index.html:7`) | Application profile IRI (`dsv.ttl:15`) | Class / property profiles | Dates (first, last commit) | What it profiles | DCAT version encoded? |
|---|---|---|---|---|---|---|
| `dcat2-dap/` | DCAT 2 Default Application Profile | `https://mff-uk.github.io/specifications/dcat-dap#` | 31 / 74 | 2026-06-29 `7fbb328`, 2026-06-30 `d1beabf`. ReSpec `publishDate: "2025-09-29"` (`index.html:307`) looks like a template value (inferred). | Vocabularies directly: 31 `dsv:class`, 74 `dsv:property`, no `dsv:profileOf`. The DCAT document is `https://www.w3.org/ns/dcat2.ttl` (`index.html:133`). Uses 20 DCAT-2-introduced terms and **no** DCAT-3-only term. | Only in the HTML (`isProfileOf` → `dcat2.ttl`) and the title. "created by 'downgrading' DCAT 3 DAP", "mainly for demonstration of change propagation" (`README.md:21`). |
| `dcat-dap/` | DCAT 3 Default Application Profile | **same IRI** `…/dcat-dap#` | 34 / 89 | 2025-02-27 `d59e070`, 2026-04-02 `dcc9d9f` | Vocabularies directly. The DCAT document is `https://www.w3.org/ns/dcat3.ttl` (`index.html:125`). Uses 10 DCAT-3-only terms: `DatasetSeries`, `inSeries`, `resource`, `version`, `hasVersion`, `hasCurrentVersion`, `previousVersion`, `first`, `last`, `prev`. | HTML and title only |
| `dcat-ap2/` | DCAT-AP 2.1.1 based on DCAT 2 DAP | `https://mff-uk.github.io/specifications/dcat-ap#` | 31 / 107 | 2026-06-30 `833685e` | 107 `dsv:profileOf` to `…/dcat-dap#…`. The `isProfileOf` entry has `@id …/dcat-dap#` and artefact `https://mff-uk.github.io/specifications/dcat2-dap/` (`index.html:22,44`). 24 direct properties and 7 direct classes, all non-DCAT (DCTERMS, ADMS, SPDX, SKOS, FOAF, r5r). **So the chain reaches DCAT 2 terms**, but only through the document that is loaded. | HTML and title only. "created by 'downgrading' DCAT-AP 3.0.1" (`README.md:22`). |
| `dcat-ap/` | DCAT-AP 3.0.1 based on DCAT 3 DAP | **same IRI** `…/dcat-ap#` | 34 / 131 | 2025-02-28 `fa2b026`, 2026-06-22 `1468b52` | 133 `dsv:profileOf` to `…/dcat-dap#…`, artefact `https://mff-uk.github.io/specifications/dcat-dap/` (`index.html:52`): **DCAT 3 terms**. Direct terms are non-DCAT (adds ELI, `LegalResource`). | HTML and title only |
| `dcat-ap-hvd/` | DCAT-AP HVD 3.0.0 | `https://mff-uk.github.io/specifications/dcat-ap-hvd#` | 15 / 29 | 2026-01-09 `667ddb3`, 2026-04-02 `ef00c1f` | 38 `dsv:profileOf` to `…/dcat-ap#`. One goes straight to the DAP (`:LicenseDocument dsv:profileOf <…/dcat-dap#LicenseDocument>`, `dsv.ttl:197`). Artefact `…/dcat-ap/` (`index.html:43`). | Through the chain |

Not published: DCAT 2014 (no DAP), DCAT-AP 1.1, 1.2, 1.2.1, 2.0.0, 2.0.1 and 2.1.0, DCAT-AP 3.0.0 as such, and GeoDCAT-AP. DCAT-AP-CZ moved to ofn.gov.cz ("Move DCAT-AP-CZ related specs to ofn.gov.cz", 2025-05-08 `f1c6943`).

The DAPs declare cardinality 0..n on every property profile except `CatalogRecord.primaryTopic` (0..1). They declare no requirement levels: DCAT has no obligations.

Licence: the repository is MIT, "Copyright (c) 2025 mff-uk" (`SPEC/LICENSE:1-3`). The content is derived from SEMIC DCAT-AP (CC BY 4.0, as our `profile.yaml` files record) and from W3C DCAT. Attribute all three when vendoring (inferred).

### 2.2 How versions are told apart

- **IRIs are shared on purpose (inferred from the importer).** On a reload, Dataspecer pairs the old and new profiled specification by URL or by profile IRI (`DS/services/backend/src/routes/import.ts:572-573`). It pairs raw vocabularies by their dominant namespace (`import.ts:584-617`; `getDominantBaseIri` at `:126`). Keeping `…/dcat-ap#Dataset.contactPoint` identical across 2.1.1 and 3.0.1 is what lets the evolution review show "modified" instead of "deleted and created" (section 5).
- **Consequence for a consumer:** the version is the document, not the IRI. Two extensions, one of 2.1.1 and one of 3.0.1, would carry identical `dsv:profileOf` triples. Only the `isProfileOf` resource URL in the specification metadata (`…/dcat-ap2/` versus `…/dcat-ap/`) tells them apart. Our compiler writes only `prof:isProfileOf <https://mff-uk.github.io/specifications/dcat-ap#>` (`OURS/backend/profile_extensioner/compile/linkml_dsv.py:131`, `compile_dsv`). That would be ambiguous as soon as a 2.1.1 index exists.

### 2.3 Fidelity of the DCAT-AP DSVs against SEMIC (`ap_vs_semic.py`)

Method: resolve each DCAT-AP property profile to (RDF class, RDF property) through `dsv:profileOf`, `dsv:class` and `dsv:property`, with the DAP loaded. The effective cardinality is the intersection along the chain. Compare with `sh:minCount` and `sh:maxCount` per (`sh:targetClass`, `sh:path`) in SEMIC's shapes.

| DSV | SEMIC reference | Pairs DSV / SHACL / shared | Cardinality differences | Other |
|---|---|---|---|---|
| `dcat-ap2` (2.1.1) | `SEMIC/releases/2.1.1/dcat-ap_2.1.1_shacl_shapes.ttl` (identical to `OURS/data/base-profiles/dcat-ap-2.1.1/shacl/…`, sha256 `467ace00…`) | 107 / 109 / 106 | **7** (DSV vs SEMIC):<br>`adms:Identifier skos:notation` 1..1 vs 0..1<br>`Catalog dct:creator` 0..1 vs 0..n<br>`Catalog dct:rights` 0..n vs 0..1<br>`CatalogRecord dct:conformsTo` 0..n vs 0..1<br>`Dataset dcat:spatialResolutionInMeters` 0..n vs 0..1<br>`Dataset dcat:temporalResolution` 0..n vs 0..1<br>`Distribution dct:rights` 0..n vs 0..1 | **Missing in DSV:** `Dataset dct:hasVersion`, `Dataset owl:versionInfo`.<br>"Extra" `Dataset dct:isReferencedBy`: SEMIC's file has the typo `dc:isReferencedBy` (elements/1.1), so DSV is right.<br>Requirement levels against `…_shacl_shapes_recommended.ttl`: 28 of 29 match. `Dataset dct:publisher` is **mandatory** in `dcat-ap2/dsv.ttl:1140-1154` but recommended in SEMIC 2.1.1 and in `dcat-ap/dsv.ttl:1408` (3.0.1). `Catalog dcat:dataset` is recommended in the DSV and absent from SEMIC's recommended shapes, while our 2.1.1 `obligations.yaml` (from the specification text) says mandatory. |
| `dcat-ap` (3.0.1), control | `SEMIC/releases/3.0.1/shacl/dcat-ap-SHACL.ttl` | 131 / 131 / 131 | 2: `Dataset dcat:temporalResolution` 0..n vs 0..1; `DatasetSeries dct:description` 0..n vs 1..n (mandatory in the DSV, but no lower bound) | |

Reading: the 3.0.1 file is faithful. Most deviations of the 2.1.1 file are 3.0.1 values left in place by the "downgrade":
- `Catalog dct:rights` is 0..n in both DSVs, and SEMIC 3.0.1 agrees;
- the downgrade removed DCAT 3's version properties (`dcat:version`, `dcat:hasVersion`) but did not restore 2.1.1's `owl:versionInfo` and `dct:hasVersion`.

### 2.4 Can we use their DSV as `dsv:profileOf` target for our historical bases?

| Our base (`OURS/data/base-profiles/*/profile.yaml`, `dcat_basis`) | DSV in `SPEC/` | Verdict |
|---|---|---|
| DCAT-AP 1.1, 1.2, 1.2.1 (DCAT 2014) | none | **No.** Keep the vocabulary fallback: `dsv:class` and `dsv:property` (`compile/linkml_dsv.py:146-148,171-173`). |
| 2.0.0 (DCAT 2 CR), 2.0.1 and 2.1.0 (DCAT 2 REC) | none | **No.** Same fallback. Pointing 2.1.0 at the 2.1.1 file would hide release differences (inferred). |
| **2.1.1** (DCAT 2 REC) | `dcat-ap2/` (demo downgrade) | **Conditionally yes.** Conditions:<br>(1) vendor `dsv.ttl` at `833685e` and record the commit, because nothing is tagged and the IRIs are reused by 3.0.1;<br>(2) build an index only for the 106 pairs that agree with our base;<br>(3) for each of the 7 cardinality deviations and the publisher level, our own declared value prevails, and the deviation is listed in the index (`known_deviations`) so Verify does not judge legality against the DSV value;<br>(4) fall back to `dsv:property` for `dct:hasVersion` and `owl:versionInfo`;<br>(5) emit the specification URL `https://mff-uk.github.io/specifications/dcat-ap2/` (2.2). |
| 3.0.0 (DCAT 3 PR) | none (`dcat-ap/` is 3.0.1) | **No.** mff-uk's HVD 3.0.0 points at their 3.0.1 DSV, which suits Dataspecer but not a strict 3.0.0 base (inferred). |
| 3.0.1 (DCAT 3 REC) | `dcat-ap/` | **Yes** (as now). The control shows 131 of 131 pairs. |
| Any base: a DCAT term not profiled by the DCAT-AP DSV | `dcat-dap/` or `dcat2-dap/` | **Yes, as a second-level fallback.** Point `dsv:profileOf` at the DAP property profile instead of `dsv:property`, as HVD does for `LicenseDocument` (`SPEC/dcat-ap-hvd/dsv.ttl:197`). This keeps DCAT's own label and definition as the reuse source. |

### 2.5 Can we use them to cross-check our DCAT models?

Yes, as a regression oracle with an allowlist, not as ground truth. Both DAPs contain errors and modelling simplifications (section 3). They are still the only machine-readable "DCAT text as a profile" that exists. W3C `dx-dcat` issue 498, "Add machine-processable representation of DCAT", proposes exactly this kind of DSV-in-JSON-LD for DCAT and uses DCAT 3 DAP as its example. That comes from a search-index snippet, about 52 days old on 2026-11-14 (so around late September 2026). verify: the author and the status of the issue. If W3C adopts it, a W3C-hosted DSV of DCAT would become the natural `dsv:profileOf` target at the DCAT level.

## 3. Cross-check with our `model.json` (Q3)

Script `dap_vs_model.py`. Pairs are (RDF class of `dsv:domain`, `dsv:property`). DSV ranges are resolved to the RDF class of the range class profile, or to the datatype.

### 3.1 DCAT 3: `OURS/data/dcat/dcat-3/model.json` vs `SPEC/dcat-dap/dsv.ttl`

Ours has 88 pairs over 14 classes; the DAP has 89 pairs; **88 are shared**. All 14 of our classes have DAP class profiles; the DAP adds 20 supportive range classes.

| Difference | Instances | Who is right |
|---|---|---|
| Pair only in DAP: (`prov:Attribution`, `dcat:hadRole`) | 1 | Both. DCAT 3 lists "had role" under Relationship (§6.13.2) with domain "prov:Attribution or dcat:Relationship". Our entry keeps that domain but attaches the property to Relationship only. Optional for us: add the pair from `domain`. |
| G1 date literals: ours `[rdfs:Literal, xsd:date, xsd:dateTime, xsd:gYear, xsd:gYearMonth]`, DAP `rdfs:Literal` | 7: `dct:issued` and `dct:modified` on CatalogRecord, Distribution and Resource; `dcat:startDate` | Neither is wrong. Ours is more precise; DSV allows one datatype per profile. |
| G2 "rdfs:Literal typed as X": ours `[rdfs:Literal, X]`, DAP `X` | 3: Dataset `dcat:spatialResolutionInMeters` (xsd:decimal), Dataset `dcat:temporalResolution` (xsd:duration), Distribution `dcat:byteSize` (xsd:nonNegativeInteger) | **The DAP is right.** Our extractor should record `X`, keeping `range_text`. |
| G3 Distribution `dcat:spatialResolutionInMeters`: ours `xsd:decimal, xsd:double`, DAP `rdfs:Literal` (`dcat-dap/dsv.ttl:1813-1824`) | 1 | **Ours is right.** The spec says "xsd:decimal or xsd:double". |
| G4 Dataset `prov:wasGeneratedBy`: ours `prov:Activity`, DAP the class profile of `prov:Entity` (`dcat-dap/dsv.ttl:1201-1211`) | 1 | **Ours is right.** DCAT-AP 3.0.1 corrects it to `:Activity` in its own profile. DCAT 2 DAP has the same error (`dcat2-dap/dsv.ttl:952-962`). |
| G5 no Range row in the DCAT 3 text: ours empty, DAP fills a range | 14:<br>CatalogRecord `foaf:primaryTopic` (DAP `dcat:Resource`);<br>Relationship `dct:relation` (`dcat:Resource`);<br>Resource `dct:publisher` (`foaf:Agent`, from the usage note);<br>Resource `dcat:theme`, `dct:relation`, `dct:hasPart`, `dct:isReferencedBy`, `dct:replaces`, `dcat:first`, `last`, `prev`, `previousVersion`, `hasVersion`, `hasCurrentVersion` (all `rdfs:Resource`) | Ours is faithful to the text (rows checked in `OURS/data/dcat/dcat-3/spec.html`). `dcat3.ttl` also has no `rdfs:range` for `dcat:theme` (`OURS/data/dcat/dcat-3/dcat.ttl:1722-1764`). DSV needs a range on every property profile (B1 rule R4), which is why the DAP fills one in. |
| Superclasses: `dcat:DataService` ours `[dctype:Service]`, DAP `specializes` CatalogedResource (= `dcat:Resource`) | 1 | **Ours is defective.** The spec lists "Sub-class of: dcat:Resource" and "Sub-class of: dctype:Service". `extract_model` builds `fields = {label: value for label, value in rows[1:]}`, so a repeated row label keeps only the last value. The same bug drops the first of DataService's two "Usage note" rows. Dataspecer cannot express `dctype:Service` (generalisations only between profiles of one AP); likewise `dcat:Relationship` → `prov:EntityInfluence`. |

### 3.2 DCAT 2: `OURS/data/dcat/dcat-2/model.json` vs `SPEC/dcat2-dap/dsv.ttl`

Ours has 75 pairs over 12 classes, the DAP 74; **73 are shared**. All 12 of our classes have DAP class profiles (31 in total).

| Difference | Who is right |
|---|---|
| Only in ours: (`dcat:DataService`, `dct:license`) and (`dcat:DataService`, `dct:accessRights`). The DCAT 2 text lists both under Data Service with service-specific definitions, e.g. "A legal document under which the service is made available." (`OURS/data/dcat/dcat-2/spec.html:2365,2377`). | **Ours.** The DAP lost them in the downgrade (DCAT 3 moved them to Resource). |
| Only in DAP: (`prov:Attribution`, `dcat:hadRole`) | as in 3.1 |
| G1 date literals: 7; G2 `dcat:byteSize` ("rdfs:Literal typed as xsd:decimal"): 1; G4 `prov:wasGeneratedBy`: 1; G5 no range: 5 (`foaf:primaryTopic`, `dct:relation` twice, `dct:publisher`, `dct:isReferencedBy`) | as in 3.1 |
| Distribution `dcat:spatialResolutionInMeters`: spec `xsd:decimal`, DAP `rdfs:Literal` | **Ours** |
| Resource `dcat:theme`: DCAT 2 text "Range: skos:Concept" (`dcat-2/spec.html:1172`), DAP `rdfs:Resource` (`dcat2-dap/dsv.ttl:719-734`) | **Ours.** The DAP carries the DCAT 3 form. |
| Location `locn:geometry`: DCAT 2 text "Range: rdfs:Literal" (`dcat-2/spec.html:2738`), DAP the class profile of `locn:Geometry` (`dcat2-dap/dsv.ttl:1272-1288`) | **Ours.** DCAT 3 form again. |
| DataService superclass | Same defect on our side as in DCAT 3 |

### 3.3 What to do

- **Fix ours** (B1 in section 7):
  1. collect repeated rows as lists in `extract_model`, for "sub-class of", "usage note" and others;
  2. map "rdfs:Literal typed as X" to `X`;
  3. optionally add pairs from a `domain` cell that names classes outside the current section, such as `prov:Attribution`.

  Then regenerate `model.json` and `versions.yaml` with `scripts/build_dcat_versions.py`.
- **Test** (A1 in section 7): a test that loads both DAP DSVs, pinned at `833685e`, and asserts that every (class, property) pair of ours is present, apart from the allowlisted DCAT 2 DataService pairs. The known range groups G1 to G5 and the two DCAT 2 downgrade items are listed with reasons.
- **Report upstream (optional):** G3, G4, the two DCAT 2 downgrade items and the two missing DataService properties are small, concrete issues for `mff-uk/specifications`.

## 4. Refinement, conformance and validation since B1 (Q4)

| Question | Answer | Evidence |
|---|---|---|
| New refinement check on `main`? | No: `main` is the B1 commit | 1.5 |
| On any branch? | No. All 86 remote branches were searched for `InvalidTermProfile`, `stricter`, `refinement`, `breaking change`, `loosen` and "narrow… cardinal". On `main` the only hits are the unused translation texts and the `dsv-model.ts` interface B1 already reported. Older branches (2024 to early 2025) carry `profile-modification-warning.tsx`, a static red text "Changing … can introduce a breaking change in the profile." with no check (`DS:stable-dia` `8ed0c77e8`); `main` no longer has it. | `git grep` over `refs/remotes/origin/*` |
| `dsv:InvalidTermProfile` produced? | No | as B1 section 5 |
| Does the evolution review check legality? | **No.** For a cardinality the profile overrides, a changed upstream value gives `override-differs` with choices `keep-own` (**default**) and `adopt-new`. Nothing tests whether the kept value is still inside the new upstream bound (`DS/packages/profile-model/src/hooks/evolution-items.ts:685-734`). The aggregated view then silently intersects (B1 1.2.5), while the DSV export writes the declared looser value (B1 1.2.5 table). | 5.3 |
| Requirement levels? | Still not constraints. They are not inherited either: the aggregators copy the profile's own `tags` (`DS/packages/core-v2/src/semantic-model/profile/aggregator/semantic-relationship-profile-aggregator.ts:156`, `semantic-class-profile-aggregator.ts:144`). | |
| SHACL lower bounds on chains | Unchanged (B1 4.4) | |
| What the SWJ 2026 paper calls "consistent" | verify: the full text was not accessible. The abstract and the reviewer remarks indexed by the journal mention "12 requirements for a tool supporting SDS ecosystems" and "explicit handling of reuse and contextual refinement". The code shows consistency through propagation, not through validation (inferred). | section 6 |

Conclusion: the refinement and conformance gap described in B1 section 5 is still open and still ours to fill. Section 5.8 shows a second instance of it, inside Dataspecer's own evolution.

## 5. Changing the base or vocabulary version in Dataspecer ("swap the base")

The coordinator relayed the user's understanding: "you can swap the base if the DCAT/DCAT-AP version changes". **Correct.** Below are the mechanics, what it detects, what it proposes, what the human decides, and what it keeps. A spec for our tool follows.

### 5.1 Short answer

| Question | Answer | Evidence |
|---|---|---|
| Same as B1 1.2.11? | **Yes.** It is the history application's "evolution" review ("History and change propagation" in the manager). The entry point is **Reload**, i.e. *update source*: the user points an imported specification or vocabulary at a new URL. It is not "re-profiling": "Profile dataspec from URL" and "Autoprofile" create a new profile from scratch (B1 1.1). Dataspecer has no "rebase" term. In code the terms are "evolution branch", "pending evolution", `analyzeEvolution`, `analyzeProfileEvolution`. The ISWC 2026 demo calls it "Change Propagation in Application Profile Hierarchies". | `DS/applications/manager/locales/en/default.json:77-78,115-129`; `DS/www/content/en/papers/iswc2026.md:1-8` |
| Used for DCAT and DCAT-AP version changes? | **Yes, and it is the showcase.**<br>Part I: DCAT2-DAP is imported, its `dcat2` vocabulary is reloaded with URL `https://www.w3.org/ns/dcat3.ttl`, and the changes are reviewed and applied: "DCAT3-DAP".<br>Part II: DCAT-AP 2.1.1 (`…/dcat-ap2/`) is imported, its profiled DCAT2-DAP is reloaded with URL `…/dcat-dap/` (DCAT3-DAP), reviewed, and renamed "DCAT-AP 3.0.1 based on DCAT 3 DAP". | `iswc2026.md:25-43,54-72,104-133` |
| Caveat | Part II propagates *DCAT-level* changes into the 2.1.1 profile. It cannot reproduce SEMIC's own 2.1.1 → 3.0.1 changes, e.g. `applicableLegislation`, the DataService properties, or Category → Concept: 33 profiles were added and 6 removed between `dcat-ap2` and `dcat-ap` (5.7). The rename at `iswc2026.md:133` is a label, not the real 3.0.1 (inferred). For *our* case, where the base itself is replaced by the next DCAT-AP release, the matching Dataspecer scenario is a profile-to-profile edge: an HVD-like profile whose profiled DCAT-AP package is reloaded from a newer URL. | 5.7 |

### 5.2 How it is triggered

1. In the manager, a package row shows a reload icon in two cases. Either the package was imported from a URL (`LOCAL_PACKAGE` with `importedFromUrl`, `DS/applications/manager/src/Dir.tsx:140-153`). Or the row is a vocabulary model sourced from one or more URLs ("RDFS snapshot") or a cached subgraph (`Dir.tsx:155-168`). Tooltip: "Reload data specification".
2. The dialog shows the warning "…its content will be completely overwritten" and a **URL field prefilled with the original URL, which the user can edit**, or one URL per line for multi-URL vocabularies (`DS/applications/manager/src/dialog/reload-resource.tsx:105-115`). There are two actions: **"Reload and view changes"** (default) and **"Reload and apply changes immediately"** (`reload-resource.tsx:126-138`; labels at `locales/en/default.json:118-119`).
3. The request is `POST <api>/resources/reload?iri=<resource>[&url=<new URL>][&apply=true]`, with an optional JSON body `{"urls": [...]}` for multi-URL vocabularies (`reload-resource.tsx:45-68`; route at `DS/services/backend/src/main.ts:122`; handler `DS/services/backend/src/routes/import.ts:730-844`).
4. After a reload with review, the browser goes to `/evolution/review?packageIri=…&branch=<id>` (`reload-resource.tsx:75-81`; link at `DS/applications/manager/src/known-models.tsx:19-23`). The history button shows a red dot while an evolution is pending (`Dir.tsx:213-218`).

What the backend does in `reloadResource`:
- **Vocabulary model** (RDFS snapshot or cached subgraph; `import.ts:761-809`):
  - a changed URL list becomes a `changeRdfsSourceUrls` operation (`:771-774`);
  - the model is re-read (`reloadRdfsModel` or `reloadCachedSemanticModel`) and **diffed entity by entity** into operations (`diffModelEntitiesToOperations`, `DS/services/backend/src/models/model-operations.ts:53-57`).
- **Imported specification package** (`import.ts:812-843`):
  - the whole specification is re-imported from the old or new URL **into an in-memory staging overlay** (`StagingModelRepository`, `:819-831`);
  - the package IRI is reused, so models pair up;
  - all models of the package are diffed into operations (`diffModelStates`, `model-operations.ts:69-…`).
- Then either the operations are applied directly (`apply`), or they are **recorded on an evolution branch without being applied** (`recordEvolutionTransactions`, `DS/services/backend/src/models/model-repository.ts:579-643`). There is **one pending evolution branch per resource**; a new reload replaces the old one (`DS/services/backend/src/models/transaction-model.ts:287-299`).

### 5.3 What it detects

The generic diff is by entity id: created, changed (deep-equal on the whole entity) or deleted (`DS/packages/core/src/entity-model/diff.ts:9-40`). Ids of imported terms and profiles are their IRIs (B1 1.2.1). The analysis then works in two ways:

- **Vocabulary → profile edge:** the pending operations are applied to a copy of the vocabulary, and the before and after states are diffed (`DS/packages/profile-model/src/hooks/semantic-model.ts:26-38`).
- **Profile → profile edge:** the upstream profile is **aggregated through its whole hierarchy before and after**, and the aggregated states are diffed. This catches indirect effects and suppresses no-ops (`DS/packages/profile-model/src/hooks/profile-model.ts:31-64`).
- Edges are found because a dependent model's profiles list ids (`profiling[]`) that exist in the upstream model (`DS/applications/history/src/pages/evolution/evolution-data.ts:257-299`). Edges between two models changed by the same branch are skipped, because "the branch is one atomic upstream update" (`evolution-data.ts:301-315,390-453`). The aggregator used here is "a stand-in … these proof-of-concept projects" (`evolution-data.ts:329-335`).

| Change upstream | Detected? | Evidence |
|---|---|---|
| Class, relationship or generalization added | Yes, as a create item. A **new relationship only when both end classes are already profiled, or proposed in the same review** ("new relationship between classes with no profiles produces no item"). | `evolution-items.ts:268-347`; test `DS/packages/profile-model/src/hooks/semantic-model.spec.ts:183` |
| Class or relationship deleted | Yes, as a delete item with cascade | `evolution-items.ts:375-389,771-890` |
| Name, definition, usage note changed (usage note only if upstream is a profile) | Yes, as a field decision | `:398-470,495-543` |
| Cardinality changed (per end) | Yes | `:545-554,685-734` |
| Domain or range **class** retyped | Yes, but only when a class profile for the new class exists or is proposed | `:556-586` |
| Domain or range **datatype** changed (e.g. `dcat:byteSize` `xsd:decimal` → `xsd:nonNegativeInteger`, DCAT2-DAP → DCAT3-DAP) | **No.** There are no class-profile candidates for a datatype, so no decision is made, and the dependent profile keeps its own old datatype (inferred from `:557-559`). | |
| External documentation URL changed | Yes | `:740-765` |
| **Requirement level or class role changed** | **No.** These are tags. They are not inherited (aggregators at `…-relationship-profile-aggregator.ts:156` and `…-class-profile-aggregator.ts:144`), and there is no decision kind for them (no `tags` in `evolution-items.ts`). | |
| **Renamed IRI** (e.g. `dcat-ap#Category` → `dcat-ap#Concept`, both `dsv:class skos:Concept`) | **No: it appears as delete plus create** | `diff.ts:9-40`; 5.7 |
| **Deprecated term** (`owl:deprecated`) | **No.** The RDFS adapter does not read `owl:deprecated` (no hit in `DS/packages/rdfs/src`). | |
| Upstream profile re-pointed to another term (`profiling` changed) | No decision kind | `evolution-items.ts:398-600` |
| Legal refinement after the change | **Not checked** | section 4 |

### 5.4 What it proposes: kinds, severities, defaults

Severities (`evolution-items.ts:52-64`):
- `automatic`: "flows through inheritance";
- `decision`: "a safe default exists and is preselected";
- `attention`: "real conflict … no safe default; the user must look".

Every decision can also be set to **"Resolve manually"**: it becomes a to-do with a tick box "I resolved this manually in the conceptual model editor" (`DS/applications/history/src/pages/evolution/review-state.ts:11-12`; `locales/en/default.json` key `evolution.manual-todo`).

| Item and situation | Severity | Choices (ids) | Default | Evidence |
|---|---|---|---|---|
| New upstream class → create class profile | decision | apply or not (check box) | **checked**: every item starts with `checked: true` | `evolution-items.ts:273-290`; `review-state.ts:89` |
| New relationship, both ends profiled → create relationship profile (one per pair of domain and range profiles); depends on proposed class profiles | decision | apply or not | checked | `:308-340` |
| New generalization → create profile generalization | decision | apply or not | checked | `:342-347,928-956` |
| Field the profile **inherits** changed (text or cardinality) | automatic | `inherit`, `freeze-old` | `inherit` | `:633-646,698-709` |
| Field the profile **overrides**, and the override now equals the new value | decision | `drop-override`, `keep-override` | `drop-override` | `:653-665,711-722` |
| Field the profile overrides, override differs (conflict) | attention | text: `keep-own`, `adopt-new`, `inherit`; cardinality: `keep-own`, `adopt-new` | **`keep-own`** | `:667-678,724-733` |
| Documentation URL changed (not inheritable) | decision if the profile had the old value, else attention | `adopt-new`, `keep-own` | `adopt-new` or `keep-own` | `:740-765` |
| Domain or range class retyped | attention | `keep-own`, `retarget:<profile>` (may depend on a proposed class profile) | `retarget:…` if exactly one existing candidate, else `keep-own` | `:556-586` |
| Upstream class or relationship deleted | attention | `delete` (cascades to the relationship profiles and generalizations that use it), `detach` (keep the profile, unlink it, freeze inherited texts) | `detach` if the profile also profiles other entities, else `delete` | `:771-890` |
| Upstream generalization deleted | decision | `delete`, `keep` | `delete` | `:892-922` |

The review screen groups items into New classes, New relationships, New generalizations, Deletions and Modifications. It also shows the raw upstream operations "for information" and counts per kind (`locales/en/default.json`, keys `evolution.section.*`; `iswc2026.md:74-83`). Checking an item checks its dependencies; unchecking it unchecks its dependents and resets choices that relied on it (`review-state.ts:103-172`).

### 5.5 What the human decides

- Per create item: include or not. Per decision: one choice, or manual. Per delete: delete, detach or manual (5.4).
- **The upstream change itself is not negotiable.** "The upstream changes are not negotiable — the upstream models moved to a new version; all pending operations … are committed wholesale with the first apply" (`DS/applications/history/src/pages/evolution/evolution-page.tsx:170-208`, quote at `:175-178`).
- **"Accept update & apply selected"** commits, in one transaction, all upstream operations plus the profile operations of every resolved decision. It then deletes the evolution branch. The page stays open for the remaining manual items (`evolution-page.tsx:58-68,170-208`).
- On the overview page (`DS/applications/history/src/pages/evolution/overview-page.tsx:31-40,83-114`):
  - **"Skip evolution"**: accept the upstream changes "without any reaction in the dependent models";
  - **"Cancel evolution"**: "Discard the pending changes and keep all models as they are" (deletes the branch, i.e. rollback).

### 5.6 What is kept from the old state

| Kept | How | Evidence |
|---|---|---|
| Package identity | `rootPackageId = existingPackageIri` | `import.ts:495` |
| Sub-model identity (profiled specifications and vocabularies) | Matched by the same URL or the same profile IRI. A raw vocabulary under a changed URL is matched by its dominant namespace, so `dcat2.ttl` → `dcat3.ttl` stays "the dcat model". An HTML specification under a new URL with no IRI match is imported as new. Children not touched by the reload are **deleted**. | `import.ts:556-618,637-638` |
| Entity identity | IRIs. Same IRI = "modified"; new IRI = delete plus create. | 5.3 |
| Generator configuration | Reused model id | `import.ts:524-533` |
| The dependent profile's own values | Defaults keep overrides (`keep-own`, `keep-override`); `freeze-old` and `detach` copy old inherited values into the profile | 5.4 |
| Snapshot and history | The analysis is frozen at load time. The pending operations live on the evolution branch until accept; then they are ordinary transactions in the project history. | `evolution-page.tsx:88-112`; `transaction-model.ts:287-299` |
| Not kept | The URL in metadata (`importedFromUrl` is overwritten, `import.ts:498-503`); untouched children; visual diagrams of imported specifications ("visual diagrams are not imported", `iswc2026.md:63`) | |

### 5.7 Measured: what the swap looks like on their data (`dsv_version_diff.py`, by IRI)

| Upstream move | Term profiles old → new | Same IRI | Added | Removed | Changed on same IRI |
|---|---|---|---|---|---|
| DCAT2-DAP → DCAT3-DAP | 105 → 123 | 104 | 19: `DatasetSeries`, `Dataset.inSeries`, `Catalog.resource`, the version and series properties on `CatalogedResource`, `Checksum`, `ChecksumAlgorithm`, `Distribution.checksum`, … | 1: `Catalog.hasPart` (moved to `CatalogedResource.hasPart`) | 8 definitions, 7 usage notes, 2 labels, 4 reuse sources, 1 range (`Distribution.byteSize` decimal → nonNegativeInteger, **which the review does not surface**, 5.3). No cardinality changed. |
| DCAT-AP 2.1.1 → 3.0.1 (`dcat-ap2` → `dcat-ap`) | 138 → 165 | 132 | 33, including 5 class profiles (`Activity`, `Concept`, `ConceptScheme`, `DatasetSeries`, `LegalResource`) and the `applicableLegislation` profiles | 6: `Catalogue.isPartOf`, `Category`, `Category.preferredLabel`, `CategoryScheme`, `CategoryScheme.title`, `Dataset.isVersionOf` | 25 labels, 15 reuse sources, 10 ranges (Category → Concept ×7, CategoryScheme → ConceptScheme, `Dataset.versionNotes` Literal → langString, `Dataset.isReferencedBy`), 7 `profileOf`, 4 definitions, 2 usage notes, 4 property, 2 class, **4 requirement levels (not surfaced by the review)**: `Catalogue.service` optional → recommended, `Dataset.publisher` mandatory → recommended, two Checksum levels dropped |

Reading (inferred): a profile of `dcat-ap#Category` would see `Category` deleted (attention, default `delete`) and `Concept` created (checked by default). Yet both profile `skos:Concept` (`dcat-ap2/dsv.ttl` and `dcat-ap/dsv.ttl`, `dsv:class skos:Concept`). A matcher keyed by vocabulary terms pairs them; Dataspecer's IRI-keyed diff does not.

### 5.8 Comparison with our working-tree rebase

The working tree has `engine/rebase.py` (`analyse_rebase`, untracked), `Pipeline.rebase` in `engine/pipeline.py`, `RebaseItem` and `RebaseReport` in `contracts.py`, `POST /api/projects/{id}/rebase` in `api/app.py`, and `RebasePanel` in `frontend/src/App.tsx`.

| Aspect | Dataspecer evolution | Our rebase (working tree) |
|---|---|---|
| Unit of matching | Entity IRI | **Vocabulary terms** (`target_class`, `path`); robust to term-profile renames |
| Base or upstream changes detected | Created, deleted and modified; texts; cardinality; class retyping; URL | `now_in_base`, `base_dropped`, `base_changed` (obligation, cardinality, range; `_facet_text`), `deprecated_by_base` (from SEMIC's deprecated-URI shapes), `dcat_now_current`, `dcat_now_later`, `dcat_outdated` (replacement map `knowledge/dcat_state.py`, `DEPRECATED_REPLACEMENTS`), `mint_now_reusable`, `class_not_in_base`, `covered_claim_lost` |
| Requirement level | **Ignored** | Compared (`obligation` in `_facet_text`) |
| Datatype range | **Ignored** | Compared |
| Deprecation, DCAT version | **Ignored** | Covered |
| Requirement coverage | n/a | `covered_claim_lost` re-proposes the atom |
| Legal refinement after the move | **None**; the default keeps a possibly illegal override | `run_verify` against the new base, including V3 "legal refinement" (`engine/verify.py`, `check_refinement`) |
| Texts (label, definition, usage note) | Inherit, freeze, drop or keep, adopt | **Not compared** |
| Staging | Branch; nothing applied until accept; skip; cancel | **Base switched immediately**; release withdrawn; no preview, no cancel |
| Per-item choices | Typed choices **with ready operations**; preselected default; batch "apply selected" | One `suggestion` string (keep, withdraw, replace, review, repropose); the reviewer edits the change by hand |
| Dependencies | `dependsOn` with check and uncheck propagation | None |
| New base elements | Proposed for inclusion, **checked by default** | Not proposed (only `now_in_base` for elements a change touches). Retrieval is re-run for atoms. |
| Human decisions | No machine and human distinction | Human decisions never overwritten (`is_human`); machine decisions → `needs_review` |

### 5.9 Spec: "rebase an extension onto another DCAT-AP or DCAT version" as a migration review queue

This is a delta to the working-tree implementation. It keeps our rules: **the base is read-only, human decisions are final, and everything is re-verified.**

**MR-1 Stage before commit** (from Dataspecer's evolution branch, skip and cancel).
- `POST /api/projects/{id}/rebase/preview {base_profile_id}` returns a `RebasePlan`: `{plan_id, from_base, to_base, from_dcat, to_dcat, change_set_hash, items[]}`. The project is not mutated.
- `POST /api/projects/{id}/rebase/{plan_id}/apply {choices: {item_id: choice_id}}` commits.
- `DELETE /api/projects/{id}/rebase/{plan_id}` cancels.
- One pending plan per project, as in `transaction-model.ts:292-294`. A plan whose `change_set_hash` no longer matches (a change was edited meanwhile) must be re-previewed.
- The current `POST …/rebase` stays as "preview and apply all defaults" for scripts.
- Files: `engine/pipeline.py` (split `rebase` into `rebase_preview`, `rebase_apply`, `rebase_cancel`), `api/app.py` (routes), `store/blackboard.py` (persist the plan, entry kind `rebase_plan`).

**MR-2 Keys.** Keep term keys (`target_class`, `path`). Never store base term-profile IRIs in a change; compute `dsv:profileOf` at compile time from the target base's index. Rename robustness is then free (5.7).

**MR-3 Diff inputs per key, base A vs base B.**
- Existence.
- Effective obligation, min, max, range class or datatype, node kind, controlled vocabulary, pattern.
- Deprecation (base deprecated-URI shapes; DCAT `history.json`) and DCAT term status.
- **New:** label, definition and usage note of the base element (needed by MR-4 `base_text_changed`).
- Files: `knowledge/base_profile.py`, `knowledge/dcat_state.py`.

**MR-4 Item kinds, with typed choices.** Each choice carries a ready `ProfileChange` patch or a withdrawal, like Dataspecer's `EvolutionChoice.operations` (`evolution-items.ts:80-95`). Severity maps as info = automatic, warning = decision, error = attention.

| Finding (existing name, or new) | Sub-case | Severity | Choices | Default |
|---|---|---|---|---|
| `now_in_base` | adds nothing beyond B | decision | `withdraw`, `keep` | `withdraw` (= Dataspecer `drop-override`) |
| `now_in_base` | still tighter than B | info | `convert_to_refine`, `keep` | `convert_to_refine` (kind `reuse_property` → `refine_property`) |
| `base_changed` (split with `conformance/refinement.compare_facets`) | **inherits**: the change does not set the facet | info | `inherit`, `pin_old` | `inherit` |
| `base_changed` | **matches_new** | decision | `withdraw_facet`, `keep` | `withdraw_facet` |
| `base_changed` | **still_legal** (still tighter) | info | `keep` | `keep` |
| `base_changed` | **now_looser** (B tightened past our value) | error | `tighten_to_intersection`, `withdraw`, `manual` | `tighten_to_intersection` when non-empty. **Never `keep`**: Dataspecer's default `keep-own` would keep an illegal value (section 4). |
| `base_changed` | **conflict** (empty intersection, incomparable range) | error | `withdraw`, `manual` | none: a human must decide |
| `base_dropped` | | decision | `keep_as_addition`, `withdraw` | `keep_as_addition` (re-run reuse-before-mint) |
| `deprecated_by_base`, `dcat_outdated` | | error | `replace:<replacement>`, `keep`, `manual` | `replace` if a replacement is known (`dct:hasVersion` → `dcat:hasVersion`; `dcat:size` → `dcat:byteSize`), else `manual` |
| `dcat_now_later` (moving to an older base) | | per `later_dcat_terms` (review, forbid, allow) | `keep`, `withdraw`, `manual` | per policy |
| `mint_now_reusable` | | warning | `replace_with:<term>` (new reuse or refine change, `supersedes` the old one, same `covers`), `keep_mint` | `keep_mint`: minted IRIs are published identifiers; the LLM judge may *recommend* the replacement but cannot apply it |
| `class_not_in_base` | | warning | `keep_as_class_addition`, `retarget:<class>`, `manual` | `keep_as_class_addition` |
| `covered_claim_lost` | | warning | `repropose` (run propose for this atom only), `manual` | `repropose` |
| **new** `covered_claim_weakened` | an atom was `covered_by_base`; B still has the element but loosened it (obligation or cardinality), e.g. `Catalogue dcat:dataset` mandatory in 2.1.1, recommended in 3.0.1. The current check fires only when the element disappears. | warning | `repropose`, `keep_claim` (record that the weaker base still satisfies the atom), `manual` | `repropose` |
| **new** `base_text_changed` | change inherits the text | info | `inherit`, `freeze_old` | `inherit` (as Dataspecer) |
| **new** `base_text_changed` | change overrides; B's new text equals the override | decision | `drop_override`, `keep` | `drop_override` |
| **new** `newly_relevant_base_element` (retrieval finds a B element for an `unaddressed` or `needs_change` atom) | | info | link only | none. **Never pre-included**, unlike Dataspecer's checked-by-default create items (`review-state.ts:89`): we profile only what a requirement touches. |
| **new** `dsv_target_changed` | | info | none | automatic: `profileOf` targets and base specification URL recomputed (2.2, B2); B without DSV → `dsv:class` or `dsv:property` fallback |

**MR-5 Dependencies.**
- `depends_on`: a property change depends on its class change, and a `replace_with` of a minted class re-targets the property changes on that class.
- Check and uncheck propagate as in `review-state.ts:103-152`.

**MR-6 Review UI.**
- One card per item, grouped into: Removed or deprecated; Changed base constraints; Now in base; Minted → reusable; Coverage; Informational.
- Badges for severity and for "human decided earlier".
- Choices are buttons with the default preselected, plus "decide manually", which leaves the change in `needs_review` with a note.
- One action, "Apply selected and move to <B>", and one "Cancel".
- Files: `frontend/src/App.tsx` (`RebasePanel` and the review tab), `frontend/src/api.ts` (`RebaseItem` with `choices`, `default_choice`, `depends_on`, `status`).

**MR-7 Apply = one atomic step, then re-verification.**
1. Write the chosen patches as new `ProfileChange`s with `supersedes` and provenance `rebased_from=<A>`.
2. Switch `base_profile_id`.
3. Mark the downstream stages stale.
4. Run retrieve, verify, consolidate, compile and conformance against B, as `Pipeline.rebase` already does.
5. A *machine* change that fails verification goes to `needs_review`. A *human-decided* change keeps its decision, but its failure blocks sign-off until a human acts. Human decisions stay final and are not silently overridden.

**MR-8 Record.**
- Extend `RebaseReport` (`contracts.py`) with `plan_id`, the chosen choice per item, `decided_by`, and the new change ids.
- Keep all reports (`Project.rebases`).
- The trace sidecar (B1 3.9) gains `prov:wasRevisionOf <old change>` for each rebased change (our interpretation).

**MR-9 Tests** (new `tests/test_rebase.py`):
- (a) an extension of 2.1.1 moved to 3.0.1. Expect:
  - `deprecated_by_base` with replacements `owl:versionInfo` → `dcat:version`, `dct:hasVersion` → `dcat:hasVersion` and `dct:isVersionOf` → `dcat:isVersionOf` (`data/base-profiles/dcat-ap-3.0.1/shacl/deprecateduris.ttl`);
  - `now_in_base` for a change on `dcat:DatasetSeries`;
  - `base_changed` / `now_looser` for a change that left `Catalogue dcat:service` optional (our `obligations.yaml`: optional in 2.1.1, recommended in 3.0.1);
  - `covered_claim_weakened` for an atom covered by 2.1.1's mandatory `Catalogue dcat:dataset` (recommended in 3.0.1);
- (b) 1.1 → 3.0.1: DCAT 2014 → DCAT 3, `dcat:size` → `dcat:byteSize`;
- (c) a human-decided change is never modified;
- (d) cancel leaves the project byte-identical.

### 5.10 Other Dataspecer capabilities we have not covered yet

| Capability | Where | On `main`? | Relevance to us |
|---|---|---|---|
| Operation log with up and down events; full history page; evolution branches; LDES export | `DS/services/backend/src/models/transaction-model.ts`; `DS/applications/history/src/pages/history/history-page.tsx`; `main.ts:109-112` | yes | Medium: our blackboard is an append log. "Diff two states of the extension" and "undo a decision" could reuse the idea. |
| Multi-URL vocabularies ("RDFS snapshot"), reloadable with an edited URL list; cached subgraphs | `import.ts:761-809`; `DS/packages/rdfs/src/semantic-model/implementation.ts:34` | yes | Low: we vendor vocabularies |
| Controlled vocabularies: manager, assignments with qualifiers `must`, `at-least-one`, `recommended`, `may`; SHACL `sh:pattern` and `skos:inScheme` with severity; documentation; catalogue embedded in `dsv.ttl` | 1.2 | yes (DSV terms unpublished) | Medium: our `controlled_vocabulary` facet could export to the same SHACL pattern (B1 4.2) |
| Multiprofiling (one profile profiles several terms) | `profiling[]` (B1 1.2.2); iiWAS 2026 paper (verify) | yes | Low or medium: a requirement may need one property profile over two terms |
| Git integration (commit, pull, merge-conflict diff editor, GitHub Action publication) | `DS:git-integration` | no | Medium for collaboration; not now |
| Domain-map AI link, knowledge base model | `DS:feature/project-AI-vocabularies-connection` | no | Watch: possible future overlap |
| Geo datatypes (WKT, GML) | merge `a4cddef90` | yes | Low |
| Automatic diagram layout for specifications without a visual model | `6f2671e84` | yes | Medium for the workbench canvas (B1 section 6) |
| Documentation templates with diff, regexes and examples | 1.2 | yes | Low |
| App generator, LDkit generator | branches `app-generator`, `feature/ldkit_generator` | no | No |

## 6. Publications (Q5)

Verification means a search-index record of the primary page (publisher, DBLP, CEUR-WS or the university repository) showing the title, authors and venue. Direct page fetches of dblp.org and link.springer.com were blocked in this session (0). A field that did not appear in such a record is omitted, or marked **verify**. The Dataspecer website source lists the group's papers (`DS/www/layouts/index.html:70-110`, commit "Add current publications" `bed4b8264`, 2026-09-25), and `DS/CITATION.cff` gives the ESWC 2022 entry with its editors.

| # | Year | Title | Authors | Venue, pages | DOI or URL | Status |
|---|---|---|---|---|---|---|
| P1 | 2022 | DataSpecer: A Model-Driven Approach to Managing Data Specifications | Štěpán Stenchlák, Martin Nečaský, Petr Škoda, Jakub Klímek | The Semantic Web: ESWC 2022 Satellite Events, LNCS 13384, pp. 52–56, Springer | 10.1007/978-3-031-11609-4_10 | **verified** (Springer chapter page; DBLP `conf/esws/eswc2022s`; `DS/CITATION.cff`) |
| P2 | 2023 | Atlas: A Toolset for Efficient Model-Driven Data Exchange in Data Spaces | Jakub Klímek, Pavel Koupil, Petr Škoda, Jáchym Bártík, Štěpán Stenchlák, Martin Nečaský, Irena Holubová | MODELS-C 2023 (Tools and Demonstrations), pp. 4–8, IEEE | DOI **verify**: `10.1109/MODELS-C59198.2023.00009`, as linked from `DS/www/layouts/index.html:99`, not shown by the IEEE record | **verified** except the DOI (IEEE Xplore record; DBLP `conf/models/models2023c`) |
| P3 | 2023 | A framework for data specification modeling in complex domains | Štěpán Stenchlák | ER 2023 Companion (Doctoral Consortium), CEUR-WS Vol-3618 (published 2024-01-15) | https://ceur-ws.org/Vol-3618/ | **verified** (CEUR-WS index); paper number not seen |
| P4 | 2024 | Towards Authoring of Vocabularies and Application Profiles using Dataspecer | Jakub Klímek, Štěpán Stenchlák, Adam Polický, Petr Škoda, Martin Nečaský | ISWC 2024 Posters, Demos and Industry Tracks, CEUR-WS Vol-3828 (2024-11-11); Best Demo Award | https://ceur-ws.org/Vol-3828/paper33.pdf | **verified** (CEUR-WS index; DBLP `conf/semweb/KlimekSP0N24`; award per `DS/www/layouts/index.html:90-94`) |
| P5 | 2024 | Enhancing Domain Modeling with Pre-trained Large Language Models: An Automated Assistant for Domain Modelers | Dominik Prokop, Štěpán Stenchlák, Petr Škoda, Jakub Klímek, Martin Nečaský | Conceptual Modeling, ER 2024, LNCS, pp. 235–253, Springer | 10.1007/978-3-031-75872-0_13 | **verified** (Springer chapter page; DBLP). LNCS volume number not seen. |
| P6 | 2025 | Data Specification Vocabulary (DSV): Representation of Application Profiles of Semantic Data Specifications | Jakub Klímek, Štěpán Stenchlák, Petr Škoda | iiWAS 2025, LNCS 16330, pp. 221–236, Springer | DOI **verify**: `10.1007/978-3-032-11976-6_16`, seen only in W3C `dx-dcat` issue 498, not on Springer | **verified** except the DOI (DBLP `conf/iiwas/iiwas2025`; Springer book page) |
| P7 | 2026 | Dataspecer: Development of Consistent Semantic Data Specification Ecosystems | Štěpán Stenchlák, Jakub Klímek, Petr Škoda, Martin Nečaský | Semantic Web (SAGE) | 10.1177/22104968261479880 | **verified** (SAGE article page; SWJ accepted list). Volume and issue **verify**. |
| P8 | 2026 | Change Propagation in Application Profile Hierarchies using Dataspecer | **verify** | ISWC 2026 Posters and Demos (announced) | https://dataspecer.com/papers/iswc2026 | **verify**: only the project site and `DS/www/content/en/papers/iswc2026.md`; no proceedings record found |
| P9 | 2026 | Reusing Multiple Vocabularies in Semantic Data Specifications: the Multiprofiling Approach | **verify** | iiWAS 2026, short paper (announced) | none | **verify**: only `DS/www/layouts/index.html:76-80` |
| P10 | 2023 | "Conceptual-model-first data specification design approach" (ER 2023 landing page) | **verify** | ER 2023 (instance) | `DS/www/content/en/er2023.md:2` | **verify**: no paper with this title found; possibly a demo or tutorial (inferred) |
| R1 | 2019 | DCAT-AP representation of Czech National Open Data Catalog and its impact | Jakub Klímek | Journal of Web Semantics 55, pp. 69–85 | 10.1016/j.websem.2018.11.001 | **verified** (ScienceDirect; DBLP `journals/ws/Klimek19`) |
| R2 | 2012 | Evolution and change management of XML-based systems | Martin Nečaský, Jakub Klímek, Jakub Malý, Irena Mlýnková | Journal of Systems and Software 85(3), pp. 683–707 | 10.1016/j.jss.2011.09.038 | **verified** (ScienceDirect). The group's earlier model-driven change propagation, the root of section 5 (inferred). |
| R3 | 2026 | Improving Linked Data Development Experience with LDkit | Karel Klíma, Ruben Taelman, Martin Nečaský | Semantic Web (SAGE) | 10.1177/22104968251404248 | **verified** (SAGE page) |
| T1 | 2024 | Using large language model as an assistant for conceptual modeling (master thesis; Czech title "Použití velkého jazykového modelu jako asistenta pro konceptuální modelování") | Dominik Prokop | Charles University, Faculty of Mathematics and Physics; defended 2024-09-11 | https://dspace.cuni.cz/handle/20.500.11956/193876 | **verified** (repository record); supervisor not seen |
| T2 | 2026 | Context-Enriched Prompting Strategies for Automated Data Specification Adjustment in Dataspecer Using LLMs, RAG and MCP (master thesis) | Egor Ulianov | Charles University, Faculty of Mathematics and Physics, Department of Software Engineering; defended 2026-02-10 | https://dspace.cuni.cz/handle/20.500.11956/207052 | **verified** (repository record); supervisor not seen. **Closest prior work to our LLM proposer**: LLM-driven structured changes to Dataspecer specifications. Its tool is not in the Dataspecer repository (no MCP or LLM code, 1.2). |
| S1 | 2025 | Data Specification Vocabulary (vocabulary, version 1.0.0, released 2025-05-13) | Jakub Klímek, Štěpán Stenchlák, Petr Škoda | https://w3id.org/dsv | `DSV/CITATION.cff` | **verified** (self-published citation file; the repository now carries 1.0.1) |
| S2 | n/a | Dataspecer (software, MIT) | Stenchlák, Nečaský, Škoda, Klímek, Čermák, Janda, Miklóšová, Gora, Polický, Bujko, Strýček, Akhvlediani | https://github.com/dataspecer/dataspecer | `DS/CITATION.cff` | **verified** (self-published); the preferred citation is P1 |

Count: **14 verified** entries (P1 to P7, R1 to R3, T1, T2, S1, S2; P2 and P6 lack a confirmed DOI, P7 a confirmed volume) and **3 to verify** (P8 to P10). BibTeX follows in section 9, for verified entries only.

## 7. Recommendations (Q6)

Value: H, M or L. Effort: S (hours), M (days), L (weeks). Within each list, items are ranked by value over effort.

### (a) Reuse directly

| Rank | What | Licence | Value / effort | Files in our repository |
|---|---|---|---|---|
| A1 | **DCAT 3 DAP and DCAT 2 DAP as a regression oracle** for `data/dcat/*/model.json`. Vendor `SPEC/dcat-dap/dsv.ttl` and `SPEC/dcat2-dap/dsv.ttl` at `833685e` as test fixtures; assert pair coverage with the allowlist of section 3. | MIT (`SPEC/LICENSE`); content from W3C DCAT; attribute both | H / S | `tests/test_dcat_state.py` (extend) or new `tests/test_dcat_model_vs_dap.py`; `tests/fixtures/dap/` |
| A2 | **2.1.1 DSV index from `dcat-ap2`**, with a pinned commit, a `known_deviations` list (2.3) and the specification URL; fallback to `dsv:property` for the missing pairs | MIT; content from SEMIC (CC BY 4.0) | M / S | `scripts/build_base_profile.py` (index builder, as B1's `build_base_index.py`); `data/base-profiles/dcat-ap-2.1.1/dsv-index.json` (new); `…/dcat-ap-2.1.1/profile.yaml` (`dsv_index`, `dsv_specification_url`, `dsv_commit`); `knowledge/base_profile.py` (`dsv_*` lookups) |
| A3 | **DAP fallback in the index**: (class, path) → `…/dcat-dap#…` profile when the DCAT-AP DSV lacks it (HVD pattern, `SPEC/dcat-ap-hvd/dsv.ttl:197`) | MIT | M / S | `knowledge/base_profile.py` (`dsv_property_profile`, `dsv_class_profile`); `compile/linkml_dsv.py` (`compile_dsv`) |
| A4 | **Dataspecer's evolution taxonomy as the design of our rebase queue**: severities, choice ids (`inherit`, `freeze-old`, `drop-override`, `keep-own`, `adopt-new`, `detach`, `retarget`, `manual`), defaults, `dependsOn` (5.4). Design reuse only; we are Python. | MIT (code not copied) | H / S | `contracts.py` (`RebaseItem`), `engine/rebase.py` |
| A5 | **DSV and its code lists** (already used); cite P6 and S1 | CC BY 4.0 | L / S | `README.md`, `docs/` |
| A6 | **Interop run in Dataspecer** (`ghcr.io/dataspecer/ws`): import our compiled 2.1.1 extension, then reload its base URL from `…/dcat-ap2/` to `…/dcat-ap/`, and record what their evolution review shows. This turns 5.7 into an experiment for the paper. | n/a | M / M | `docs/research/` (protocol), `examples/` |

Not reusable: DSV for DCAT-AP 1.1, 1.2, 1.2.1, 2.0.0, 2.0.1, 2.1.0 and 3.0.0, and for DCAT 2014. None is published; keep the vocabulary fallback.

### (b) Implement, inspired by them

| Rank | What | Value / effort | Files |
|---|---|---|---|
| B1 | **Fix the DCAT model extractor**: repeated rows (`dcat:DataService` superclass and usage notes) and "rdfs:Literal typed as X" ranges; optionally domain-derived pairs. Regenerate. | H / S | `scripts/build_dcat_versions.py` (`extract_model`, the `fields` dict and the `range` entry); `data/dcat/*/model.json`, `versions.yaml`; tests |
| B2 | **Version-unambiguous DSV output**:<br>(1) add the base specification URL (`hasArtifact`, e.g. `…/dcat-ap2/`) next to `prof:isProfileOf <…/dcat-ap#>`;<br>(2) state the DCAT basis (e.g. `dct:conformsTo` the DCAT TR used) in the specification metadata, or in the B1 3.8 wrapper when it is built.<br>Needed because 2.1.1 and 3.0.1 share all IRIs (2.2). | H / S | `compile/linkml_dsv.py` (`compile_dsv`, line with `PROF.isProfileOf`); `data/base-profiles/*/profile.yaml`; `knowledge/base_profile.py` |
| B3 | **Staged migration review queue** (5.9, MR-1 to MR-9): preview, apply, cancel; typed choices with patches; defaults; dependencies; manual; re-verification | H / M | `engine/rebase.py`; `engine/pipeline.py` (`rebase`); `contracts.py` (`RebaseItem`, `RebaseReport`, new `RebasePlan`); `api/app.py` (`RebaseRequest`, `/rebase` routes); `store/blackboard.py`; `frontend/src/App.tsx` (`RebasePanel`, review tab); `frontend/src/api.ts`; new `tests/test_rebase.py` |
| B4 | **Split `base_changed` by legality** (inherits, matches_new, still_legal, now_looser, conflict) with `compare_facets`; `now_looser` is never kept | H / S | `engine/rebase.py` (`analyse_rebase`, section 1); `conformance/refinement.py` (`compare_facets`) |
| B5 | **Do not pre-include new base elements** (policy): `newly_relevant_base_element` stays informational, linked to atoms | H / S | `engine/rebase.py`, `frontend/src/App.tsx` |
| B6 | **Text reuse versus override per field** (B1 2 #4), enabling `base_text_changed` and DSV `PropertyValueReuse` | M / M | `contracts.py` (`ProfileChange`); `compile/linkml_dsv.py`; `engine/rebase.py` |
| B7 | **Base-to-base diff report** (5.7 numbers for any two of our nine bases): helps choose a base and documents a rebase | M / S | `api/app.py` (`GET /api/base-profiles/{a}/diff/{b}`); `knowledge/base_profile.py` |

### (c) Where we are clearly stronger, and how to say it

| Claim | Evidence to cite | Suggested wording |
|---|---|---|
| Refinement and conformance are checked; Dataspecer checks neither, at authoring or in evolution | B1 section 5; `DS/packages/profile-model/src/hooks/evolution-items.ts:685-734` (`keep-own` default with no legality test); `DS/packages/shacl-v2/…/structure-model-factory.ts:410-473` (lost lower bounds, B1 4.4) | "Dataspecer [P1, P7] propagates upstream changes along profile hierarchies (ISWC 2026 demo), but at commit ece634b it neither checks that a profile narrows its base nor flags overrides that a new base version makes illegal. Our tool verifies every element against the effective base constraints, at authoring time and after a base change." |
| Requirement levels are constraints, are compared on a base change, and reach SHACL | `…/semantic-relationship-profile-aggregator.ts:156` (tags not inherited); no tag decision in `evolution-items.ts`; B1 4.2 | "In Dataspecer requirement levels are non-inherited annotations: they are not propagated, not compared on evolution, and not compiled to SHACL." |
| Requirement traceability (atom → change → artefact) and LLM proposals with symbolic verification and a judge | No LLM code in DS (1.2); P5 and T2 are research prototypes outside the tool | "LLM assistance in the Dataspecer ecosystem targets vocabulary modelling from text [P5] and specification adjustment [T2]. Neither starts from requirement atoms or verifies conformance to a base profile." |
| Rebase matched by vocabulary terms, robust to term-profile renames | 5.7: 6 removed and 33 added IRIs between their 2.1.1 and 3.0.1 DSVs, including `Category` → `Concept` (same `skos:Concept`) | "Profiles matched by profile IRI break under re-identification; we key extension elements by vocabulary terms." |
| DCAT-version awareness, with evidence per base and D1/D2 checks | `OURS/data/base-profiles/*/profile.yaml` `dcat_basis`; `engine/verify.py` (D1, D2); 2.2 (shared IRIs; version only in HTML metadata) | "Each base is pinned to the DCAT state it builds on, with citations; terms later than, or deprecated in, that state are flagged." |
| Be fair about where they are stronger | B1 sections 1 and 6; 5.10 | Editing UX, visual modelling, documentation, many generators (JSON Schema, XSD, CSVW, SHACL, ShEx, OpenAPI), controlled vocabularies, operation history, and a staged evolution review with ready-made choices. Our queue adopts that last design (A4). |

## 8. Open points (verify)

1. P8, P9, P10: authors and proceedings. The DOIs of P2 and P6, and the volume and issue of P7.
2. W3C `dx-dcat` issue 498: author, status, and whether W3C plans a DSV representation of DCAT (2.5).
3. Whether the external "slovniky-AI" assistant (1.3) and Ulianov's tool (T2) are public, and what they do with application profiles.
4. A6: run the reload of a 2.1.1-based extension inside Dataspecer to confirm 5.3 and 5.7 by experiment; B1's import experiment is also still open.
5. Licence of vendored `SPEC/` files: MIT covers the repository, but the content derives from SEMIC (CC BY 4.0) and W3C DCAT. Confirm the attribution text (inferred).
6. Whether upstream regards the defects of section 3 and 2.3 as bugs (`wasGeneratedBy` range; the 2.x downgrade items; `Dataset.publisher` level in `dcat-ap2`).
7. Our working tree changed during this study. Re-check the line numbers in 5.8 and 7 against the committed state.

## 9. BibTeX (verified entries only)

```bibtex
@inproceedings{stenchlak2022dataspecer,
  author    = {Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and Ne{\v{c}}ask{\'y}, Martin and {\v{S}}koda, Petr and Kl{\'\i}mek, Jakub},
  title     = {{DataSpecer}: A Model-Driven Approach to Managing Data Specifications},
  booktitle = {The Semantic Web: ESWC 2022 Satellite Events},
  editor    = {Groth, Paul and Rula, Anisa and Schneider, Jodi and Tiddi, Ilaria and Simperl, Elena and Alexopoulos, Panos and Hoekstra, Rinke and Alam, Mehwish and Dimou, Anastasia and Tamper, Minna},
  series    = {Lecture Notes in Computer Science},
  volume    = {13384},
  pages     = {52--56},
  publisher = {Springer},
  year      = {2022},
  doi       = {10.1007/978-3-031-11609-4_10}
}

% DOI not confirmed on the publisher record; dataspecer.com links 10.1109/MODELS-C59198.2023.00009 (verify before adding).
@inproceedings{klimek2023atlas,
  author    = {Kl{\'\i}mek, Jakub and Koupil, Pavel and {\v{S}}koda, Petr and B{\'a}rt{\'\i}k, J{\'a}chym and Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and Ne{\v{c}}ask{\'y}, Martin and Holubov{\'a}, Irena},
  title     = {Atlas: A Toolset for Efficient Model-Driven Data Exchange in Data Spaces},
  booktitle = {2023 ACM/IEEE International Conference on Model Driven Engineering Languages and Systems Companion (MODELS-C)},
  pages     = {4--8},
  publisher = {IEEE},
  year      = {2023}
}

@inproceedings{stenchlak2023framework,
  author    = {Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n},
  title     = {A framework for data specification modeling in complex domains},
  booktitle = {Companion Proceedings of the 42nd International Conference on Conceptual Modeling (ER 2023), Doctoral Consortium},
  series    = {CEUR Workshop Proceedings},
  volume    = {3618},
  publisher = {CEUR-WS.org},
  year      = {2023},
  url       = {https://ceur-ws.org/Vol-3618/}
}

@inproceedings{klimek2024authoring,
  author    = {Kl{\'\i}mek, Jakub and Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and Polick{\'y}, Adam and {\v{S}}koda, Petr and Ne{\v{c}}ask{\'y}, Martin},
  title     = {Towards Authoring of Vocabularies and Application Profiles using {Dataspecer}},
  booktitle = {Posters, Demos, and Industry Tracks at ISWC 2024},
  series    = {CEUR Workshop Proceedings},
  volume    = {3828},
  publisher = {CEUR-WS.org},
  year      = {2024},
  url       = {https://ceur-ws.org/Vol-3828/paper33.pdf},
  note      = {Best Demo Award}
}

@inproceedings{prokop2024enhancing,
  author    = {Prokop, Dominik and Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and {\v{S}}koda, Petr and Kl{\'\i}mek, Jakub and Ne{\v{c}}ask{\'y}, Martin},
  title     = {Enhancing Domain Modeling with Pre-trained Large Language Models: An Automated Assistant for Domain Modelers},
  booktitle = {Conceptual Modeling. ER 2024},
  series    = {Lecture Notes in Computer Science},
  pages     = {235--253},
  publisher = {Springer},
  year      = {2024},
  doi       = {10.1007/978-3-031-75872-0_13}
}

% Chapter DOI not confirmed on Springer; W3C dx-dcat issue 498 cites 10.1007/978-3-032-11976-6_16 (verify before adding).
@inproceedings{klimek2025dsv,
  author    = {Kl{\'\i}mek, Jakub and Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and {\v{S}}koda, Petr},
  title     = {Data Specification Vocabulary ({DSV}): Representation of Application Profiles of Semantic Data Specifications},
  booktitle = {Information Integration and Web Intelligence. iiWAS 2025},
  series    = {Lecture Notes in Computer Science},
  volume    = {16330},
  pages     = {221--236},
  publisher = {Springer},
  year      = {2025}
}

% Volume and issue not confirmed (verify).
@article{stenchlak2026dataspecer,
  author    = {Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and Kl{\'\i}mek, Jakub and {\v{S}}koda, Petr and Ne{\v{c}}ask{\'y}, Martin},
  title     = {{Dataspecer}: Development of Consistent Semantic Data Specification Ecosystems},
  journal   = {Semantic Web},
  year      = {2026},
  doi       = {10.1177/22104968261479880}
}

@article{klimek2019dcatap,
  author    = {Kl{\'\i}mek, Jakub},
  title     = {{DCAT-AP} representation of {Czech} National Open Data Catalog and its impact},
  journal   = {Journal of Web Semantics},
  volume    = {55},
  pages     = {69--85},
  year      = {2019},
  doi       = {10.1016/j.websem.2018.11.001}
}

@article{necasky2012evolution,
  author    = {Ne{\v{c}}ask{\'y}, Martin and Kl{\'\i}mek, Jakub and Mal{\'y}, Jakub and Ml{\'y}nkov{\'a}, Irena},
  title     = {Evolution and change management of {XML}-based systems},
  journal   = {Journal of Systems and Software},
  volume    = {85},
  number    = {3},
  pages     = {683--707},
  year      = {2012},
  doi       = {10.1016/j.jss.2011.09.038}
}

@article{klima2026ldkit,
  author    = {Kl{\'\i}ma, Karel and Taelman, Ruben and Ne{\v{c}}ask{\'y}, Martin},
  title     = {Improving Linked Data Development Experience with {LDkit}},
  journal   = {Semantic Web},
  year      = {2026},
  doi       = {10.1177/22104968251404248}
}

@mastersthesis{prokop2024thesis,
  author    = {Prokop, Dominik},
  title     = {Using large language model as an assistant for conceptual modeling},
  school    = {Charles University, Faculty of Mathematics and Physics},
  year      = {2024},
  url       = {https://dspace.cuni.cz/handle/20.500.11956/193876},
  note      = {Defended 2024-09-11}
}

@mastersthesis{ulianov2026thesis,
  author    = {Ulianov, Egor},
  title     = {Context-Enriched Prompting Strategies for Automated Data Specification Adjustment in {Dataspecer} Using {LLMs}, {RAG} and {MCP}},
  school    = {Charles University, Faculty of Mathematics and Physics, Department of Software Engineering},
  year      = {2026},
  url       = {https://dspace.cuni.cz/handle/20.500.11956/207052},
  note      = {Defended 2026-02-10}
}

@misc{dsv2025,
  author       = {Kl{\'\i}mek, Jakub and Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and {\v{S}}koda, Petr},
  title        = {Data Specification Vocabulary},
  howpublished = {\url{https://w3id.org/dsv}},
  year         = {2025},
  note         = {Version 1.0.0, released 2025-05-13 (CITATION.cff); repository github.com/mff-uk/data-specification-vocabulary, version 1.0.1 at commit 5c1d655; CC BY 4.0}
}

@misc{dataspecer_software,
  author       = {Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and Ne{\v{c}}ask{\'y}, Martin and {\v{S}}koda, Petr and Kl{\'\i}mek, Jakub and {\v{C}}erm{\'a}k, Marek and Janda, Jan and Mikl{\'o}{\v{s}}ov{\'a}, Tereza and Gora, Martin and Polick{\'y}, Adam and Bujko, Viktor and Str{\'y}{\v{c}}ek, Radek and Akhvlediani, Anastasia},
  title        = {Dataspecer},
  howpublished = {\url{https://github.com/dataspecer/dataspecer}},
  note         = {Software, MIT licence; commit ece634b (2026-11-12). Preferred citation: stenchlak2022dataspecer}
}
```
