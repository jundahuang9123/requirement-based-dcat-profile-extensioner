# RQ2 paper draft

Draft of the RQ2 paper, the companion of the RQ1 paper (ESWC 2027 submission):
**"Trace-Verified Profile Modeling for DCAT-AP Extensions with LLMs"** (running head "Trace-Verified Changes for
DCAT-AP Extensions"; the title is open, Q10). Springer LNCS (`llncs`), anonymous.

It uses the same skeleton and voice as RQ1, with a different narrative. RQ1 turns documents into requirement atoms.
RQ2 turns the atoms into a DCAT-AP extension that meets four criteria:
- **E1**: reuse first, and minimal.
- **E2**: every change is traced to a verbatim quote, and its obligation is licensed by the atom's modality.
- **E3**: the model decides most changes, every decision can be inspected and overruled, and only a person releases.
- **E4**: the extension conforms to its base DCAT-AP release, inside the DCAT state that release builds on.

**State.** This is a full draft with placeholders.
- The method sections describe the extensioner at `main` commit `5ffd56e` (DCAT-state pinning, nine DCAT-AP bases,
  rebase). That commit is **not** merged into this branch (Q14).
- The main evaluation does not exist yet. Its numbers print as a red **?** (`\tbd`, `\res{}{}{}`).
- The development runs made so far are contaminated (see "Where every number comes from") and appear only as a
  debugging history in Appendix C.1.

<!-- sections below: build, generated inputs, local-only material, files, number provenance, open markers,
     questions, tool issues, RQ1 mapping, how the draft was made -->

## Build

```bash
# TeX Live with llncs and latexmk (Ubuntu 24.04 packages used for this draft):
sudo apt-get install texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-science \
  texlive-publishers texlive-pictures texlive-fonts-recommended texlive-bibtex-extra latexmk lmodern
cd paper
latexmk -pdf main.tex          # -> main.pdf (bibtex with splncs04; acronyms need the usual extra passes)
latexmk -c                     # clean auxiliary files
```

Generated inputs. Run each command from the repository root. None of them calls a model.

| Command | Writes | From |
|---|---|---|
| `python paper/scripts/make_pilot_tables.py` | `paper/results/pilot-numbers.tex` (`\pilot{}{}{}`, `\pilotkind{}{}{}`), `paper/tables/pilot-runs.tex` | `paper/inputs/pilot-runs-2026-11-13.md`, `paper/inputs/dev-runs-2026-11-14-run3.md` |
| `python paper/scripts/check_pilot_macros.py paper` | prints mismatches (expected: 176 values, 0 mismatches) | the same two files, parsed independently |
| `python paper/scripts/tool_facts.py [REPO_ROOT] > paper/inputs/tool-facts*.txt` | tool counts (vocabularies, index size, base elements, obligations, tests) | the code at `REPO_ROOT` (default: this checkout; `tool-facts-main-5ffd56e.txt` was made from a worktree of `main`) |
| `python paper/scripts/list_markers.py` | the "Open markers" block of this README | the `.tex` sources and `references.bib` |

**Local-only material.** `paper/sections/local/` is gitignored.
- If `paper/sections/local/qualitative-examples.tex` exists, Appendix C.2 includes it. The file holds examples of
  atoms and the changes generated for them, which restate reference content. Without it, a TODO marker prints there.
- The committed `main.pdf` is built without it. The version with the examples was shared in chat only, as agreed.

## Files

| Path | What |
|---|---|
| `main.tex` | preamble, title, section inputs; markers `\todo{}`, `\verify{}`, `\tbd` (dark red, as in RQ1) |
| `acronyms.tex` | `\acrodef` list (expansions as printed in the RQ1 PDF; keys to check against RQ1's `main.tex`, Q1) |
| `sections/00-abstract.tex` ... `09-conclusion.tex` | the body, one file per section |
| `sections/10-statements.tex` | Supplementary Material Statement, Use of Generative AI |
| `sections/11-appendix.tex`, `sections/12-appendix-cd.tex` | Appendices A-B and C-D |
| `figures/*.tex` | TikZ figures (pipeline, reference flow, results frame) and the workbench figure |
| `figures/wb-*.png` | screenshots of the synthetic demo `examples/materials-testing-lab`, made with the offline rules provider |
| `tables/pilot-runs.tex`, `results/pilot-numbers.tex` | generated (see above) |
| `results/main-numbers.tex` | `\res{scope}{condition}{measure}`: prints `\tbd` until the RQ2 evaluator writes the definitions |
| `references.bib` | the RQ1 bibliography (`inputs/rq1-bibliography.2026-11-11a.bib`, 62 entries, keys unchanged), the companion placeholder `anon2027rq1`, then 26 RQ2 additions |
| `inputs/` | numbers-only run records, tool facts, the synthetic demo run, the RQ1 bibliography, the run script of the development runs |
| `scripts/` | generators and checks (above) |

## Where every number comes from

Every number in the paper either comes from one of these files or is a red `?`/`[verify: ...]`.

| Numbers | Source | How they reach the text |
|---|---|---|
| Development runs (Appendix C.1, Table `tab:pilot`) | `inputs/pilot-runs-2026-11-13.md` (rules baseline, runs 1-2), `inputs/dev-runs-2026-11-14-run3.md` (run 3) | `scripts/make_pilot_tables.py` → `\pilot{case}{run}{field}`; checked by `scripts/check_pilot_macros.py` (176 values, 0 mismatches) |
| Tool counts used in the method (12 vendored vocabularies, 11,599 triples, 926-933 index terms per base, nine bases with class/element/obligation counts, 98 tests) | `inputs/tool-facts-main-5ffd56e.txt` (made from a read-only worktree of `main` at 5ffd56e) | typed in the text with a `% src:` comment |
| Tool counts of the engine that made the development runs (13 vocabularies incl. the DCAT 3 RDF, 912 terms with the 1.1 base, three bases) | `inputs/tool-facts.txt` | typed, `% src:` comment |
| Synthetic demo (Table `tab:criteria`, Fig. `fig:workbench`): 15 atoms; 4 covered by the base, 5 addressed, 5 pending review, 1 out of scope; 10 changes (5 auto-accepted, 5 in the review queue); conformant to DCAT-AP 3.0.1 | `inputs/demo-materials-testing-lab-2026-11-14.json` (mock provider, offline) | typed, `% src:` comment |
| Configuration defaults (top_k 8, three repair rounds, one vote, confidence threshold 0.5, four parallel calls) | `backend/profile_extensioner/contracts.py` (`PipelineConfig`; at 5ffd56e lines 589-602) | typed, `% src:` comment |
| Obligation mapping (must → mandatory, should → recommended, may → optional, unspecified → recommended) and ranks | `backend/profile_extensioner/contracts.py` (`MODALITY_OBLIGATION`, `OBLIGATION_RANK`) | typed, `% src:` comment |
| Literature steps: 99; 33 implemented, 30 partly, 36 planned; G1+G2 22/17/11 | `docs/literature-steps.md` (summary line and table; recounted by script for this draft) | typed; Table `tab:steps` |
| Atom counts of the development cases and the bases of the companion study | the RQ1 paper (Table 1 of the 13 Nov draft), cited as `\cite{anon2027rq1}` | typed; the RQ1 PDF is not committed |
| Main results | none yet | `\res{...}` → `?` |

The development runs are **contaminated**, so they are a debugging history and not results:
- Every prompt printed the atom's source reference, which names the target profile and section.
- The project title named the case.
- Run 2 replayed cached answers, and two code versions were involved.
- The runs used the engine before DCAT-state pinning (2b92d77; run 1 at about a52df71, verify).

No number from them appears in the abstract, the contributions or the conclusion. The test cases (Mobility, Geo,
Health) were not run, inspected or reported for this draft.

## Open markers

<!-- markers:begin -->

_Generated by `python paper/scripts/list_markers.py`; do not edit this block by hand._

**Counts.** 18 `\verify`, 72 `\todo`, 363 `\res` uses (330 distinct result slots), 15 direct `\tbd` cells, 6 bibliography entries with a printed verify note.

#### Verify items (`\verify{...}`)

- `sections/01-introduction.tex:39`: each ``none'' claim
- `sections/02-related-work.tex:26`: Dataspecer: code reading only
- `sections/03-problem.tex:26`: release quotes: DCAT version
- `sections/03-problem.tex:31`: release text: optional-field rule
- `sections/04-pipeline.tex:58`: blackboard source: released code only, no DOI (Q24, Q30)
- `sections/04-pipeline.tex:78`: LinkML output valid; opens in the profile editor
- `sections/04-pipeline.tex:80`: DSV output imports into Dataspecer
- `sections/04-pipeline.tex:105`: 1.1 and 1.2 record only the zip file's hash
- `sections/05-benchmark.tex:55`: 1.1 base, importer, recommended-minimum normalization added during development
- `sections/05-benchmark.tex:70`: share of unspecified modalities per case
- `sections/06-setup.tex:30`: endpoint defaults
- `sections/07-results.tex:103`: how each finding was found: prompts, probes or code
- `sections/08-discussion.tex:43`: StatDCAT-AP 1.0.0 only: recheck the reference version (Q3)
- `sections/08-discussion.tex:64`: OE-Assist finding: from the authors' slides
- `sections/08-discussion.tex:97`: how the leak was found: stored prompts or code
- `sections/12-appendix-cd.tex:112`: step-to-operation assignment (literature digest 1.4)
- `sections/12-appendix-cd.tex:121`: G3-S16, G3-S23 in part at the described commit
- `sections/12-appendix-cd.tex:122`: no DOI for chmielewski2026blackboard, cited from its code

#### TODO items (`\todo{...}`)

- `sections/00-abstract.tex:24`: reference deltas and conditions: final set (Q3, Q7)
- `sections/00-abstract.tex:25`: main results: Recovery and Strict of FP, RB, CB
- `sections/01-introduction.tex:22`: mobilityDCAT-AP example: keep or generic (Q17)
- `sections/01-introduction.tex:70`: conditions: final set (Q7)
- `sections/01-introduction.tex:81`: reference deltas: build, align, freeze before claiming (Q23)
- `sections/01-introduction.tex:84`: with results, say ``an evaluation''
- `sections/02-related-work.tex:28`: anonymized reference to the profile editor (Q25)
- `sections/04-pipeline.tex:24`: supplementary material: demo atom walk-through
- `sections/04-pipeline.tex:69`: tool: duplicates repaired; merged changes skip T2 (Q22)
- `sections/04-pipeline.tex:96`: tool: unresolved atoms do not block sign-off (Q22)
- `sections/04-pipeline.tex:110`: tool: rebase flags reset; lost coverage claims kept (Q22)
- `sections/04-pipeline.tex:111`: described commit not in the paper branch (Q14)
- `sections/04-pipeline.tex:115`: anonymized repository link
- `sections/05-benchmark.tex:16`: base and reference version per case (Q3)
- `sections/05-benchmark.tex:33`: Q3
- `sections/05-benchmark.tex:33`: Q3
- `sections/05-benchmark.tex:34`: Q3
- `sections/05-benchmark.tex:34`: Q3
- `sections/05-benchmark.tex:35`: Q3
- `sections/05-benchmark.tex:35`: Q3
- `sections/05-benchmark.tex:38`: Q3
- `sections/05-benchmark.tex:38`: Q3
- `sections/05-benchmark.tex:39`: Q3
- `sections/05-benchmark.tex:39`: Q3
- `sections/05-benchmark.tex:52`: test-case statement: confirm (Q18)
- `sections/05-benchmark.tex:54`: freeze: commit and tag
- `sections/05-benchmark.tex:62`: test-case atom counts: print? (Q11)
- `sections/05-benchmark.tex:70`: modality from the reference's obligation? (Q20)
- `sections/05-benchmark.tex:73`: extracted atoms: run, conversion, in or out (Q21)
- `sections/05-benchmark.tex:83`: reference deltas: source and construction (Q23)
- `sections/05-benchmark.tex:86`: alignment and hand extraction: who, agreement (Q9)
- `sections/05-benchmark.tex:101`: adjudicator and agreement (Q9)
- `sections/05-benchmark.tex:101`: evaluator: not built
- `sections/06-setup.tex:12`: closed book: probe script and variant (Q7)
- `sections/06-setup.tex:22`: conditions: names; SX, TC, TR, HR (Q7)
- `sections/06-setup.tex:30`: provider: effort and output limit (Q22)
- `sections/06-setup.tex:34`: fresh store per run (Q22)
- `sections/06-setup.tex:36`: second model, repetitions, budget, dates (Q8)
- `sections/06-setup.tex:42`: namespaces hidden per case
- `sections/06-setup.tex:45`: leak fix and its commit (Q5)
- `sections/06-setup.tex:48`: unseen case: in or out (Q12)
- `sections/06-setup.tex:52`: L4 atoms per case
- `sections/06-setup.tex:55`: audit: who, sample, agreement (Q9)
- `sections/06-setup.tex:62`: relation labels: join at scoring
- `sections/06-setup.tex:63`: trace audit (Q9)
- `sections/06-setup.tex:79`: behavior on test records: in or out (Q27)
- `sections/07-results.tex:20`: after results: comparisons, kinds, ablations, unmatched changes
- `sections/07-results.tex:54`: evaluator: stacked bars by match, after results
- `sections/07-results.tex:70`: after results: ranges, element kinds, without refinements
- `sections/07-results.tex:73`: after results: Strict, other conditions, credits per run
- `sections/07-results.tex:79`: audit: agreement with the person's labels (Q9)
- `sections/07-results.tex:88`: after results: other conditions and E3, E4 measures
- `sections/07-results.tex:93`: development cases: leak-free, DCAT-pinned reruns
- `sections/07-results.tex:106`: leak fix commit (Q5)
- `sections/07-results.tex:109`: after results: cost per condition
- `sections/08-discussion.tex:23`: extracted atoms: results (Q21)
- `sections/08-discussion.tex:26`: after results: keep or drop this sentence
- `sections/08-discussion.tex:32`: after results: extension rates, unjustified mints
- `sections/08-discussion.tex:56`: audit: result (Q9)
- `sections/08-discussion.tex:60`: tool: sign-off ignores unresolved atoms (Q22)
- `sections/08-discussion.tex:69`: conditions SX, TC, TR (Q7)
- `sections/08-discussion.tex:83`: tool: align C1 with V3 (Q22)
- `sections/08-discussion.tex:90`: counterfactual atoms: results (L4)
- `sections/08-discussion.tex:97`: leak fix commit (Q5)
- `sections/08-discussion.tex:104`: second model: in or out (Q8)
- `sections/09-conclusion.tex:11`: main results: Recovery and Strict of FP, RB, CB
- `sections/09-conclusion.tex:15`: next steps: author to pick, candidates in source
- `sections/10-statements.tex:4`: persistent identifiers before submission.
- `sections/10-statements.tex:14`: authors: list any further tools
- `sections/11-appendix.tex:172`: cases in full: Q3, Q9, Q11, Q21, Q23
- `sections/12-appendix-cd.tex:22`: after results: largest gap between the two sums
- `sections/12-appendix-cd.tex:107`: qualitative examples: reference-derived (atom identifier and generated change), in a local, uncommitted file

#### Bibliography entries with a verify note (`references.bib`)

- `klimek2024dataspecer`: verify: identifiers checked through search results only
- `stenchlak2022dataspecer`: verify: identifiers checked through search results only
- `prokop2024assistant`: verify: identifiers checked through search results only
- `moxon2021linkml`: verify: identifiers checked through search results only
- `robertson2009bm25`: verify: identifiers checked through search results only
- `zhou2026nl2shacl`: verify: identifiers checked through search results only

#### Main-result slots (`\res{scope}{condition}{measure}`, all print `?` now)

- `five`: all/N ×2, all/arq1, all/class, all/counterfactual, all/elements, all/loosened, all/mint, all/refine, all/reuse, all/unaligned
- `geo`: CB/calls, CB/extrate, CB/included, CB/matched, CB/recovery, CB/strict, FP/calls, FP/extrate, FP/included, FP/matched, FP/queue, FP/recovery, FP/strict, RB/extrate, RB/included, RB/matched, RB/queue, RB/recovery, RB/strict, all/N ×3, all/arq1, all/class, all/counterfactual, all/elements, all/extrateRef, all/loosened, all/mint, all/refine, all/reuse, all/unaligned, noREP/calls, noREP/extrate, noREP/included, noREP/matched, noREP/queue, noREP/recovery, noREP/strict, noRET/calls, noRET/extrate, noRET/included, noRET/matched, noRET/queue, noRET/recovery, noRET/strict, noTT/calls, noTT/extrate, noTT/included, noTT/matched, noTT/queue, noTT/recovery, noTT/strict
- `health`: CB/calls, CB/extrate, CB/included, CB/matched, CB/recovery, CB/strict, FP/calls, FP/extrate, FP/included, FP/matched, FP/queue, FP/recovery, FP/strict, RB/extrate, RB/included, RB/matched, RB/queue, RB/recovery, RB/strict, all/N ×3, all/arq1, all/class, all/counterfactual, all/elements, all/extrateRef, all/loosened, all/mint, all/refine, all/reuse, all/unaligned, noREP/calls, noREP/extrate, noREP/included, noREP/matched, noREP/queue, noREP/recovery, noREP/strict, noRET/calls, noRET/extrate, noRET/included, noRET/matched, noRET/queue, noRET/recovery, noRET/strict, noTT/calls, noTT/extrate, noTT/included, noTT/matched, noTT/queue, noTT/recovery, noTT/strict
- `jrc`: CB/calls, CB/extrate, CB/included, CB/matched, CB/recovery, CB/strict, FP/calls, FP/extrate, FP/included, FP/matched, FP/queue, FP/recovery, FP/strict, RB/extrate, RB/included, RB/matched, RB/queue, RB/recovery, RB/strict, all/N ×3, all/arq1, all/class, all/counterfactual, all/elements, all/extrateRef, all/loosened, all/mint, all/refine, all/reuse, all/unaligned, noREP/calls, noREP/extrate, noREP/included, noREP/matched, noREP/queue, noREP/recovery, noREP/strict, noRET/calls, noRET/extrate, noRET/included, noRET/matched, noRET/queue, noRET/recovery, noRET/strict, noTT/calls, noTT/extrate, noTT/included, noTT/matched, noTT/queue, noTT/recovery, noTT/strict
- `mobility`: CB/calls, CB/extrate, CB/included, CB/matched, CB/recovery, CB/strict, FP/calls, FP/extrate, FP/included, FP/matched, FP/queue, FP/recovery, FP/strict, RB/extrate, RB/included, RB/matched, RB/queue, RB/recovery, RB/strict, all/N ×3, all/arq1, all/class, all/counterfactual, all/elements, all/extrateRef, all/loosened, all/mint, all/refine, all/reuse, all/unaligned, noREP/calls, noREP/extrate, noREP/included, noREP/matched, noREP/queue, noREP/recovery, noREP/strict, noRET/calls, noRET/extrate, noRET/included, noRET/matched, noRET/queue, noRET/recovery, noRET/strict, noTT/calls, noTT/extrate, noTT/included, noTT/matched, noTT/queue, noTT/recovery, noTT/strict
- `stat`: CB/calls, CB/extrate, CB/included, CB/matched, CB/recovery, CB/strict, FP/calls, FP/extrate, FP/included, FP/matched, FP/queue, FP/recovery, FP/strict, RB/extrate, RB/included, RB/matched, RB/queue, RB/recovery, RB/strict, all/N ×3, all/arq1, all/class, all/counterfactual, all/elements, all/extrateRef, all/loosened, all/mint, all/refine, all/reuse, all/unaligned, noREP/calls, noREP/extrate, noREP/included, noREP/matched, noREP/queue, noREP/recovery, noREP/strict, noRET/calls, noRET/extrate, noRET/included, noRET/matched, noRET/queue, noRET/recovery, noRET/strict, noTT/calls, noTT/extrate, noTT/included, noTT/matched, noTT/queue, noTT/recovery, noTT/strict
- `test`: CB/included ×2, CB/matched ×2, CB/matchedShare, CB/recovery ×2, CB/recoveryShare, CB/strict, CB/strictShare, FP/auditDispositions, FP/auditVerdicts, FP/c7warnings, FP/calls, FP/conflicts, FP/extrate, FP/hours, FP/included ×2, FP/jaccard, FP/matched ×2, FP/matchedShare ×2, FP/queue ×2, FP/recovery ×3, FP/recoveryShare ×2, FP/strict ×2, FP/strictShare ×2, FP/tokens, FP/unjustifiedMints, FP/verdicts, RB/included ×2, RB/matched ×2, RB/matchedShare, RB/recovery ×2, RB/recoveryShare, RB/strict, RB/strictShare, all/N ×4, all/arq1, all/class, all/counterfactual, all/elements, all/extrateRef, all/loosened, all/mint, all/refine, all/reuse, all/unaligned, noREP/included, noREP/matched, noREP/matchedShare, noREP/recovery ×2, noREP/recoveryShare, noREP/strict, noREP/strictShare, noRET/included, noRET/matched, noRET/matchedShare, noRET/recovery ×3, noRET/recoveryShare, noRET/strict, noRET/strictShare, noTT/included, noTT/matched, noTT/matchedShare, noTT/recovery ×2, noTT/recoveryShare, noTT/strict, noTT/strictShare

#### Direct `\tbd` cells

- `sections/11-appendix.tex` (15)

<!-- markers:end -->

## Questions for Junda

Numbered as in the `\todo` markers of the sources (Qn). Each can be answered on its own.

1. **Q1 RQ1 sources.** I have the RQ1 PDF (13 Nov check version) but not its `main.tex`. Please send it, or attach
   the private run store. I need the exact `\acro` keys, the `\acresetall` convention and the table macros;
   `acronyms.tex` copies the expansions as printed.
2. **Q2 Where the paper lives.** I read "keep the paper draft on your side and in chat" as follows:
   - the committed paper has no reference-derived examples;
   - the full version (with atom-id examples) goes to chat only, built from the gitignored
     `sections/local/qualitative-examples.tex`;
   - the RQ1 PDF is not committed.
   Confirm, or tell me if the whole paper should leave the repository.
3. **Q3 Base release and reference version per case.** I did not choose them.
   - RQ1 bases: Mobility 2.0.1, Geo 1.1, Health 3.0.0, Stat 1.1, JRC 1.1 (RQ1 Table 1).
   - At 5ffd56e the tool ships all nine DCAT-AP releases with SHACL (1.1 to 3.0.1).
   - The reference profile versions are open too (e.g. DCAT-AP-JRC v1 or v2, StatDCAT-AP 1.0.0 or 1.0.1).
   - Table `tab:cases` prints `\todo` cells until you decide.
4. **Q4 RQ1 run store.** `reqs_extract_run_store` could not be attached to this session. Attach it, or upload
   `rq1-paper-instructions-2026-11-04.md` and the final-scoring `paper/*.tex`, so that voice and table macros can be
   aligned exactly.
5. **Q5 Answer-in-input leak (with Q15).** Fix it in the tool before any evaluation run. Three channels:
   - every proposer, repairer and judge prompt prints `source: <document>, <locator>`
     (`backend/profile_extensioner/engine/prompts.py:113-115` at 5ffd56e);
   - the run script names the case in the project title (`scripts/run_reference_case.py:33`);
   - atom identifiers can name the case, and they are printed in every prompt. Re-key them in the importer and
     keep a private map for scoring.
6. **Q6 Auto-accept rule.** The paper states what the code does: a "partially supported" verdict and an
   unavailable judge only warn, and a change cleared by consolidation can be accepted without any judge verdict.
   The design note says otherwise. Confirm the paper's wording, or fix the code first.
7. **Q7 Conditions.** Status of each:
   - FP (full pipeline), RB (rules baseline), −RET, −REP, −T2: runnable or nearly;
   - CB (closed book: the same model without the atoms, a contamination probe): needs a probe script, and its variant
     is open (the companion's, with domain and base only, or the plan's, with the extension's name);
   - SX (the model writes SHACL): not implemented;
   - TC/TR need a working verify switch (`PipelineConfig.verify` is never read);
   - HR (human review in the loop): in or out?
   Confirm the names and the set.
8. **Q8** A second model, the number of repetitions (three are planned) and the budget.
9. **Q9 Human judgments.** Who does each, and with what sample size and agreement statistic?
   - auditing the judge's verdicts and the repairer's dispositions;
   - adjudicating relaxed matches;
   - checking the hand-extracted references.
10. **Q10 Title.** Proposal: "Trace-Verified Profile Modeling for DCAT-AP Extensions with LLMs". Alternatives:
    "Reuse-First, Trace-Verified Modeling of DCAT-AP Extensions with LLMs"; "From Requirement Atoms to Conformant
    DCAT-AP Extensions with LLMs".
11. **Q11** May Table `tab:cases` print the test-case atom counts that RQ1 Table 1 already reports? The cells are
    `\todo` now.
12. **Q12** Construct-DCAT as an unseen case: in or out of this paper, and how to keep the submission anonymous?
13. **Q13 Use of Generative AI statement.** Should it say that the literature steps were extracted and
    fact-checked with AI agents? Should it name further tools?
14. **Q14 Described commit.** The paper describes the tool at `main` 5ffd56e, which is not merged into
    `paper-draft`. A merge was requested from the tool session. I did not do it, because you asked me to push only to
    `paper-draft`, not to change tool code, and to ask before touching `main`. Merge, or describe another commit?
15. **Q15** The leak persists at 5ffd56e (see Q5).
16. **Q16 Development runs 1-3.** Keep them only as the appendix debugging history (current draft), or drop
    Table `tab:pilot` entirely?
17. **Q17** Sect. 1 reuses RQ1's mobilityDCAT-AP update-frequency example, which RQ1 itself reports. Keep it, or
    use a generic example?
18. **Q18** The test-case statement in Sect. 5, and the practice of citing the 18 G3 literature steps only through
    keys that are not test-case specifications. Are both acceptable?
19. **Q19** ESWC 2027 page rules. If the appendix is limited to two pages, the move-out order is:
    - Table `tab:checks`;
    - Fig. `fig:reference`;
    - Table `tab:steps`;
    - the debugging history.
20. **Q20 Modality.**
    - Option 1: carry the reference's obligation into the atoms' modality. This is more faithful.
    - Option 2: keep the conservative mapping. This leaks less, but most atoms are "unspecified", so no change can be
      mandatory.
21. **Q21 Extracted atoms (the plan's A-rq1).** Which companion run, which retained needs (none were accepted), and
    how should needs be converted to atoms?
22. **Q22 Tool issues: fix before the evaluation, or state as limits?** See the table below; the first group matters
    most.
23. **Q23 Reference-delta construction.** Open points:
    - the implicit class targets of DCAT-AP 1.1;
    - the obligation tables of the published profiles;
    - profiles of profiles;
    - how to count loosened elements.
24. **Q24** Cite artefact-level evidence (RIGOR repository, SAST-Blackboard code, OE-Assist slides) as "the
    released implementation of X", or with a pointer to the repository?
25. **Q25** How to cite the companion paper and name the profile editor under double-blind review.
26. **Q26** Venue and track if the main results are not ready. Do not submit while `\res` prints `?`.
27. **Q27** Behavior on test records (a plan metric): in or out?
28. **Q28** Votes above one, or the HR condition, so that the final say is evaluated and not only implemented.
29. **Q29** Table `tab:steps`: list the planned steps by id, or only count them?
30. **Q30** The new bibliography entries and their open points (see the bibliography markers above). Notes:
    - `w3cshacl12profiling` is in the bib but uncited, and its content was not read.
    - `chmielewski2026blackboard` (RQ1) has neither DOI nor URL ("to appear").
    - The RQ1 bib header says 54 entries, but the file has 62.

31. **Q31 Next steps in the conclusion.** Pick them (the candidates are in a comment in `sections/09-conclusion.tex`):
    - a person's review of drafted extensions (HR);
    - an end-to-end run from extracted needs;
    - embedding retrieval;
    - controlled-vocabulary usage levels;
    - per-atom witnesses for C7.
32. **Q32 Work before the main evaluation** (markers without a question of their own):
    - freeze the commit and tag of the pipeline and the reference deltas;
    - build the evaluator that writes `results/main-numbers.tex`;
    - hide the target namespace per case;
    - write the counterfactual atoms per case (leakage control L4);
    - join the relation labels back at scoring time;
    - prepare the demo walk-through for the supplementary material.
33. **Q33 Synthetic demo wording.** Table `tab:criteria` quotes the synthetic atoms verbatim, including the British
    "organisation" from `examples/materials-testing-lab/atoms.yaml`. Keep it, or change the example file?

## Tool issues found while writing

All issues were checked read-only, offline and in memory on a worktree of `main` at **5ffd56e**. Only synthetic atoms,
the synthetic demo and the mock provider were used. No tool code was changed. `B/` = `backend/profile_extensioner/`.
Status: **still present** unless marked.

### A. Threats to the evaluation (fix before the main runs, or state as limits; Q22)

| # | Issue | Where (5ffd56e) | Consequence |
|---|---|---|---|
| A1 | **Answer-in-input leak.** The source document and locator are printed in every proposer, repairer and judge prompt, the run script names the case in the project title, and atom identifiers can name the case. | `B/engine/prompts.py:113-115` (used at `:177`, `:231`, `:265`), `:174`; `scripts/import_rq1_reference.py:57-58`; `scripts/run_reference_case.py:33` | All development runs are contaminated; the main runs must not start before this is fixed (Q5). `docs/design.md:73` calls the leakage controls "implemented". |
| A2 | Dead switches `PipelineConfig.verify` and `require_human_signoff`: defined, never read. | `B/contracts.py:594,600`; docstring `:589-590` | Conditions TC/TR cannot run; the docstring "each component can be turned off" is wrong (Q7). |
| A3 | The replay cache is global across projects, and one store is shared by the run script. `judge-v1` is unchanged, so old judge verdicts replay. | `B/store/blackboard.py:341-351`; `B/llm/client.py:85-95`; `scripts/run_reference_case.py:28` | Repeated runs are not independent unless each gets a fresh store. Probe: a second project got 25 of 25 calls from the cache. |
| A4 | The OpenAI-compatible provider sends neither `max_output_tokens` nor `effort`, and a truncated answer (`finish_reason "length"`) is accepted. | `B/llm/openai_compatible.py:82-91,123`; `B/llm/client.py:130-139` | Cost and truncation are uncontrolled; `effort` still enters the cache key (`B/llm/client.py:70-72`). |
| A5 | The judge (T2) is bypassed for changes that consolidation clears; `_decide` does not need a T2 result. | `B/engine/pipeline.py:359-366`, `:246-267` | A merged change can be auto-accepted with no verdict (probe: 0 judge calls). Contradicts `docs/design.md:25`. |
| A6 | Duplicates go to model repair before the deterministic consolidation (every member gets a V5 error). | `B/contracts.py:104-107`; `B/engine/verify.py:493-510` | Probe: 6 repair calls for one duplicate pair. A repairer can withdraw or swap a correct change. |
| A7 | **NEW-1** Rebase review flags are overwritten by the consolidation that follows the rebase. | `B/engine/pipeline.py:600-605` → `:359-366` | Flagged machine changes return to `auto_accepted`, and the queue is empty. The test `tests/test_rebase.py:62` passes for another reason (V4). |
| A8 | **NEW-2** Lost "covered by the base" claims survive a rebase; B1 is not re-run; sign-off is allowed. | `B/engine/rebase.py:164-179`; `B/engine/pipeline.py:200-211,591-607` | Coverage can be overstated after a rebase. |
| A9 | Sign-off checks only change statuses and conformance, not the atoms (unclear, unaddressed). | `B/engine/pipeline.py:618-626`; compare `B/contracts.py:69` | "Only a person releases" holds for changes, not for unresolved atoms. |

### B. Checks and artefacts

| # | Issue | Where (5ffd56e) | Consequence |
|---|---|---|---|
| B1 | C7 warns on legal refinements (range narrowing, `dcat:keyword` min 2, `xsd:hexBinary`): the witness generator, not the extension, fails. Its error branch cannot fire. | `B/conformance/check.py:181-209`, `:102-108,233-245` | Verdicts read "conformant with warnings" without cause; the paper calls C7 a satisfiability witness. |
| B2 | Incomparable deltas count as "tightened" and appear in no item list; conflicts count as "loosened". | `B/conformance/check.py:124-136`, `:131-133` | Conformance counts can mislead; `docs/conformance.md:69-71` says otherwise. |
| B3 | `owl:imports` names the HTML release page (3.0.0, 3.0.1) and is absent for the seven 1.x and 2.x bases; `prof:isProfileOf` is relative there. | `B/compile/shacl.py:33-34`; `B/compile/linkml_dsv.py:131`; `B/data/base-profiles/dcat-ap-3.0.1/profile.yaml:6` | The artefact does not point to the official shapes; conformance itself uses the vendored shapes, so the verdicts are unaffected. |
| B4 | **NEW-3** For base elements the specification lists without a shape, V3 compares the obligation, while C1 and the ProfileDelta count them as "added". | `B/engine/verify.py:302-305,319-330`; `B/conformance/check.py:119-123`; `B/compile/model.py:65,72` | A human-accepted loosening of such an element passes conformance. |
| B5 | **NEW-4** `unknown` obligations in the newly added releases (1.2.1: 2, 2.0.0: 5, 2.0.1: 5, 2.1.0: 4, 2.1.1: 3), from shape typos left as published and properties missing from the extracted obligations. | `B/data/base-profiles/dcat-ap-2.*/obligations.yaml`; `docs/dcat-versions.md:171-176` | B1 can never confirm these elements, and their loosening is not detected. |
| B6 | The ProfileDelta's status and severity disagree with SHACL and conformance (main shape always `sh:Violation`; an identical refinement is "tightened" in the delta and "unchanged" in conformance). | `B/compile/model.py:65-72`; `B/compile/shacl.py:76`; `B/engine/propose.py:295` | The scoring must use one definition; the paper uses the ProfileDelta's. |
| B7 | Usage-note changes are dropped from the SHACL and DSV artefacts. | `B/compile/model.py:21-38`; `B/compile/docs.py:94-103` | Usage notes appear only in the documentation; the paper does not score them. |
| B8 | DSV IRIs collide on equal local names (`dcterms:identifier` and `adms:identifier` on Dataset become one node). | `B/compile/linkml_dsv.py:166` | Invalid DSV for such extensions. |
| B9 | Stale references to a minted term after a person rejects it (a property ranged on a rejected class stays included; the verdict is conformant). | `B/engine/verify.py:68-72`; `B/conformance/check.py:149-168` | Human overrides can leave dangling ranges. |
| B10 | Merge keeps stale justifications; an incomparable refinement is labelled "tightened"; the delta is never "unchanged". | `B/engine/consolidate.py:54-77`; `B/engine/verify.py:316-317`; `B/compile/model.py:72` | Justification text can disagree with the merged facets. |
| B11 | `sh:pattern` is never compared by V3/C1. | `B/conformance/refinement.py` | A loosened pattern goes unnoticed. |
| B12 | V2 treats `dcam:rangeIncludes`/`schema:domainIncludes` as strict, and several domain statements are read as "any of" (3 vendored terms). | `B/knowledge/vocab_index.py:28-31,162-167`; `B/engine/verify.py:177` | A false V2 error (e.g. `dcterms:rightsHolder` with range `foaf:Organization`); verify the DCMI semantics. |
| B13 | Classes without a known superclass get only a V2 warning for a misfit (8 of 11 classes in 1.x); minted classes are never in the hierarchy. On 1.1, `dcat:theme` on `dcat:Distribution` can be auto-accepted. | `B/engine/verify.py:260-272`; `B/knowledge/__init__.py:112-129` | Changed at 5ffd56e (D1 blocks this for DCAT 2/3 bases); the pilot base 1.1 is still exposed. |
| B14 | **NEW-6** D1's placement check is skipped for later-DCAT terms. | `B/engine/verify.py:260-261` | Under 1.1, `dcat:accessService` on `dcat:Dataset` reaches the person only as "introduced in DCAT 2", not as misplaced. |
| B15 | **NEW-7** D2 matches a base deprecation on the exact class only (`dct:hasVersion` deprecated on Dataset is not flagged on Catalog or DatasetSeries). | `B/knowledge/base_profile.py:165-171`; `B/engine/retrieve.py:186-190` | Verify the intended scope of DCAT-AP deprecations. |
| B16 | Class retrieval truncates before the priors and the base boost (a base class can be lost, e.g. `dcterms:LicenseDocument` for "licence"). Properties are handled the same way. | `B/engine/retrieve.py:215-230`, `:160` | A reuse candidate can be missed. |
| B17 | The retrieval docstring promises a full-wording fallback that only runs when nothing is left. | `B/engine/retrieve.py:28-30` vs `:57-62` | Documentation. |
| B18 | Range shape files are vendored but never loaded. | `B/knowledge/base_profile.py:93` | `docs/conformance.md:29-31` says they are part of the base. |
| B19 | `edit_change` accepts a failing version without the "despite failing checks" note; atom edits through the API do not withdraw the sign-off; a consolidation conflict note is overwritten. | `B/engine/pipeline.py:512-536,351-366`; `B/api/app.py:287-303` | The workbench record can understate what a person overrode. |
| B20 | **NEW-10** `dct:conformsTo` names the DCAT Recommendation for releases built on a Candidate or Proposed Recommendation (2.0.0, 3.0.0). | `B/compile/shacl.py:36-37`; `B/knowledge/base_profile.py:139-146` | Documented approximation; low impact. |

### C. Metrics, records and documentation

| # | Issue | Where (5ffd56e) | Consequence |
|---|---|---|---|
| C1 | The extension rate is minted properties over included property-level changes. The pilot file's prose ("share of included changes that mint new terms") gives other values. | `B/engine/pipeline.py:463,473`; `inputs/pilot-runs-2026-11-13.md` | The paper uses the code's definition. |
| C2 | Status "rejected" covers both human rejections and repairer withdrawals. | `B/contracts.py:86`; `B/engine/pipeline.py:328-331` | In all development runs every "rejected" is a withdrawal; the paper says "withdrawn by the repairer". |
| C3 | The `repaired` metric counts failed repair attempts. | `B/engine/pipeline.py:334-336,474` | The paper does not use the metric. |
| C4 | Call records keep only the first prompt (the corrective retry is lost) and have no stop reason. | `B/llm/client.py:73-83,128-148` | Cost and failure analysis is incomplete. |
| C5 | `README.md:95` says 70 tests; 98 are collected at 5ffd56e. | `README.md:95` | Documentation. |
| C6 | **NEW-5** The README artefact says each later-DCAT term was "accepted by a human reviewer", even under `later_dcat_terms="allow"`. | `B/compile/docs.py:85-90`; `docs/conformance.md:51` | The artefact overstates human review. |
| C7 | **NEW-8** The C8 row sits outside the rules table (a blank line ends the table). | `docs/conformance.md:50-51` | Cosmetic. |
| C8 | **NEW-9** The three DCAT-AP 1.1 obligation corrections are not recorded in the file header, unlike 1.2. | `B/data/base-profiles/dcat-ap-1.1/obligations.yaml:1-4` | Provenance; `docs/dcat-versions.md:157-158` says they are recorded. |
| C9 | The workbench stepper shows "Review & sign-off: running" after a completed run (by design, until a sign-off exists). | `B/engine/pipeline.py:425-426,608`; `frontend/src/App.tsx:204,208` | A label such as "waiting for you" would be clearer. |
| C10 | The mock provider's datatype cue misses "number of" (a count becomes `xsd:string`). | `B/llm/mock.py:319,334` | Visible in the workbench figure; its caption says so. |
| C11 | Packaging: no `B/cli.py` behind the entry point; package data only `py.typed`; `B/data/dcat` (2.3 MB) undeclared. Smaller items: the docstring of `B/compile/linkml_dsv.py:10-11` is stale; `LEGACY_CHANGE_TYPE` is unused (`B/contracts.py:689`); `Credentials.source("anthropic")` ignores SDK profiles. | `pyproject.toml:26-33` | A non-editable install may fail (verify). |

### D. Security (stated as a limit in the paper)

| # | Issue | Where (5ffd56e) |
|---|---|---|
| D1 | No authentication. The reviewer name is self-asserted, including on the new rebase endpoint (a rebase "by anyone-at-all" is recorded as `human:anyone-at-all`). | `B/api/app.py:111-114,370-380` |
| D2 | A user-set `base_url` (SSRF); a development server; the SPA path handler (verify path traversal); DELETE without a lock. | `B/api/app.py:281-284,452-455` |

### E. Fixed at 5ffd56e (reported earlier, now gone)

- V2 reads `owl:unionOf` domains: `dcat:hadRole` on `dcat:Dataset` now fails V2 (`B/knowledge/vocab_index.py:120-136`).
- The DCAT-AP 1.1 obligation errata (`contactPoint` key, `dcat:mediaType`, `accrualPeriodicity`): 0 unknown obligations in 1.1.
- `GET /api/base-profiles/{unknown}` returns 404, not 500.
- An atom set's declared base is honoured.
- The README lists all nine releases.

### F. In the paper's own scripts

- `paper/scripts/make_pilot_tables.py` built the conformance counts with a dict keyed by number, so equal counts
  collided and two macros printed empty. Fixed in commit f2abb61. `paper/scripts/check_pilot_macros.py` re-parses
  the inputs independently and finds 0 mismatches.

## Section-by-section mapping to RQ1

| RQ2 | RQ1 | Parallel | Different |
|---|---|---|---|
| Abstract | Abstract | problem, gap, approach, benchmark, results slot, artefacts; same length (≈220 words) | input atoms instead of documents; no result numbers yet (`?`) |
| 1 Introduction | 1 Introduction | seven paragraphs to seven: setting, the "requirements problem before a modeling problem" pick-up (cited to the companion), gap, approach, RQ, contributions as three dashes, outline | the gap is guidance-level (why an element exists is not recorded); RQ2 asks how far the model can carry an extension that stays reuse-first, traced, decided under human control and conformant |
| 2 Related Work | 2 Related Work | four italic run-in paragraphs in the same order | profile tooling (Dataspecer, DSV, LinkML), ontology/shape generation with LLMs (RIGOR, OntoChat, Ontogenia, NL2SHACL-Bench, text2shacl), conformance and validation, human control |
| 3 Changes for a DCAT-AP Extension | 3 Requirements for a DCAT-AP Extension | task sentence, input/output objects, criteria E1-E4 as the twins of R1-R4 | the object is a change (ProfileChange) in a ProfileDelta; the reuse ladder and kinds (Table `tab:kinds`); obligation licensed by modality; base = release + DCAT state |
| 4 Pipeline (4.1-4.4) | 4 Workflow (4.1-4.4) | figure first, four subsections, "Implementation and traceability" last | nine operations on a blackboard; checks V1-V5, D1-D3, T1-T2, B1; compilation targets; conformance C1-C8; the workbench, sign-off and rebase |
| 5 Benchmark | 5 Benchmark | same run-in heads; development and test cases; references fixed before any run | reference deltas (published profile minus base) and their alignment to atoms instead of reference atoms; Fig. `fig:reference` in the appendix |
| 6 Experimental Setup | 6 Experimental Setup | same run-in heads plus one; conditions, model, repetitions, measures with the strict and relaxed views | conditions FP/RB/CB and removal ablations −RET/−REP/−T2; measures Recovery/Strict, change precision against the reference, extension rate, conformance, review load, cost |
| 7 Results | 7 Results | same run-in heads in the same order; the development cases apart | every number is `\res{}` (`?`); the development runs only as a debugging history (Appendix C.1) |
| 8 Discussion and Threats to Validity | 8 Discussion and Threats to Validity | eight run-in paragraphs, re-aimed, plus one | lexical retrieval; missing vocabularies; controlled-vocabulary levels not modelled; the C7 witness; judge reliability; no authentication; contamination |
| 9 Conclusion | 9 Conclusion | one paragraph, ≈130 words | the hand-off: atoms in, a signed-off extension out |
| Appendix A-B | A Illustrations, B The Benchmark in Full | criteria on synthetic atoms (twin of RQ1 Table 2); the cases in full | A adds the workbench figure and the check table; B adds the reference-delta flow |
| Appendix C-D | C Results in Full | full results table (`\res`) | C.1 debugging history (Table `tab:pilot`), C.2 qualitative examples (local only); D the 99 literature steps by operation |

## How this draft was made

- Readers digested the engine, the knowledge/compile/UI code, the docs, the literature steps, the RQ1 voice (from
  the PDF), the development runs, conformance and Dataspecer, and DCAT-state pinning.
- An outline panel followed: two independent outlines plus a main-loop candidate, two judges with different lenses,
  and a synthesis into writer briefs.
- Nine section writers worked in parallel. Adversarial reviewers then checked numbers, citations, hard rules,
  technical accuracy, reviewer critique and LaTeX/voice, and skeptics verified each finding before a fix was applied.
- Bibliography entries were added only with a checked DOI or URL. Entries checked only through search results print
  a "verify" note.
- No tool code was changed. No test case was run or inspected. No external model was called for the paper.
