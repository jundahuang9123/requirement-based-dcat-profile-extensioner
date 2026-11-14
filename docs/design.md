# Design

## Goal

Given requirement atoms (atomic, term-free requirements with subject, modality
and source) and a base profile (a pinned DCAT-AP release), produce an extension
that (1) satisfies the atoms, (2) reuses before it mints, (3) traces every
element and every tightened constraint to the atoms that justify it, (4) still
conforms to the base, and (5) is decided mostly by the model with the human
holding the final review right.

## Roles

| Component | Role | Where |
|-----------|------|-------|
| Model (proposer, repairer, judge) | Fills typed records only: an `AtomDecisionOut` per atom, a `RepairOut` per failed change, an `AttributionOut` per judged change. Never writes SHACL or IRIs of minted terms. | `engine/prompts.py`, `engine/schemas.py` |
| Symbolic engine | Retrieves, expands and mints IRIs, decides change kinds from the facts (reuse vs refine), verifies, merges, compiles, checks conformance. | `engine/`, `knowledge/`, `compile/`, `conformance/` |
| Blackboard | Append-only log of every action (rule, model, person) plus the current state of each object. | `store/blackboard.py` |
| Human | Reviews the queue, overrules any decision, edits changes, overrides atom dispositions, signs off. | workbench, `engine/pipeline.py` (`decide`, `edit_change`, `override_assessment`, `sign_off`) |

## Decision policy

| Situation | Outcome |
|-----------|---------|
| All error-level checks pass, the judge finds the change supported (when on), confidence ≥ threshold, a majority of votes agree (when voting) | `auto_accepted`: part of the profile unless a human overrules |
| An error-level check fails | bounded repair (default 3 rounds; every round starts from a fresh verification of the whole set); still failing → `needs_review` |
| Two changes on the same (class, property) | a set-level finding (V5 `duplicate_element`). Each claim is still judged on its own; **consolidation** merges only valid claims (no error of their own, not rejected by the judge), keeping the judged-supported one, before repair; the merged change is verified and judged again with all its atoms. A claim with an error of its own is repaired first and merged afterwards. Incompatible duplicates become a conflict. If a machine withdraws a merged change, what it had absorbed is restored |
| The judge did not assess the change (not run, or unavailable), or found it only partly supported, while the judge is on | `needs_review` (never auto-accepted without a "supported" verdict) |
| Low confidence, no majority, conflict between changes (stays in review until a human resolves it), automatic acceptance switched off | `needs_review` |
| A repair revision drops atoms of the change it replaces | the atoms are re-attached (a repair never loses coverage) |
| A DCAT term only a later DCAT version than the base's defines (D1, policy `review`) | `needs_review`: a human decides |
| A human decides | final: later machine stages never overwrite it |
| The base is changed (rebase) | human decisions stay; machine changes with a migration finding go to `needs_review`; all are verified again |
| Release | only by a human sign-off, only with an empty queue, no pending rebase plan, every stage current (done or skipped) and a passing conformance report; any later decision, atom edit, title or settings change withdraws it (and the artefacts are recompiled as a draft). Condition `require_human_signoff: false` releases a conformant profile automatically, labelled as such |
| Condition `verify: false` (ablation) | only the well-formedness guard V0 runs (plus the judge if on); decisions never claim "all checks passed"; conformance C1-C8 still measures the outcome |

## Checks

`V1` term exists · `V2` domain/range fit · `V3` legal refinement of the base ·
`V4` reuse before mint · `V5` internal consistency · `V6` valid SHACL ·
`D1` DCAT state: terms of the DCAT version the base builds on, used on a class that
DCAT lists them for · `D2` no deprecated term (pinned DCAT or base) · `D3` inverse
properties only in addition to the property they invert ·
`T1` trace (atoms exist, verbatim quote, every constraint justified, obligation
not stronger than the atoms' modality licenses) · `T2` judge: the atoms support
the change · `B1` "covered by the base" claims name base elements that are strong
enough. Final conformance: `C1`–`C8` ([conformance.md](conformance.md)). The DCAT
state and the rebase are described in [dcat-versions.md](dcat-versions.md).

## Key steps taken from the literature

The complete, fact-checked list (99 steps from four groups of papers, with verdicts and
the state of each step in this tool) is in [literature-steps.md](literature-steps.md);
the evidence is in `docs/research/`. The table below summarises the steps that shaped
the architecture. "What they did" is the paper's; "here" is our adaptation.

| Step | From | What they did | Here | Status |
|------|------|---------------|------|--------|
| Answerability pre-check | lippolis2025ontology (Ontogenia / memoryless CQbyCQ) | Ask first whether the CQ is already answerable by the current ontology; if so, change nothing. | Disposition `covered_by_base` is the first decision per atom; check `B1` verifies the claim against the base symbolically. | implemented |
| One requirement per call, memoryless | lippolis2025ontology | One CQ per call with an empty context of earlier output; merge afterwards. | One propose call per atom; merging and duplicate handling are deterministic (`consolidate`). | implemented |
| Fixed decomposition procedure | lippolis2025ontology (Ontogenia procedure) | Subject / predicate / object, then restrictions, then explain and rate confidence. | Numbered procedure in the propose prompt; `reading` and `information_needed` stored per atom; confidence per change. | implemented |
| Named prompt sections, mistakes footer | fathallah2026rigor, lippolis2025ontology | `[MANDATORY TASKS]`, `[STRICT CONSTRAINTS]`, `[CORRECTION INSTRUCTIONS]`; list of typical mistakes. | Same anatomy; versioned prompts; full prompts stored with every call. | implemented |
| Deterministic backbone, model emits deltas only | fathallah2026rigor | Direct mapping merged first; the LLM only enriches; fall back to the backbone. | The base is immutable; the model only proposes `ProfileChange` deltas; unresolved atoms leave the base untouched. | implemented |
| Typed records instead of model-written syntax | fathallah2026rigor (failure analysis) | Model wrote Manchester syntax read by a tolerant parser (artefact IRIs observed). | Typed JSON; IRIs and SHACL are produced by the engine only. | implemented |
| Bounded repair with error-specific hints | fathallah2026rigor, alharbi2027idea2 | At most three attempts; failures fed back in a dedicated section; scoped to rejected items. | `repair` stage, `[CORRECTION INSTRUCTIONS]` lists failed checks; rounds configurable. | implemented |
| Closed candidate list, explicit abstain | busch2025dcat, sadruddin2025schema | Pick identifiers from a given list; decline when in doubt. | Candidates listed in the prompt; a term outside them is flagged (`V1` warning); minting requires rejected candidates with reasons. | implemented |
| Reuse ladder | suarez2012neon, SEMIC reuse guidelines | Reuse non-ontological / ontological resources before building new ones. | Reuse base element → tighten base → reuse vocabulary term → mint; `V4`. | implemented |
| Element-level provenance; missing trace is a defect | fathallah2026rigor | `prov:wasDerivedFrom` on every generated element; missing provenance warned. | `covers` + `facet_justifications`; `T1` makes a missing trace an error; `prov:wasDerivedFrom` in SHACL and DSV. | implemented |
| Preserved or strengthened, never removed | fathallah2026rigor | The delta may not remove or contradict the backbone. | `V3` per change, `C1`/`C2` on the whole extension. | implemented |
| Executable coverage witness | lippolis2025oeassist | A CQ counts as modelled if a query answering it can be written. | `C7` witness data validated with pySHACL against base and extension. Per-atom witnesses: planned. | partial |
| Judge independent of the proposer; verbalised slice | fathallah2026rigor, lippolis2025bench4ke, zhang2024ontochat | Separate judge with graded decisions; plain-text verbalisation for checking. | `T2` judge reads the same verbalisation the reviewer reads (`engine/verbalise.py`); per-step models configurable. Warning when judge = proposer model: planned. | partial |
| Guardrails against over-trust | lippolis2025oeassist | Wrong suggestions lowered reviewer accuracy; show evidence and pre-check. | Machine decisions shown with check results, quotes, alternatives and calls; "Undecided" option; every human decision logged. | implemented |
| Atom well-formedness gate | iso29148, alharbi2026cq, zhang2024ontochat | Singular, unambiguous requirements; split compound questions; abstract named entities. | `intake` lint: term-free (error), compound, modality mismatch, vague wording, unmapped subject. Proposals to split: planned. | partial |
| Review ledger and structured feedback | alharbi2027idea2, sadruddin2025schema | Votes, scores, comments per item; feedback re-injected next round. | Decisions with notes in the log; `[HUMAN FEEDBACK]` prompt section exists; structured feedback codes: planned. | partial |
| Version lineage | alharbi2027idea2 | Versions of each item with history. | Edits and repairs create new versions (`supersedes`); full export of state, log and calls. | implemented |
| Independent votes | alharbi2026cq (more than one proposer) | Several generators, then refinement. | `votes` per atom with majority on the decision shape. | implemented |
| Leakage controls | RQ2 plan (L2 answer held out, L4 counterfactual atoms) | Keep the answer out of the input; change atoms so the right answer departs from the publication. | Term-free atoms enforced at intake; namespaces can be hidden from the index; counterfactual atoms supported (`counterfactual_of`). | implemented |

## Relation to the existing repositories

* **visual-profile-editor**: same visual language and LinkML conventions
  (global slots = identity, `slot_usage` = per-class obligation). The
  `extension.linkml.yaml` artefact can be opened in VPE.
* **vpe-rq2 WP0 contracts**: `ProfileElement`/`ProfileDelta` and the atom
  contract are reused unchanged; `knowledge/shacl_reader.py` and
  `conformance/refinement.py` generalise `scripts/shacl_delta.py`.
* **Dataspecer**: `extension.dsv.ttl` follows the statements of Dataspecer's DSV
  writer (class and property profiles, cardinality, requirement level), so the
  profile can be published there.


## Benchmark hygiene (blind runs)

What the model sees of an atom is its id, statement, subject and modality, nothing else (also the offline
provider's context). Prompts carry no source reference, no project title, no namespace or prefix
(`propose-v3`, `repair-v3`, `judge-v2`). For RQ1 reference atoms:

- `scripts/import_rq1_reference.py` writes opaque ids (`A-001` ...) and no source reference, case name or
  benchmark id; the join back to the reference set is a separate evaluator map (`<out>.evalmap.json`)
  that the tool never reads. `--modality unspecified` withholds the modality where the reference document
  is the published profile itself.
- `scripts/run_reference_case.py` runs a blind project (`PipelineConfig.blind`: the workbench hides
  sources from the reviewer), project-scoped replay (no answers of earlier runs), neutral title and
  namespace, records every setting, and scans every stored prompt for canaries (case name, original ids,
  locators, reference document, published-profile names) before it reports (`LEAKCHECK`).
- Intake flags atom statements that name a published profile (`contains_profile_name`).
