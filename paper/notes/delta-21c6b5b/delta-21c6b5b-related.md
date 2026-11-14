# Delta 5ffd56e -> 21c6b5b: related work (B3), security (D1-D2), workbench (C9-C10, figure)

Area "related" of the 21c6b5b delta. Read-only on both worktrees; nothing was written into either one.
Abbreviations: `WT2/` = worktree of main at 21c6b5b, `B/` = `backend/profile_extensioner/` at 21c6b5b,
`B3` = `docs/research/B3-dataspecer-update.md` (WT2), `DS@ece634b` = dataspecer/dataspecer at commit
ece634b8c5 (the commit B3 read), `P/` = `paper/`. Line numbers are at 21c6b5b unless marked `@5ffd56e`.

## 0. Method and sources

- Git: `git log 5ffd56e..21c6b5b` = 5 commits (9321951, 40a5d5d, a3d8098, 913bea2, 21c6b5b). B3 was added in
  **40a5d5d** (694 lines, 2026-11-14 18:11) and is unchanged at 21c6b5b. Diffs read for `B/api/app.py`,
  `B/llm/registry.py`, `B/engine/rebase.py`, `B/engine/pipeline.py` (rebase, release, metrics, snapshot),
  `B/contracts.py` (rebase records, PipelineConfig), `B/compile/linkml_dsv.py`, `frontend/src/{App,Inspector}.tsx`,
  `frontend/src/api.ts`, `README.md`, `docs/dcat-versions.md`, `docs/design.md`, `tests/fixtures/dap/*`.
- Probes (all offline; project virtualenv `/home/user/.venv-rbdpe`, `python -B`, `PYTHONPATH=WT2/backend` or the
  5ffd56e worktree, `Store(":memory:")`, mock provider; scripts and outputs in
  `scratchpad/related-delta-probe/`):
  1. `demo_probe.py`, `mint_detail.py`: the synthetic demo `examples/materials-testing-lab` at both commits.
  2. `now_in_base_probe.py`: one synthetic atom and change, rebase plan 2.1.1 -> 3.0.1.
  3. `spa_probe.py`: the SPA catch-all route called as an ASGI app (no server, no network); workspace and a fake
     `frontend/dist` in `scratchpad/related-delta-probe/spa/`.
  4. `dap_pairs.py`: our DCAT models against the Dataspecer DAP test fixtures.
  5. An inline probe of `Credentials` (key binding to an origin; no request sent).
- Network: curl reaches only raw.githubusercontent.com and pypi.org (doi.org, api.crossref.org, dblp.org,
  ceur-ws.org, link.springer.com, dspace.cuni.cz, journals.sagepub.com, ieeexplore, sciencedirect, openalex,
  semanticscholar: code 000). WebSearch works. WebFetch of dspace.cuni.cz failed ("ENOTFOUND"); that host would
  have to be allowed in the session's network settings. No further sites were tried.
- Fetched (raw.githubusercontent.com, each into its own directory under `scratchpad/related-delta-dl/`, read as data):

  | File | Ref | sha256 (first 8) | Used for |
  |---|---|---|---|
  | dataspecer/dataspecer `CITATION.cff` | main | 9f8efecf | P1 fields (preferred-citation, l.42-90), S2 |
  | dataspecer/dataspecer `www/layouts/index.html` | main | 18bafbbe | P4 URL and award (l.89-94), P7 DOI (l.82-85), P2 DOI link (l.97-100), P8/P9 announcements (l.70-79) |
  | dataspecer/dataspecer `www/content/en/papers/iswc2026.md`, `iswc2024.md` | main | 84c5cbfc, 3ac45514 | P8 "Demo Submission" (l.6), P4 title (l.6) |
  | mff-uk/data-specification-vocabulary `CITATION.cff` | main | 87c6143d | S1 (version 1.0.0, 2025-05-13) |
  | `packages/core/src/entity-model/diff.ts` | ece634b | 1d9ee79a | "keyed by entity id" (l.9-40) |
  | `packages/profile-model/src/hooks/evolution-items.ts` | ece634b | dc49d4df | severities (l.52-64), `cardinalityDecision` keep-own default (l.685-734) |
  | `applications/history/src/pages/evolution/evolution-page.tsx` | ece634b | 72cfb9f2 | upstream "not negotiable" (l.175-178) |

## 1. What changed in this area (5ffd56e -> 21c6b5b)

| Item | Change | Where (21c6b5b) |
|---|---|---|
| B3 research report | new: Dataspecer 2026 activity, DCAT/DCAT-AP DSVs, model cross-check, evolution review ("swap the base"), a staged migration-review spec (MR-1..MR-9), 17 publications (14 "verified"), recommendations, BibTeX | `WT2/docs/research/B3-dataspecer-update.md` (added in 40a5d5d) |
| Staged rebase (B3 rec. B3/A4) | `rebase` split into preview (plan, nothing changes), apply (with choices; defaults otherwise), cancel; one pending plan; a plan computed on a changed state is refused; a pending plan blocks release | `B/engine/pipeline.py:726-903`; `B/contracts.py:635-700`; `B/api/app.py:402-446`; `frontend/src/App.tsx:64-112`; `docs/dcat-versions.md:205-259` |
| Typed choices per finding | `keep`, `withdraw`, `replace`, `manual`, `repropose`, `keep_claim`; default preselected; on a human-decided change the default is `keep`/`manual` | `B/contracts.py:635,638-670`; `B/engine/rebase.py:80-87` |
| Legality split of `base_changed` (rec. B4, in part) | still legal: `keep`; no longer legal: `manual`/`withdraw` (two-way, not B3's five-way split) | `B/engine/rebase.py:115,130-142` |
| New findings | `covered_claim_weakened`, `intake_changed` | `B/contracts.py:659-660`; `B/engine/rebase.py:192-217` |
| Not adopted from Dataspecer/B3 | dependencies (`depends_on`), text decisions (`base_text_changed`), new-base-element items, `dsv_target_changed`, Dataspecer's "skip" | no such field or finding in `B/contracts.py:638-670`; `_facet_text` compares obligation, cardinality, range only (`B/engine/rebase.py:32-36`) |
| DAP oracle (rec. A1) and extractor fix (rec. B1) | Dataspecer DCAT 2/3 DSVs vendored as test fixtures (MIT, mff-uk/specifications @833685e) | `WT2/tests/fixtures/dap/{README.md,LICENSE}`; `WT2/tests/test_dcat_model_vs_dap.py:46-61` |
| Version-unambiguous DSV (rec. B2, in part) | DSV names the base release (shape URLs or archives, homepage) and the DCAT TR with `dct:conformsTo`; `prof:isProfileOf` is never a relative IRI | `B/compile/linkml_dsv.py:131-145` |
| Not implemented | A2 (2.1.1 DSV index), A3 (DAP fallback), B6, B7; only 3.0.1 has a `dsv-index.json` | `B/data/base-profiles/dcat-ap-3.0.1/dsv-index.json` (only one) |
| Keys | an OpenAI-compatible key is bound to the origin (scheme, host, port) it was entered for | `B/llm/registry.py:26-79,118`; `B/api/app.py:140-143,208-217`; `frontend/src/App.tsx:130-136` |
| Blind projects | snapshot and export drop atom sources, counterfactual markers and hints; atom inspector hides source and counterfactual | `B/engine/pipeline.py:644-648`; `B/api/app.py:494-509`; `frontend/src/Inspector.tsx:112-113`; `B/contracts.py:623-625` |
| Release state | release needs no pending plan, an empty queue, a conformance report and every stage current; settings, title or atom changes mark stages stale and withdraw a release (artefacts recompiled) | `B/engine/pipeline.py:120-181`; `B/api/app.py:294-333` |
| Metrics | `rejected_by_human`, `withdrawn_by_machine`, `extension_rate_proposed`, `repair_calls`, `repaired_and_included`, `judge_calls` | `B/engine/pipeline.py:601-641` |
| Stage order | verify -> consolidate -> repair | `B/contracts.py:106-109`; `frontend/src/api.ts:159` |

## 2. Claims of the tool session (this area), checked

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | B3 "has the verified related work (14 entries with BibTeX)" | **partly** | 14 entries counted as verified (B3:482-500) and 14 BibTeX blocks (B3:552-694). "Verified" there means search-index records, because publisher pages were unreachable (B3:26, 478). Three entries carry open fields already in B3 (P2 DOI, P6 DOI, P7 volume and issue: B3:500). In this session: R3's DOI (LDkit) was not found anywhere and no published version was seen; P6's DOI comes from one record; T1's author field is reported inconsistently by two search summaries (section 3). |
| 2 | "they key on IRIs, we key on terms" | **confirmed** (theirs: code at ece634b; "id = IRI" is B1's reading) | Dataspecer's diff pairs entities by id: created / changed (deep-equal) / deleted (`DS@ece634b packages/core/src/entity-model/diff.ts:9-40`, fetched). That imported ids are IRIs is B1 1.2.1 (B3:289), not re-checked: verify. Ours: old and new base element looked up by (target class, path) (`B/engine/rebase.py:110-115`); stated in `docs/dcat-versions.md:257`. |
| 3 | "they do no refinement checking" | **confirmed as far as checkable here** | At ece634b, `cardinalityDecision` returns `override-differs` with choices `keep-own`/`adopt-new` and default `keep-own`, with no comparison of the kept value against the new bounds (`evolution-items.ts:685-734`, fetched; no "legal", "refine", "narrow" or "InvalidTermProfile" in the file). The search of all 86 branches is B3 §4 (B3:244-256), another session's code reading. The paper's "as we read its code" stays. |
| 4 | "their review screen inspired our staged rebase plan" | **confirmed** | Stated in the code and docs (`B/contracts.py:638-642`; `B/engine/rebase.py:16-21`; `docs/dcat-versions.md:255-259`). Implemented: preview `B/engine/pipeline.py:739-756`, cancel `:758-763`, apply `:765-891` (stale plan refused `:772-773`), defaults `B/engine/rebase.py:80-87`, release blocked while a plan is pending `B/engine/pipeline.py:168-169`. Differences to Dataspecer: no dependencies, texts not compared, new base elements never proposed, repair not run after apply (`B/engine/pipeline.py:876-878`). |
| 5 | (tool docs) "a value the new base makes illegal is never kept by default" | **partly** | True for `base_changed` (`B/engine/rebase.py:130-142`). Not for `now_in_base`: legality is computed (`:115`) but not used there (`:116-124`). Probe (`now_in_base_probe.py`): a machine change on `dcat:DataService dcterms:publisher` with max 3, made on 2.1.1; 3.0.1 defines the element with max 1. The plan item reads `now_in_base`, info, choices keep/manual, **default keep**, "the change now tightens it". After apply, re-verification gives V3 error "max_count 1 -> 3 (loosens the base)" and the change goes to `needs_review` (rule:policy). The end state is safe for machine changes; the plan text is not. |
| 6 | (blind section, UI part) "the workbench hides sources from the reviewer" | **confirmed** for snapshot, export and atom inspector | `B/engine/pipeline.py:644-648`; `B/api/app.py:494-509`; `frontend/src/Inspector.tsx:112-113`. Default `blind: False` (`B/contracts.py:625`), so the synthetic demo still shows sources. |

Also confirmed (B3-derived, other area): our DCAT models against the Dataspecer DAP fixtures. DCAT 3: 89 ours, 89 theirs, 89 shared.
DCAT 2: 76 ours, 74 theirs, 74 shared; the 2 extra pairs are the documented `dcat:DataService` `dct:license`/`dct:accessRights`
(`dap_pairs.py`; `WT2/tests/test_dcat_model_vs_dap.py:19-27,46-61`).

## 3. The 14 "verified" entries of B3 (§6, §9)

How checked in this session: **F** = file fetched from raw.githubusercontent.com (the group's own records);
**S** = WebSearch result records (publisher, DBLP/researchr, CEUR listing, university repository), not opened.
"Checked" = identifiers and core fields seen in F, or in at least two S records.

| B3 # | Entry (B3 key -> paper key) | In `P/references.bib`? | Checkable here? How | Status |
|---|---|---|---|---|
| P1 | ESWC 2022 demo (`stenchlak2022dataspecer`) | **yes**, `references.bib:847-858` | F: DS `CITATION.cff:42-90` (authors, editors, title "DataSpecer: ...", LNCS 13384, pp. 52-56, Springer, 2022, DOI 10.1007/978-3-031-11609-4_10); S: unpaywall record of the DOI, dblp1 `conf/esws/StenchlakN0K22`, the ESWC 2022 PDF | **checked**. The paper's title casing `{Dataspecer}` differs from the authors' record `DataSpecer` (CITATION.cff:79). |
| P2 | Atlas, MODELS-C 2023 (`klimek2023atlas`) | no | S: dblp `conf/models/KlimekK0BSNH23` (7 authors, "MoDELS (Companion) 2023: 4-8"), proceedings.com table of contents (Tools and Demonstrations, p. 4); F: the DOI 10.1109/MODELS-C59198.2023.00009 only as a link on the project site (`index.html:99`) | **checked except the DOI** (verify DOI) |
| P3 | Stenchlák, ER 2023 DC (`stenchlak2023framework`) | no | S: CEUR listing `ceur-ws.org/Vol-3618/dc_paper_1.pdf` (title, author, ER 2023 Companion, Doctoral Consortium, Lisbon), Charles Explorer record | **checked**; new: paper id `dc_paper_1` (B3:484 "paper number not seen") |
| P4 | ISWC 2024 demo (`klimek2024authoring` -> `klimek2024dataspecer`) | **yes**, `references.bib:835-844` | F: `index.html:89-94` (CEUR Vol-3828 paper33 URL, Best Demo award), `iswc2024.md:6` (title); S: CEUR listing (5 authors) | **checked** |
| P5 | ER 2024 LLM assistant (`prokop2024enhancing` -> `prokop2024assistant`) | **yes**, `references.bib:864-875` | S: Springer chapter record (DOI 10.1007/978-3-031-75872-0_13, "Published: 21 October 2024", Springer Cham, print ISBN 978-3-031-75871-3), OUCI record, KSI entry, starfos record (pp. 235-253) | **checked**; year 2024 settled (publication date); LNCS volume 15238 not re-seen (from the earlier session's book-page search): verify volume only |
| P6 | DSV paper, iiWAS 2025 (`klimek2025dsv`) | no (the paper cites the vocabulary, `klimek2026dsv`) | S: researchr `KlimekSS25` (iiWAS 2025, LNCS 16330, pp. 221-236, Springer chapter link 10.1007/978-3-032-11976-6_16); KSI listing (title only). A search for the DOI string finds nothing | **verify** (venue, pages and DOI from one record) |
| P7 | SWJ 2026 journal paper (`stenchlak2026dataspecer`) | **no** | F: `index.html:82-85` (title; link doi.org/10.1177/22104968261479880; "published in the Semantic Web journal"); S: KSI publication page (authors; Semantic Web 17(5); article number 22104968261479880; DOI), SWJ review pages | **checked**; volume 17, issue 5 from one record: verify those two fields |
| R1 | Klímek 2019, JWS (`klimek2019dcatap`) | no | S: X-MOL record (DOI 10.1016/j.websem.2018.11.001, online 2018-11-16), dblp1 `journals/ws/Klimek19`, KSI bib, starfos (vol. 55, pp. 69-85) | **checked** |
| R2 | Nečaský et al. 2012, JSS (`necasky2012evolution`) | no | S: Bohrium record (authors, JSS, March 2012, DOI 10.1016/j.jss.2011.09.038), starfos RIV record, Holubová's habilitation thesis (includes the paper) | **checked except volume 85(3) and pages 683-707** (verify) |
| R3 | LDkit, SWJ 2026 (`klima2026ldkit`) | no | S: SWJ submission and review pages (Klíma, Taelman, Nečaský; "major revision" April 2025); **no record of DOI 10.1177/22104968251404248 and no published version found** | **verify** (B3:494 "verified (SAGE page)" not reproducible here) |
| T1 | Prokop 2024, master thesis (`prokop2024thesis`) | no | S: dspace record 20.500.11956/193876 (EN/CZ title, defended 11 Sep 2024). One summary names Dominik Prokop as author (advisor Nečaský, consultant Stenchlák); another names Stenchlák | **checked except the author field** (verify) |
| T2 | Ulianov 2026, master thesis (`ulianov2026thesis`) | no | S: dspace record 20.500.11956/207052 (title) and its PDF ("MASTER THESIS Bc. Egor Ulianov ..."), defended 10 Feb 2026 | **checked** (department and supervisor not seen) |
| S1 | DSV vocabulary 1.0.0 (`dsv2025`) | equivalent entry `klimek2026dsv` (1.0.1), `references.bib:881-888` | F: DSV `CITATION.cff` (version 1.0.0, released 2025-05-13, url w3id.org/dsv, 3 authors) | **checked**; keep `klimek2026dsv` (1.0.1, the ontology's own `dct:bibliographicCitation`); the CITATION.cff still says 1.0.0 |
| S2 | Dataspecer software (`dataspecer_software`) | no | F: DS `CITATION.cff:1-41` (12 authors, MIT, repository URL) | **checked**; not needed: its preferred citation is P1 (`CITATION.cff:42`) |

The 3 entries B3 lists as unverified (P8 ISWC 2026 change-propagation demo, P9 iiWAS 2026 multiprofiling, P10 ER 2023
landing page) stay **verify**. P8 and P9 are announced on the project site (`index.html:70-79`, F); no proceedings
record was found (S).

## 4. BibTeX for checked entries

Paper keys where the paper has one. Recommended for the paper: **`stenchlak2026dataspecer`** (the group's journal
paper on the tool the paper compares with) and, optionally, **`ulianov2026thesis`** (the closest LLM work in the
Dataspecer ecosystem, B3:496). The others are listed for completeness; the paper does not need them.

```bibtex
% [F] dataspecer/dataspecer CITATION.cff preferred-citation (l.42-90), fetched 14 Nov 2026; [S] unpaywall record of
% the DOI, dblp conf/esws/StenchlakN0K22. Title casing as in the authors' record. (Already in references.bib.)
@inproceedings{stenchlak2022dataspecer,
  author    = {Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and Ne{\v{c}}ask{\'y}, Martin and {\v{S}}koda, Petr and Kl{\'\i}mek, Jakub},
  title     = {{DataSpecer}: A Model-Driven Approach to Managing Data Specifications},
  booktitle = {The Semantic Web: ESWC 2022 Satellite Events},
  series    = {Lecture Notes in Computer Science},
  volume    = {13384},
  pages     = {52--56},
  publisher = {Springer, Cham},
  year      = {2022},
  doi       = {10.1007/978-3-031-11609-4_10}
}

% [F] dataspecer/dataspecer www/layouts/index.html l.82-85 (title, doi.org link), fetched 14 Nov 2026; [S] KSI
% publication page (authors; Semantic Web 17(5), article 22104968261479880; DOI); SWJ review pages.
@article{stenchlak2026dataspecer,
  author  = {Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and Kl{\'\i}mek, Jakub and {\v{S}}koda, Petr and Ne{\v{c}}ask{\'y}, Martin},
  title   = {{Dataspecer}: Development of Consistent Semantic Data Specification Ecosystems},
  journal = {Semantic Web},
  volume  = {17},
  number  = {5},
  year    = {2026},
  doi     = {10.1177/22104968261479880},
  note    = {verify: volume and issue seen in one record only}
}

% [S] dspace.cuni.cz handle 20.500.11956/207052: record (title) and thesis PDF (title page "MASTER THESIS Bc. Egor
% Ulianov"); defence date 10 Feb 2026 in the search summary. Content: abstract only.
@mastersthesis{ulianov2026thesis,
  author = {Ulianov, Egor},
  title  = {Context-Enriched Prompting Strategies for Automated Data Specification Adjustment in {Dataspecer} Using {LLMs}, {RAG} and {MCP}},
  school = {Charles University, Faculty of Mathematics and Physics},
  year   = {2026},
  url    = {https://dspace.cuni.cz/handle/20.500.11956/207052},
  note   = {Master's thesis, defended 10 February 2026}
}

% [F] index.html l.89-94 (CEUR URL; Best Demo award), iswc2024.md l.6 (title); [S] CEUR listing (5 authors).
% (Already in references.bib; unchanged.)
@inproceedings{klimek2024dataspecer,
  author    = {Kl{\'\i}mek, Jakub and Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and Polick{\'y}, Adam and {\v{S}}koda, Petr and Ne{\v{c}}ask{\'y}, Martin},
  title     = {Towards Authoring of Vocabularies and Application Profiles using {Dataspecer}},
  booktitle = {{ISWC} 2024 Posters, Demos and Industry Tracks: From Novel Ideas to Industrial Practice},
  series    = {CEUR Workshop Proceedings},
  volume    = {3828},
  year      = {2024},
  url       = {https://ceur-ws.org/Vol-3828/paper33.pdf}
}

% [S] Springer chapter record (DOI; published 21 October 2024; Springer, Cham; print ISBN 978-3-031-75871-3), OUCI,
% KSI, starfos (pp. 235-253). Volume 15238 from the earlier session's book-page search, not re-seen.
% (Already in references.bib; unchanged except the note.)
@inproceedings{prokop2024assistant,
  author    = {Prokop, Dominik and Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and {\v{S}}koda, Petr and Kl{\'\i}mek, Jakub and Ne{\v{c}}ask{\'y}, Martin},
  title     = {Enhancing Domain Modeling with Pre-trained Large Language Models: An Automated Assistant for Domain Modelers},
  booktitle = {Conceptual Modeling -- ER 2024},
  series    = {Lecture Notes in Computer Science},
  volume    = {15238},
  pages     = {235--253},
  publisher = {Springer, Cham},
  year      = {2024},
  doi       = {10.1007/978-3-031-75872-0_13},
  note      = {verify: LNCS volume}
}

% [S] dblp conf/models/KlimekK0BSNH23 (authors, pp. 4-8); proceedings.com table of contents (Tools and Demonstrations,
% p. 4). Not needed by the paper.
@inproceedings{klimek2023atlas,
  author    = {Kl{\'\i}mek, Jakub and Koupil, Pavel and {\v{S}}koda, Petr and B{\'a}rt{\'\i}k, J{\'a}chym and Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n and Ne{\v{c}}ask{\'y}, Martin and Holubov{\'a}, Irena},
  title     = {Atlas: A Toolset for Efficient Model-Driven Data Exchange in Data Spaces},
  booktitle = {2023 ACM/IEEE International Conference on Model Driven Engineering Languages and Systems Companion (MODELS-C)},
  pages     = {4--8},
  year      = {2023},
  note      = {verify: DOI 10.1109/MODELS-C59198.2023.00009 is linked from the project site only}
}

% [S] CEUR listing ceur-ws.org/Vol-3618/dc_paper_1.pdf; Charles Explorer record. Not needed by the paper.
@inproceedings{stenchlak2023framework,
  author    = {Stenchl{\'a}k, {\v{S}}t{\v{e}}p{\'a}n},
  title     = {A framework for data specification modeling in complex domains},
  booktitle = {Companion Proceedings of the 42nd International Conference on Conceptual Modeling (ER 2023), Doctoral Consortium},
  series    = {CEUR Workshop Proceedings},
  volume    = {3618},
  year      = {2023},
  url       = {https://ceur-ws.org/Vol-3618/dc_paper_1.pdf}
}

% [S] X-MOL (DOI), dblp journals/ws/Klimek19, KSI bib, starfos (vol. 55, pp. 69-85). Not needed by the paper.
@article{klimek2019dcatap,
  author  = {Kl{\'\i}mek, Jakub},
  title   = {{DCAT-AP} representation of {Czech} National Open Data Catalog and its impact},
  journal = {Journal of Web Semantics},
  volume  = {55},
  pages   = {69--85},
  year    = {2019},
  doi     = {10.1016/j.websem.2018.11.001}
}

% [S] Bohrium record (authors, journal, March 2012, DOI), starfos RIV record. Not needed by the paper.
@article{necasky2012evolution,
  author  = {Ne{\v{c}}ask{\'y}, Martin and Kl{\'\i}mek, Jakub and Mal{\'y}, Jakub and Ml{\'y}nkov{\'a}, Irena},
  title   = {Evolution and change management of {XML}-based systems},
  journal = {Journal of Systems and Software},
  year    = {2012},
  doi     = {10.1016/j.jss.2011.09.038},
  note    = {verify: volume 85(3) and pages 683--707 (B3) not seen in this session}
}

% [S] dspace.cuni.cz 20.500.11956/193876 (title, defence 11 Sep 2024). Not needed by the paper.
@mastersthesis{prokop2024thesis,
  author = {Prokop, Dominik},
  title  = {Using large language model as an assistant for conceptual modeling},
  school = {Charles University, Faculty of Mathematics and Physics},
  year   = {2024},
  url    = {https://dspace.cuni.cz/handle/20.500.11956/193876},
  note   = {Master's thesis, defended 11 September 2024. verify: author field (two search summaries disagree)}
}
```

S1 and S2 are checked (F) but should not be added: `klimek2026dsv` already covers DSV (and is the newer 1.0.1),
and the software's preferred citation is P1. **verify, no BibTeX from this session:** P6 `klimek2025dsv`, R3 `klima2026ldkit`
(and P8-P10).

## 5. Comparison with the paper and the earlier digest

### 5.1 What the paper says now (5ffd56e text)

- Sect. 1 `P/sections/01-introduction.tex:34-36`: Dataspecer generates DSV and SHACL from profiles of profiles and,
  "by our reading of its code, does not check that their cardinalities and ranges refine the base". This is still
  consistent with B3 §4 (B3:68, 244-256) and with `evolution-items.ts:685-734`.
- Sect. 2 `P/sections/02-related-work.tex:23-26`: "neither derives them from requirements nor checks refinement of the
  base. Its review of base updates for dependent profiles is the closest pattern we found for machine proposals that a
  person decides". This is consistent, but at 21c6b5b it understates the link: the rebase now follows that review
  (preview, typed choices, defaults, apply or cancel).
- Sect. 4.4 `P/sections/04-pipeline.tex:107-111`: describes the one-step rebase of 5ffd56e (compare, flag, check again).
  At 21c6b5b it is staged (section 1).
- Sect. 8 `P/sections/08-discussion.tex:101-108`: one base; DSV maps bounds onto four cardinalities; no authentication,
  self-asserted reviewer, anyone who reaches the server can use the key. All still true at 21c6b5b (section 6).

### 5.2 Against the earlier digest `digests/conformance-dataspecer.md`

- §3.6 (no refinement checking) and §6 item 15 (code-reading claims at a pinned commit): unchanged. B3 extends the
  search to all 86 branches (B3:249) and adds the evolution case: an override that the new base makes illegal is kept
  by default (B3:251; re-confirmed at `evolution-items.ts:685-734`).
- §3.8 (LLM features): B3 confirms that there are none on `main` and on any branch apart from a link to an external
  assistant (B3:109, 115). The group's LLM work is P5 and T2 (B3:69).
- §3.9 (evolution review; "verify: title and venue of that ISWC 2026 paper"): still verify (P8). The project site
  says it "will be presented at the ISWC 2026 Posters and Demos session" (`index.html:70-73`, F).
- §6 item 14 (DSV export: no wrapper; DCAT-AP term profiles only on 3.0.1): still true at 21c6b5b. New: the DSV now
  names the base release and its DCAT (`B/compile/linkml_dsv.py:131-145`).
- Bibliography digest open points: SWJ paper (P7) is now confirmed by the project site plus KSI. Prokop year: 2024
  (chapter published 21 Oct 2024). DSV paper (P6): still verify.

### 5.3 What the paper should change (details in the table of section 9)

1. Sect. 2: cite P7 (`stenchlak2026dataspecer`) next to P1/P4. Say that the missing refinement check also holds for
   base updates, where the review keeps a profile's own value by default. Say that its review pairs elements by
   identifier, while ours pairs by vocabulary term and re-verifies, and that our staged rebase follows its review.
   Keep `\verify{Dataspecer: code reading only}`, adding the commit (ece634b).
2. Sect. 2 P3 (optional): one clause and `ulianov2026thesis` (LLM adjustment of Dataspecer specifications),
   marked verify (abstract only).
3. Sect. 1: add `stenchlak2026dataspecer` to the citation (no other change needed).
4. Sect. 4.4: describe the staged rebase. This overlaps the rebase/policy area; the A7/A8 todo should be settled there.
5. Sect. 8: keep the security sentence; update its source comment (the tool README's "another host" clause is outdated).
6. Figure: keep the screenshots; update the provenance comment (section 7).
7. references.bib: add P7 (and optionally T2); `stenchlak2022dataspecer` title casing `{DataSpecer}`; narrower notes.
8. README: update D1, D2, C9 and C10 (section 6), the bibliography verify list, and the demo-record source.
9. Do not use B3's quantitative Dataspecer findings (e.g. 6 removed and 33 added IRIs between their 2.1.1 and 3.0.1
   DSVs, B3:360) without a verify marker: they come from another session's scripts, which this session did not re-run.

## 6. README tool issues D1, D2, C9, C10 at 21c6b5b

| Id | Status at 21c6b5b | Evidence |
|---|---|---|
| D1 | **still present** (wider) | No authentication middleware (`B/api/app.py:1-75`; no `Depends`, no middleware). Every actor name is a request field: `by` in `DecisionRequest`, `RebaseRequest`, `RebaseApplyRequest` (new), `EditRequest`, `AssessmentOverride`, `SignOffRequest` (`B/api/app.py:105-138`), and the `by` query parameter of `DELETE .../rebase/{plan_id}` (`:426-433`). These names are recorded as `human:<by>` (`B/engine/pipeline.py:751,754,763,783`). Releases without a person are signed `rule:auto-release` when `require_human_signoff` is off (`:561-576`). |
| D2 | **changed in part** | (a) Keys: an OpenAI-compatible key now requires a base URL and is bound to its origin; `get` returns None for any other origin (`B/llm/registry.py:26-79`; used at `:118`; API `B/api/app.py:140-143,208-217`; UI `frontend/src/App.tsx:130-136`). Probe: same origin -> key; another host or port -> None; a provider built for another host carries no key. The server-side request itself remains possible, without the key, to any URL a user sets (`POST /api/llm/models`, `B/api/app.py:220-225`; `B/llm/openai_compatible.py:160-166`). (b) Development server: unchanged (`B/api/app.py:3`). (c) SPA path handler: **path traversal confirmed in memory**. An ASGI call with path `/../secret.txt` (or raw `/%2e%2e/secret.txt` decoded to it) returned 200 and the content of a file outside `FRONTEND_DIST` (`B/api/app.py:526-532`: `FRONTEND_DIST / path`, no resolve or containment check). Whether uvicorn delivers such a path unnormalised: verify with a live server. (d) `DELETE /api/projects/{id}` still takes no lock (`B/api/app.py:311-314`); the new rebase-plan DELETE does (`:426-433`). |
| C9 | **still present** | After a completed run without sign-off, the review stage is set to `running` (`B/engine/pipeline.py:557-559`), also after a rebase (`:890`) and on withdrawal (`:127`). The stepper prints "Review & sign-off" with that state (`frontend/src/App.tsx:8-10,233-240`). New: `skipped` after an automatic release (`B/engine/pipeline.py:557-559`). |
| C10 | **still present** | `B/llm/mock.py` is unchanged (`git diff 5ffd56e 21c6b5b` empty). The cue list contains "number of" (`:39`), but the cue is matched against the trimmed need phrase (`:90,177`), which drops stop words such as "of" (`:334-340`). In memory, `_information_needed("A dataset must state the number of specimens that were tested.")` gives `'number specimens'`, which maps to `xsd:string`; the full sentence would map to `xsd:integer`. The demo at 21c6b5b still mints `lab:numberSpecimens` as `xsd:string`. |
| (C5, aside) | still present | `WT2/README.md:95` "(70 tests)"; 170 pass (`P/inputs/tests-main-21c6b5b-2026-11-14.txt`). |
| (B3 issue, aside) | fixed for the DSV | `prof:isProfileOf` is never relative; release and DCAT named (`B/compile/linkml_dsv.py:131-145`). The `owl:imports` part belongs to the compile area. |

## 7. Workbench figure (`P/figures/workbench.tex`, screenshots taken at 5ffd56e)

**Not misleading for 21c6b5b.** The figure shows a canvas card and the change inspector, top and bottom, for
`lab:numberSpecimens`.
- Code: `frontend/src/Canvas.tsx` is unchanged. `Inspector.tsx` changed only in the atom view (`:112-113`: source and
  counterfactual hidden when `config.blind`), which is not in the figure. The App changes are the rebase panel, the model
  panel and the review-queue banner (`App.tsx:64-136,295-304`), none of which is in the figure.
- Content: the in-memory mock run of the demo gives the same result at both commits.
  - Run: same statuses, same 10 changes, conformant to 3.0.1, 25 calls (15 propose, 10 judge).
  - Figured mint: verbalisation, decision note "confidence 0.45 below 0.5", cover reason and quote, the four facet
    justifications, the reason for minting, the three rejected candidates with scores, and the checks V1 V2 D1 V3 V4 V5 T1 T2
    are byte-identical apart from the timestamp (`mint-main-wt*.json`).
  - Only the notes of auto-accepted changes gain "judged supported", and those notes are not in the figure.
- Blind projects: the demo is not blind (default `blind: False`), and the figure shows no source line.
- New metrics: the workbench's metric panel shows the same eight values as before (`Inspector.tsx:84-91`). The new
  metrics are not displayed, and the panel is not in the figure.
- Release state: the release panel code is unchanged (`App.tsx:313-319`) and is not in the figure. Withdrawal now
  recompiles the artefacts (`B/engine/pipeline.py:120-134`).
- Stage order: changed (verify, consolidate, repair; `B/contracts.py:106-109`), but the stepper is not in the figure.
- Action: change the provenance comment (`workbench.tex:1-4`). Either state that the content is identical at 21c6b5b
  (probe) or retake the screenshots at 21c6b5b. The caption stays true, including "xsd:string for a count" (C10).
- `P/README.md:75` demo numbers are unchanged at 21c6b5b: 15 atoms; 4/5/5/1; 10 changes, 5 auto-accepted, 5 in the queue;
  conformant to 3.0.1.
  - The metric keys changed: `rejected` -> `rejected_by_human` + `withdrawn_by_machine`, `repaired` -> `repair_calls` +
    `repaired_and_included`; new `extension_rate_proposed` = 0.5 and `judge_calls` = 10 (`demo-main-wt2.json`).
  - Add a 21c6b5b record to `P/inputs/` if the paper cites 21c6b5b.

## 8. New issues found at 21c6b5b

1. **SPA path traversal** (`B/api/app.py:526-532`). Confirmed by the in-memory ASGI probe; live uvicorn: verify.
   Confidence high (ASGI level).
2. **Rebase plan ignores legality for `now_in_base`** (`B/engine/rebase.py:115-124`). The plan says "the change now
   tightens it" with default `keep` for a change the new base makes illegal; re-verification after apply catches it.
   Contradicts `B/engine/rebase.py:19-20` and `docs/dcat-versions.md:259` at plan level. Confidence high (probe).
3. **Tool README security note partly outdated** (`WT2/README.md:97-99`). "including by pointing an OpenAI-compatible
   base URL at another host" no longer holds (keys bound to origins, `B/llm/registry.py:37-79`). Requests to any host,
   without the key, remain. Confidence high.
4. **`docs/design.md:33` outdated**. "machine changes with a migration finding go to `needs_review`" holds only for
   items applied as `manual` (`B/engine/pipeline.py:828-845`: withdraw `:828`, manual `:831`, replace `:834`): `keep` leaves the change, `withdraw` rejects it, and
   `replace` creates a proposed version. Confidence high.
5. **B3's statements about our tool are outdated** (documentation drift; B3:550 itself asks for a re-check):
   - finding 10, "base switches at once ... no batch apply and no cancel" (B3:70);
   - §2.2, "Our compiler writes only prof:isProfileOf" (B3:171);
   - §0.1/§3, the two extractor defects, now fixed (B3:63-67; `WT2/tests/test_dcat_model_vs_dap.py:55-61`);
   - §5.8 rows "Staging" and "Per-item choices" (B3:378-379).
   Confidence high.
6. **B3 bibliographic status overstated for R3** (B3:494). LDkit's DOI 10.1177/22104968251404248 and a published
   version were not found; B3 says "verified (SAGE page)". Confidence medium (absence of evidence).
7. **No Host or Origin check** (no middleware in `B/api/app.py`). "Run it on 127.0.0.1" (`WT2/README.md:97-98`) does
   not by itself stop DNS-rebinding access from a web page to an unauthenticated server. Not probed. Confidence low:
   verify.
8. **Workbench metric panel** (`frontend/src/Inspector.tsx:84-91`) shows none of the new metrics. "Decided by you"
   counts acceptances only, not human rejections. Low impact.

## 9. Paper impact

| File:line | Current (short) | Replacement fact | Anchor (21c6b5b unless stated) |
|---|---|---|---|
| `P/sections/02-related-work.tex:23-26` | "Dataspecer edits profiles of profiles ... \cite{stenchlak2022dataspecer,klimek2024dataspecer,klimek2026dsv}. As we read its code, it neither derives them from requirements nor checks refinement of the base. Its review of base updates ... is the closest pattern we found ..." | Add `stenchlak2026dataspecer` to the citation. Then: "As we read its code, it neither derives them from requirements nor checks refinement of the base, also not after a base update: its review pairs elements by identifier and, where a profile overrides a changed value, keeps the profile's value by default. Its items with preselected choices, applied or cancelled by a person, are the model of our staged rebase (Sect. 4.4), which pairs changes by vocabulary term and verifies them against the new base." Keep `\verify{Dataspecer: code reading only, commit ece634b}`. | DS@ece634b `packages/core/src/entity-model/diff.ts:9-40`, `packages/profile-model/src/hooks/evolution-items.ts:685-734` (fetched); B3:46, 68, 251, 289-305; `B/engine/rebase.py:16-21,110-142`; `B/contracts.py:638-642`; `docs/dcat-versions.md:255-259` |
| `P/sections/02-related-work.tex:10-12` (src comment) | "Dataspecer: docs/research/B1-dataspecer.md:28 and section 5 ..., :30 and :155-166 (evolution review ...)" | Add: "B3 (docs/research/B3-dataspecer-update.md, 21c6b5b) §4 (no refinement check on main or 85 other branches), §5.3-5.4 (entity-id diff; keep-own default), §5.8; Dataspecer ece634b diff.ts:9-40 and evolution-items.ts:685-734 re-read 14 Nov 2026". | B3:244-256, 287-332, 364-382 |
| `P/sections/02-related-work.tex:61` (optional) | "and assist domain modelers \cite{prokop2024assistant};" | "assist domain modelers \cite{prokop2024assistant} and adjust data specifications to changed sources with retrieval \cite{ulianov2026thesis}\verify{abstract only};" | dspace 20.500.11956/207052 (search record); B3:496 |
| `P/sections/01-introduction.tex:34-36` | "Dataspecer~\cite{stenchlak2022dataspecer,klimek2024dataspecer} generates ... does not check that their cardinalities and ranges refine the base." | Add `stenchlak2026dataspecer` to the citation. Optional: "... refine the base, neither when they are authored nor when the base is updated." | B3:68, 251; `evolution-items.ts:685-734` @ece634b |
| `P/sections/01-introduction.tex:40-44` (src comment) | "No claim about model features: the Dataspecer group's LLM work is separate (prokop2024assistant; digest :331-335)." | Add: "B3:69, 109, 115: no LLM code on main or any branch apart from a link to an external assistant; LLM work in P5 and a 2026 master thesis (T2)". | B3:69, 109, 115, 496 |
| `P/sections/04-pipeline.tex:107-111` | "A rebase moves the extension onto another release and its DCAT. Every change is compared under both bases; human decisions stay, machine changes with a finding that asks for a decision are flagged for review, and the extension is checked again, withdrawing the sign-off." | "A rebase moves the extension onto another release and its DCAT in two steps, after Dataspecer's review of base updates. A preview compares every change and atom under both bases and lists each finding with choices and a preselected default; nothing changes until a person applies the plan or cancels it, and a pending plan blocks release. Applying it switches the base, runs intake, retrieval, the chosen re-proposals, verification, consolidation, compilation and conformance again, and withdraws the sign-off; human decisions stay." Settle the A7/A8 todo with the rebase/policy area. | `B/engine/rebase.py:90-218`; `B/engine/pipeline.py:168-169,739-891`; `B/contracts.py:635-700`; `B/api/app.py:402-446`; `docs/dcat-versions.md:205-259` |
| `P/sections/04-pipeline.tex:100` (src comment) | "% src: @5ffd56e frontend/src/App.tsx:203-207, 241, 302" | Same text. Anchors: `frontend/src/App.tsx:233-242` (stepper, Run all), `:270-273` (tabs), `:333-335` (conformance) | 21c6b5b |
| `P/sections/08-discussion.tex:105-106` (src comment) | "@5ffd56e B/contracts.py:656, B/compile/linkml_dsv.py:113-116" | Text unchanged (one base; four DSV cardinalities). Anchors: `B/contracts.py:706`; `B/compile/linkml_dsv.py:113-116` | 21c6b5b |
| `P/sections/08-discussion.tex:107-108` | "The workbench is a local research prototype without authentication: the reviewer's name is self-asserted and anyone who reaches the server can use the key entered there ..." | Still true. Optional precision: "can run projects with the key entered there". Source: `B/api/app.py:105-138,402-433` (self-asserted `by`, also for rebase plans); `B/llm/registry.py:37-79` (a key is sent only to the origin it was entered for). Note that `README.md:97-99` (tool) has an outdated "another host" clause. | 21c6b5b |
| `P/figures/workbench.tex:1-4` (comment) | "retaken on 14 Nov 2026 at commit 5ffd56e (the tool the paper describes; frontend built from that commit)" | "taken at 5ffd56e; at 21c6b5b the components shown are unchanged and an in-memory mock run gives identical content for every element shown (statuses, notes, justifications, candidates, checks). Retake at 21c6b5b if the figure must come from the described commit (verify)". | `git diff 5ffd56e 21c6b5b -- frontend/src/Inspector.tsx` (only `:112-113`); probe `mint-main-wt*.json` |
| `P/figures/workbench.tex:19-24` (caption) | "... the choices shown are a lexical baseline's (\term{xsd:string} for a count) ..." | No change; still true at 21c6b5b. | `B/llm/mock.py:39,90,177,334-340` (file unchanged) |
| `P/references.bib:847-858` | `title = {{Dataspecer}: A Model-Driven Approach ...}`, note "verify: identifiers checked through search results only" | `{DataSpecer}` as in the authors' record. Note: "[F] project CITATION.cff preferred-citation; [S] unpaywall, dblp; publisher page not reachable". | DS `CITATION.cff:42-90` (fetched, sha256 9f8efecf...) |
| `P/references.bib:835-844` | `klimek2024dataspecer`, note "verify: identifiers checked through search results only" | Fields unchanged. Note: "[F] project site (CEUR URL, Best Demo) and demo page (title); [S] CEUR listing". | DS `www/layouts/index.html:89-94`; `www/content/en/papers/iswc2024.md:6` |
| `P/references.bib:860-875` | `prokop2024assistant`; comment "One search summary says ... datePublished 2025" | Year 2024 settled: chapter "Published: 21 October 2024" (Springer chapter record, search). Remaining verify: LNCS volume 15238. | search record link.springer.com/chapter/10.1007/978-3-031-75872-0_13 |
| `P/references.bib` (new entry) | (none) | Add `stenchlak2026dataspecer` (BibTeX in section 4); optionally `ulianov2026thesis`. | DS `www/layouts/index.html:82-85`; KSI page (search) |
| `P/README.md:197-199` | three bib entries "verify: identifiers checked through search results only" | `stenchlak2022dataspecer`: confirmed by the project's CITATION.cff (fetched) + search. `klimek2024dataspecer`: confirmed by the project site (fetched) + CEUR listing. `prokop2024assistant`: DOI and date confirmed by the Springer chapter record in search results; volume verify. Publisher pages still unreachable. | section 3 |
| `P/README.md:102` | "`sections/02-related-work.tex:26`: Dataspecer: code reading only" | Keep. Add "(commit ece634b; diff.ts and evolution-items.ts re-read 14 Nov 2026)". | section 0 |
| `P/README.md:75` | demo numbers, source `inputs/demo-materials-testing-lab-2026-11-14.json` | Same numbers at 21c6b5b (15; 4/5/5/1; 10 changes, 5 + 5; conformant). Add a 21c6b5b record. Metric keys renamed (section 7). | `scratchpad/related-delta-probe/demo-main-wt2.json` |
| `P/README.md:384` (C9) | "...`B/engine/pipeline.py:425-426,608`; `frontend/src/App.tsx:204,208`" | Still present. Anchors: `B/engine/pipeline.py:557-559,890,127`; `frontend/src/App.tsx:8-10,233-240`. New state `skipped` after an automatic release. | 21c6b5b |
| `P/README.md:385` (C10) | "The mock provider's datatype cue misses 'number of' ... `B/llm/mock.py:319,334`" | Still present (file unchanged). Mechanism: the cue list has "number of" (`:39`), but it is matched against the trimmed phrase without "of" (`:90,177,334-340`). | `B/llm/mock.py` |
| `P/README.md:392` (D1) | "No authentication. The reviewer name is self-asserted, including on the new rebase endpoint ... `B/api/app.py:111-114,370-380`" | Still present. Also on rebase preview, apply and cancel. Anchors: `B/api/app.py:105-138,402-446`; `B/engine/pipeline.py:751,754,763,783`. | 21c6b5b |
| `P/README.md:393` (D2) | "A user-set `base_url` (SSRF); a development server; the SPA path handler (verify path traversal); DELETE without a lock. `B/api/app.py:281-284,452-455`" | Keys bound to their origin (fixed part); requests to a user-set host without the key remain (`B/api/app.py:220-225`; `B/llm/openai_compatible.py:160-166`). Development server unchanged (`:3`). SPA traversal confirmed in memory (`:526-532`; live server verify). Project DELETE without lock (`:311-314`). | `B/llm/registry.py:26-79,118`; probes |
