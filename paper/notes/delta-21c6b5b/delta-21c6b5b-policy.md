# Delta 5ffd56e -> 21c6b5b: pipeline order and decision policy

Area: stage order and decision policy (`B/engine/pipeline.py`, `B/engine/consolidate.py`, `B/engine/verify.py` set-level
duplicates, `B/engine/rebase.py` staged rebase, `B/contracts.py` STAGE_ORDER and PipelineConfig, metrics), with the tests
`test_conditions.py`, `test_t2_after_consolidation.py`, `test_duplicates_consolidated.py`, `test_merge_never_loses_atoms.py`
and `test_rebase.py`.

- `B/` = `backend/profile_extensioner/`. Anchors are at **21c6b5b** (read-only worktree `scratchpad/main-wt2`) unless
  marked `@5ffd56e`.
- Method:
  - `git diff 5ffd56e 21c6b5b`, the commit messages of 40a5d5d, a3d8098, 913bea2 and 21c6b5b, and a full read of the
    new code.
  - Offline probes in memory: `Store()` is `:memory:`; the mock provider (or MockProvider subclasses that script one
    role); synthetic atoms and `examples/materials-testing-lab` only. No external model, no benchmark material.
  - The probes are in `scratchpad/delta-policy-probe/probe{1..7}_*.py`, run with
    `PYTHONPATH=main-wt2/backend ~/.venv-rbdpe/bin/python3 -B` from that directory.
  - `git status --porcelain --ignored` of the worktree stayed empty after every run.
- The five test files of the area pass offline at 21c6b5b: **30 passed** (pytest run from the probe directory with
  `RBDPE_WORKSPACE` there). The full suite record is `paper/inputs/tests-main-21c6b5b-2026-11-14.txt` (170 passed).

## 1. What changed in this area

| Commit | Change | Anchor at 21c6b5b |
|---|---|---|
| 40a5d5d | Rebase becomes a staged plan: preview (changes nothing), apply with choices, cancel. A pending plan blocks sign-off. Apply redoes intake, re-checks covered-by-base claims, re-proposes atoms. | `B/engine/rebase.py:16-21, 80-218`; `B/engine/pipeline.py:739-896`; `B/contracts.py:635-699` (RebaseItem/Plan/Report) |
| 913bea2 | STAGE_ORDER verify -> consolidate -> repair. | `B/contracts.py:104-109` (@5ffd56e `:104-107` had repair before consolidate) |
| 913bea2 | The V5 duplicate is a set-level finding that `repairable_failures` excludes. | `B/engine/verify.py:503-525` |
| 913bea2 | Every repair round re-verifies the set. A revision re-attaches dropped atoms. Consolidation runs again after repair. | `B/engine/pipeline.py:406, 423-427, 455-456` |
| 913bea2 | Merged changes are re-judged with all their atoms. | `B/engine/pipeline.py:474-476, 349-367` |
| 913bea2 | A judge outage counts as not judged. Conflicts stay with a person. | `B/engine/pipeline.py:287-290, 311-313, 331-334` |
| 913bea2 | `verify=False` runs the V0 guard. | `B/engine/verify.py:528-546`; `B/engine/pipeline.py:255, 345-347, 374-377` |
| 913bea2 | `require_human_signoff=False` auto-releases. | `B/engine/pipeline.py:555-576` |
| 913bea2 | Metrics split: rejected_by_human / withdrawn_by_machine, repair_calls / repaired_and_included, extension_rate_proposed, judge_calls, no 2000-call limit. | `B/engine/pipeline.py:601-642`; `B/store/blackboard.py:329-342` |
| 913bea2 | Settings changes after a run mark stages stale and withdraw the release. | `B/engine/pipeline.py:136-164`; `B/api/app.py:294-308` |
| 21c6b5b | Each claim is judged on its own, also a duplicate. | `B/engine/pipeline.py:383-387` |
| 21c6b5b | Only valid claims merge (`_ready`), and the judged-supported one is kept (`_rank`). | `B/engine/consolidate.py:25-35, 40, 61` |
| 21c6b5b | A machine withdrawal restores the absorbed changes. | `B/engine/pipeline.py:450, 479-490` |
| 21c6b5b | Consolidation neither merges nor relabels rebase items. | `B/engine/consolidate.py:102-103`; `B/engine/pipeline.py:469` |
| 21c6b5b | A partial verdict means review. | `B/engine/pipeline.py:318, 335-336` |
| 21c6b5b | Release needs every stage current; atom edits withdraw the release. | `B/engine/pipeline.py:166-181, 905-908`; `B/api/app.py:318-334` |
| 21c6b5b | A withdrawal recompiles the artefacts as a draft. | `B/engine/pipeline.py:132-134`; `B/compile/docs.py:73-74` |
| 21c6b5b | Auto-release never replaces a sign-off. | `B/engine/pipeline.py:564-565` |
| 21c6b5b | A judge outage verdict is kept, not re-called. | `B/engine/pipeline.py:360` |
| 21c6b5b | Metrics count machine work only. | `B/engine/pipeline.py:605, 635-636` |
| 21c6b5b | Rebase apply checks the provider first and marks an incomplete re-run. | `B/engine/pipeline.py:784-785, 883-889` |
| 21c6b5b | Blind snapshot. | `B/engine/pipeline.py:644-656` (other area) |

## 2. Verification of the tool session's claims (my area)

| Claim | Verdict | Evidence |
|---|---|---|
| Order verify -> consolidate -> repair | **confirmed** | `B/contracts.py:104-109`; `run_all` follows STAGE_ORDER (`B/engine/pipeline.py:540-554`). Probe P1b: intake, retrieve, propose, verify, consolidate, repair, compile, conformance. After repair, consolidation runs again when a revision or a withdrawal happened (`:455-456`). The workbench stepper uses the new order (`frontend/src/api.ts:159`). |
| A duplicate (class, property) is a set-level finding; each claim is still judged on its own | **confirmed** | `B/engine/verify.py:510-519` (`set_level=True`; property elements only, class changes are merged by consolidation without a V5 finding: `B/engine/consolidate.py:13-18`). Judging: `B/engine/pipeline.py:383-387`. P2: each of three duplicate proposals got one judge call in verify, and no repair call was made. |
| Only valid claims (no error of their own, not rejected by the judge) are merged; the judged-supported one is kept | **confirmed, with nuance** | `_ready` (`B/engine/consolidate.py:25-29`) excludes any non-set-level error, including T2 "unsupported" or a named facet. A partial verdict without a facet, or a judge outage (both warnings), can still merge. `_rank` (`:32-35`): judged-supported first, then the strongest obligation, then confidence. |
| Merged changes are judged again with all their atoms | **confirmed** | `B/engine/pipeline.py:474-476` (rejudge set), `:360-366`. P2: the merged change was judged twice (verify, consolidate), and the last judge prompt holds every atom statement. Test: `test_duplicates_consolidated.py:72-78`. |
| A machine withdrawal of a merged change restores what it absorbed | **confirmed, gap** | `B/engine/pipeline.py:443-450, 479-490`. P4b: the absorbed change is restored as "proposed", then auto-accepted. The keeper's own claim, though, is withdrawn with it: a1 is "addressed" alone but "unaddressed" when merged with a2 (scripted judge rejects the two-atom claim, mock repairer withdraws on T2). See NEW-P1. No test exercises the restore path (`grep restore tests/` finds only a docstring). |
| Nothing is auto-accepted without a "supported" verdict; an outage or a partial verdict means review | **confirmed while the judge is on** | `B/engine/pipeline.py:317-318, 331-336`. P8: outage -> "the judge was unavailable (T2): not judged"; partial -> "the judge found the change only partly supported by its atoms (T2)"; no repair call in either case. With `attribution_check=False` (the -T2 ablation) auto-acceptance needs no verdict, by design (`:331, :335`). The outage verdict is kept for the rest of the run, not only "within a pass" (`:360`). |
| Conflicts and rebase items stay with a person | **confirmed** | Guards in `_decide`: `B/engine/pipeline.py:309-313`. Repair exclusion: `:408-412`. No relabel: `:469`. Conflict instead of merge: `B/engine/consolidate.py:100-103`. Tests: `test_t2_after_consolidation.py:122-130`; `test_duplicates_consolidated.py:81-100, 115-125`; `test_rebase.py:102-115`. P12 mutation: with the rule:rebase guard removed, the scenario of `test_rebase.py:102-115` ends `auto_accepted` (with the guard: needs_review by rule:rebase), so the rewritten test can fail. |
| Each repair round starts from a fresh verification; repair never drops an atom | **partly** | The fresh verification is `B/engine/pipeline.py:406`. A revision re-attaches dropped links: `:423-427`. P9: a repairer that keeps only the first atom gets "re-attached atoms the repair dropped: a2" in every round. A withdrawal still removes the change and its atoms' coverage (by design), including the keeper's own atoms after a merge (NEW-P1). |
| `verify=False` runs only a well-formedness guard; conformance still measures the outcome | **confirmed** | `B/engine/verify.py:528-546` (V0: every term an absolute IRI); `B/engine/pipeline.py:345-347`. B1 is skipped in propose (`:255`), the run logs a note (`:374-377`) and the decision note says so (`:339`). P3: checks {V0} (+T2 with the judge on); notes "symbolic verification switched off (condition)"; conformance C1-C8 still ran. With the judge on, a T2 error is still repairable, so repair still runs. |
| `require_human_signoff=False` auto-releases, labelled as such | **confirmed** | `B/engine/pipeline.py:555-576` and `B/compile/docs.py:69-70`. P3: signoff by `rule:auto-release`, with the note "released without human review (require_human_signoff is off); 5 change(s) in the review queue are not part of the profile". The review stage is "skipped" and the README artefact says "Released automatically, without human review". A later decision withdraws it, and the README then says "Draft". No auto-release when non-conformant or a rebase is pending (`:566-569`). |
| Metrics: rejected_by_human, withdrawn_by_machine; repair_calls, repaired_and_included; extension_rate, extension_rate_proposed; judge_calls | **confirmed; definition changed** | `B/engine/pipeline.py:601-642`. **extension_rate** is now minted properties *and classes* over *all* included changes except usage notes (`:615-619`). @5ffd56e it was minted properties over included property-level changes (`:463, :473`). **extension_rate_proposed** is the same share over the non-superseded *machine* changes, whatever their decision (`:605`). judge_calls and repair_calls include cached replays (`:621, :639`). P10: on the demo, every metric shared with the 5ffd56e record is identical, plus extension_rate_proposed 0.5 and judge_calls 10. |
| A release needs every stage current | **confirmed at sign-off; gap afterwards** | `B/engine/pipeline.py:166-181, 905-908`. P5: after a person emptied the queue -> "stages not current: compile, conformance". Every decision makes compile and conformance stale, even without a sign-off (`:121-124`). Re-running intake, retrieve or compile alone after a sign-off keeps the release while later stages go stale (P11). Re-running intake alone also resets machine dispositions (P13-intake). See NEW-P3. |
| A later decision, atom edit, title or settings change withdraws it, logged, artefacts recompiled as a draft | **confirmed** | Decisions: `B/engine/pipeline.py:676, 702, 721, 919-920`. Atoms: `:162-164` via `B/api/app.py:325, 334`. Settings and title: `:146-160` via `B/api/app.py:307`. Withdrawal, log and recompile: `:120-134`. P5: after each of a title, a top_k and an atoms change, the sign-off is None, the log says "The sign-off was withdrawn: ..." and the README says "Draft". A re-sign-off is refused until the stale stages run. Only the documentation carries the draft/released label (`B/compile/docs.py:69-74`). |

Rebase (area file, no explicit claim in the message):
- Each claim of 40a5d5d is confirmed by the code and by the passing tests `test_rebase.py:62-172`:
  - preview changes nothing (the state hash is unchanged);
  - cancel;
  - a stale plan is refused (`:772-773`);
  - a pending plan blocks sign-off (`:169-170`);
  - choices and defaults, a human decision never undone by default (`B/engine/rebase.py:80-87`);
  - a change the new base makes illegal is never kept by default (`:130-137`);
  - intake is redone and covered claims are re-checked (`:192-217`);
  - repair is skipped (`B/engine/pipeline.py:876-878`).
- Gap: the choice "manual" on an atom-level item does nothing (NEW-P2).

The synthetic demo at 21c6b5b:
- All 10 changes are identical in kind, atoms, status and verbalisation to the paper's 5ffd56e record
  (`paper/inputs/demo-materials-testing-lab-5ffd56e-2026-11-14.json`; probe P10b).
- Dispositions, conformance verdict and delta counts are unchanged.
- Only the auto-accept notes add "judged supported".
- Table 3 and README line 74 therefore hold.

## 3. README tool issues in this area

| Id | Status at 21c6b5b | Evidence |
|---|---|---|
| A2 | **fixed** | `verify` is read at `B/engine/pipeline.py:255, 339, 345-347, 374-377`, and `require_human_signoff` at `:555-556`. The docstring is corrected (`B/contracts.py:602-603`). `tests/test_conditions.py:28-76`; P3. |
| A5 | **fixed** | Merged changes are re-judged (`B/engine/pipeline.py:474-476`). `_decide` requires a supported T2 while the judge is on (`:317-318, 331-336`). `tests/test_t2_after_consolidation.py:66-119`; P2, P8. |
| A6 | **fixed** (residual NEW-P1) | Consolidation comes before repair (`B/contracts.py:104-109`). The set-level V5 is not repairable (`B/engine/verify.py:523-525`; `B/engine/pipeline.py:384, 410, 418`). `tests/test_duplicates_consolidated.py:55-69`; P2 (0 repair calls). |
| A7 | **fixed** | `B/engine/pipeline.py:309-310, 411, 469`; `B/engine/consolidate.py:102-103`. `tests/test_rebase.py:102-115` (P12: fails without the guard). |
| A8 | **changed** | The default is fixed: covered claims are re-checked against the new base (`B/engine/rebase.py:208-217`), the default is repropose (`:215`), and the atom is re-proposed and re-checked by B1 (`B/engine/pipeline.py:815-820, 868-869, 255`). Still present when a person picks "manual" for the atom item: nothing happens (`:812-826`), the claim stays and sign-off is allowed (P13, NEW-P2). |
| A9 | **still present** | `release_blockers` (`B/engine/pipeline.py:166-181`) checks the plan, open changes, conformance and stage currency, not unclear or unaddressed atoms. P6: sign-off succeeded with 5 unaddressed demo atoms after a person rejected the queued mints. |
| B19 | **partly fixed** | (1) Still present: `edit_change` records a failing version as accepted with the note "edited and accepted", without "despite failing checks" (`B/engine/pipeline.py:697`; P7: V1 failed). The log payload and the change's verification do list the failure (`:699-701`). (2) Fixed: atom edits through the API withdraw the sign-off (`B/api/app.py:325, 334` -> `B/engine/pipeline.py:162-164`). (3) Fixed: the conflict note is no longer overwritten (`:311-313`; `test_duplicates_consolidated.py:99-100`). |
| C1 | **changed** | New definition: minted properties and classes over included non-usage-note changes (`B/engine/pipeline.py:615-619, 632`), plus `extension_rate_proposed` (`:605, 633`). The development runs used the old one (@5ffd56e `:463, :473`; at 2b92d77 per `digests/pilot.md` 1(c)). |
| C2 | **fixed in the metrics** | `rejected_by_human` / `withdrawn_by_machine` (`B/engine/pipeline.py:630-631`). The status is still "rejected" for both (`B/contracts.py:86`; `B/engine/pipeline.py:445-446`). A rebase "withdraw" counts as human, since the applying person decides (`:828-830`). |
| C3 | **fixed** | `repaired` is replaced by `repair_calls` and `repaired_and_included`, the latter LLM revisions that are included (`B/engine/pipeline.py:621, 634-636`). |
| Q6 | **resolved by the code** | A partial verdict and an outage now mean review; merged changes are judged; docs/design.md:28 matches. The paper text must change (see the table). |
| Q7 | **changed** | TC/TR can be configured (`verify=False` plus `--no-judge`, `--repair-rounds`, `--no-retrieval`: `scripts/run_reference_case.py:55-58, 99-101`). SX is still not implemented; HR is still open. |

## 4. New issues at 21c6b5b (area)

- **NEW-P1 (confirmed by probe P4b; medium): a machine withdrawal of a merged change loses the keeper's own claim.**
  - Consolidation mutates the keeper in place (`B/engine/consolidate.py:61-94`).
  - `_restore_absorbed` restores only `merged_from` (`B/engine/pipeline.py:479-490`).
  - When the judge rejects the merged claim and the repairer withdraws it, the absorbed changes come back. The keeper's
    pre-merge claim, which was valid and judged supported alone, does not.
  - Its atoms become unaddressed.
  - The judge in the probe is scripted (it rejects multi-atom claims). With a model judge and a model repairer the
    path is plausible: `tests/test_duplicates_consolidated.py:44-45` records a model that withdrew duplicates.
  - Fix idea: keep a pre-merge copy of the keeper and restore it too, or exclude merged keepers from "withdraw".
- **NEW-P2 (confirmed by probe P13; medium-low): rebase "manual" on an atom-level item is a no-op.**
  - Affects `covered_claim_lost`/`weakened` and `intake_changed`: these items have no change, and `rebase_apply`
    `continue`s (`B/engine/pipeline.py:812-826`).
  - The machine "covered by the base" claim survives, nothing is queued, and sign-off is allowed.
  - `docs/dcat-versions.md:238-239` says "manual puts a machine-decided change in the review queue".
- **NEW-P3 (confirmed by probes P11 and P13-intake; medium-low; pre-existing since 5ffd56e, `run_intake` unchanged):
  re-running a single stage after a sign-off keeps the release.**
  - Running intake, retrieve or compile alone after a sign-off marks the later stages stale but does not withdraw the
    release: `set_stage(..., cascade)`, `B/engine/pipeline.py:111-118`; no `_withdraw_release` in `:191-219, 502-528`.
    The README artefact keeps "Released by ...".
  - Re-running intake alone also overwrites machine assessments with the bare intake result
    (`B/engine/pipeline.py:194-199`; default disposition `needs_change`, `B/contracts.py:332`).
  - On the signed demo, the 4 covered_by_base atoms and the 1 out-of-scope atom become "unaddressed" while the
    sign-off stands.
  - The workbench runs any stage alone (`B/api/app.py:336-347`).
- **NEW-P4 (low, doc): `docs/design.md:33` rebase row is stale.**
  - The row still reads "machine changes with a migration finding go to needs_review".
  - The code applies per-item choices with defaults keep, withdraw, replace, manual and repropose
    (`B/engine/rebase.py:80-218`; `B/engine/pipeline.py:811-855`).
- **NEW-P5 (cosmetic): stale comments and docstrings.**
  - The comments of the `Stage` literal still list verify, repair, consolidate (`B/contracts.py:97-99`).
  - The module docstring says "Anything else goes through bounded repair" and "Nothing is released until a human
    signs off" (`B/engine/pipeline.py:8-11`). Partial, outage, low-confidence and D1 changes go straight to review,
    duplicates go to consolidation, and the auto-release condition exists.
- **Note (by design):**
  - Every human decision makes compile and conformance stale, even without a sign-off (`B/engine/pipeline.py:121-124`).
    So after review a person must re-run compile and conformance before signing off (P5).
  - A judge outage verdict is kept until verify runs again, or the change is merged or revised (`:360`).

## 5. Paper impact

The development runs 1-3 keep their history: they ran the engine before DCAT-state pinning with the leak and the old
order and definitions. Statements about them stay; only statements about the described tool change. All replacement
numbers have a source (`B/contracts.py:608, 612`; `paper/inputs/tests-main-21c6b5b-2026-11-14.txt:5`). The probe counts
are verification only, not paper text.

| File:line | Current (short) | Replacement fact | Anchor at 21c6b5b |
|---|---|---|---|
| figures/pipeline.tex:23-25 | nodes "4. Verify ...", "5. Repair failing changes, at most three rounds", "6. Consolidate: one element per class and property" | Order 4 Verify -> 5 Consolidate -> 6 Repair. Node 5 (dashed: it calls the judge): merge valid duplicates per class and property, judge merged changes again, conflicts to a person. Node 6 (dashed): repair changes with an error of their own, at most three rounds, each from a fresh verification. | `B/contracts.py:104-109`; `B/engine/pipeline.py:459-477, 400-457`; `B/contracts.py:608` |
| figures/pipeline.tex:38-41 | o4->o5 flow, o5->o4 dashed loop, o5->o6, o6->o7 | o4->o5 (verify->consolidate), o5->o6 (consolidate->repair), o6->o7 down. Dashed o6->o4: each round verifies the set again. Dashed o6->o5: consolidation again after a revision or withdrawal. | `B/engine/pipeline.py:406, 455-456` |
| figures/pipeline.tex:44-45 | queue: "errors after repair, low confidence, conflicts, later-DCAT terms" | Add "no supported verdict" (and "rebase items"). | `B/engine/pipeline.py:306-343` |
| sections/04-pipeline.tex:15-18 | "A change with an error goes to repair~(5) and, still failing, to the review queue~(9), as do conflicts, changes below the confidence threshold and ..." | A change with an error of its own goes to repair (6) and, still failing, to the queue (9). So do conflicts, changes without a "supported" verdict, changes below the confidence threshold and, by default, later-DCAT terms. Duplicates go to consolidation (5), never to repair. | `B/engine/pipeline.py:306-343, 408-412`; `B/engine/verify.py:516-525` |
| sections/04-pipeline.tex:22 | "the model proposes~(3), judges~(4) and repairs~(5)" | Proposes (3), judges (4, again for merged and revised changes in 5 and 6) and repairs (6). | `B/engine/pipeline.py:383-387, 474-476, 432-437` |
| sections/04-pipeline.tex:55 | "Only a change without an error reaches the judge T2" | Only a change without an error of its own reaches T2; a duplicate (a set-level finding) is judged on its own. | `B/engine/pipeline.py:383-387`; `B/engine/verify.py:523-525` |
| sections/04-pipeline.tex:56-57 | "... partially supported or an unavailable judge is a warning." | The severities are unchanged, but either warning keeps the change in review: nothing is auto-accepted without a "supported" verdict while the judge is on. | `B/engine/pipeline.py:287-301, 317-318, 331-336` |
| sections/04-pipeline.tex:61-65 | "A change with an error goes to repair ... Consolidation then merges compatible changes ..." | Swap the order. **Consolidation first** merges compatible changes on one class and property, only those without an error of their own; it keeps the judged-supported one with the strongest obligation and tightest bounds and judges the merged change again with all its atoms. It queues as a conflict an incompatible group, or one with a person's decision or a rebase item. **Then repair**, at most three rounds, each from a fresh verification of the set: a revision keeps every atom and is verified, judged and decided again; a withdrawal restores any change it had absorbed. Consolidation runs again after repair. | `B/engine/consolidate.py:25-35, 38-110`; `B/engine/pipeline.py:400-490`; `B/contracts.py:608` |
| sections/04-pipeline.tex:66-68 | "auto-accepted when it has no error, automatic acceptance is on and ... confidence is at least 0.5 ... Other warnings never block" | Add "and, while the judge is on, it is judged supported". "Other warnings never block" becomes "warnings other than the judge's and D1's never block". | `B/engine/pipeline.py:319-342`; `B/contracts.py:612` |
| sections/04-pipeline.tex:69 | `\todo{tool: duplicates repaired; merged changes skip T2 (Q22)}` | Remove: A5 and A6 are fixed. Optionally add a limit for NEW-P1. | `B/contracts.py:104-109`; `B/engine/pipeline.py:474-476` |
| sections/04-pipeline.tex:92-94 | "Release requires an empty queue, a current conformance report that is not non-conformant and a recorded sign-off ...; any later decision withdraws the sign-off." | Release requires an empty queue, no pending rebase plan, every stage current (done or skipped) and a report that is not non-conformant; it records a sign-off with a hash of the included changes. Any later decision, atom edit, title or settings change withdraws it, logs this and recompiles the artifacts as a draft. Caveat NEW-P3. | `B/engine/pipeline.py:166-181, 905-917, 120-164`; `B/api/app.py:307, 325, 334`; `B/compile/docs.py:69-74` |
| sections/04-pipeline.tex:96 | `\todo{tool: unresolved atoms do not block sign-off (Q22)}` | Keep: A9 is still present (P6). | `B/engine/pipeline.py:166-181` |
| sections/04-pipeline.tex:105 | "The 98 tests pass without a model." | "The 170 tests pass without a model." (cross-area: tool facts) | `paper/inputs/tests-main-21c6b5b-2026-11-14.txt:5` |
| sections/04-pipeline.tex:107-110 | "A rebase moves ... Every change is compared under both bases; ... machine changes with a finding that asks for a decision are flagged for review ..." + todo A7/A8 | A rebase is a staged plan. A preview compares every live change and every atom's class and covered-by-base claim under both bases, offers each finding its choices with a default, and changes nothing. Apply executes a person's choices, then redoes intake, retrieval, re-proposal of the affected atoms, verification and consolidation under the new base, skips repair, recompiles and checks conformance. A pending plan blocks release, and items left to a person stay in the queue. Remove the A7/A8 todo; optionally add one for NEW-P2. | `B/engine/rebase.py:16-21, 80-218`; `B/engine/pipeline.py:739-896, 169-170, 309-310`; `B/engine/consolidate.py:102-103` |
| sections/04-pipeline.tex:111 | "% the described commit is 5ffd56e (main)" | The described commit is 21c6b5b (Q14 is still open). | git log main-wt2 |
| sections/03-problem.tex:112-114 | "... and only a person's sign-off releases the extension." | Add a qualifier: by default; the ablation `require_human_signoff=False` releases a conformant profile automatically and says so. Or keep E3 and state the ablation in Sect. 6. | `B/contracts.py:613`; `B/engine/pipeline.py:555-576`; `B/compile/docs.py:69-70` |
| sections/03-problem.tex:129-130 | "the model may withdraw it in repair (stored as rejected), and a repair, an edit, a merge or a new proposal supersedes it" | Unchanged; may add that a withdrawal of a merged change returns the absorbed changes to proposed, and that a rebase replacement also supersedes. Update the anchors. | `B/engine/pipeline.py:443-450, 479-490, 834-854`; `B/contracts.py:86, 89` |
| sections/03-problem.tex:106 | "each class and property has one element" (src V5 :493-510) | Unchanged. Anchor: the set-level V5 plus consolidation. | `B/engine/verify.py:503-520`; `B/engine/consolidate.py:38-95` |
| sections/06-setup.tex:19-21 | "TC and TR ... need a verification switch that is defined but never read." | TC/TR can now be configured. With verification off only the well-formedness guard V0 runs (every term an absolute IRI), B1 is skipped, and conformance still measures the outcome. The judge and repair run unless switched off too, and the confidence threshold and consolidation still apply. The run script exposes `--no-verify`, `--no-judge`, `--repair-rounds` and `--no-retrieval`. Not run yet; definition: verify (Q7). | `B/contracts.py:607`; `B/engine/pipeline.py:255, 337-339, 345-347, 374-377`; `B/engine/verify.py:528-546`; `scripts/run_reference_case.py:55-58, 99-101` |
| sections/06-setup.tex:17-18 | "$-$REP drops repair and $-$T2 the judge, so a change without a symbolic error is decided without a verdict." | Unchanged (true). Update the anchors. | `B/engine/pipeline.py:276-278, 331, 335, 405`; `B/contracts.py:608-609` |
| sections/06-setup.tex:24 | "Other runs stop at the review queue, ..." | Unchanged; optionally "(require_human_signoff stays on; its auto-release ablation is not used)". | `B/engine/pipeline.py:555-559`; `B/contracts.py:613` |
| sections/06-setup.tex:69-71 | "the extension rate, minted properties over included property-level changes, beside the reference delta's" | New code definition: minted properties and classes over all included changes except usage notes. Also available: the same share over the machine's non-superseded changes, rejected and queued ones included. Verify that the reference deltas' rate is computed the same way (classes included). | `B/engine/pipeline.py:605, 615-619, 632-633` |
| sections/06-setup.tex:72-74 | "For E3: auto-accepted changes, decisions by who made them, and the review load ..." | Add: withdrawals by the repairer counted apart from a person's rejections. | `B/engine/pipeline.py:627-631` |
| sections/06-setup.tex:78 | "Cost counts calls without cached replays, input tokens and hours." | Unchanged; optionally judge and repair calls. All calls are counted, with no 2000 limit. | `B/engine/pipeline.py:610, 621, 634-641`; `B/store/blackboard.py:329-342` |
| sections/07-results.tex:80-82 | "A change the judge wrongly finds unsupported goes to repair, where it can be revised or withdrawn ..." | Still true. Add: a partial verdict without a named facet keeps it in review without repair; a wrong rejection of a merged change can also withdraw the keeper's own claim (NEW-P1). | `B/engine/pipeline.py:293-301, 335-336, 408-412, 443-450, 479-490` |
| sections/07-results.tex:101-105 | "duplicates sent to repair before consolidation ... the last two are open (Sect.~\ref{sec:discussion})" | History stays. The duplicate item is fixed in the described tool: consolidation now precedes repair. The C7 item is cross-area (conformance digest). | `B/contracts.py:104-109`; `B/engine/verify.py:523-525` |
| sections/08-discussion.tex:53-54 | "It is not rerun after consolidation (Sect.~\ref{sec:check}), although it alone weighs facets ..." | It judges each claim on its own and a merged change again with all its atoms, and no change is auto-accepted without its "supported" verdict; it alone weighs facets beyond the obligation. | `B/engine/pipeline.py:383-387, 474-476, 331-336` |
| sections/08-discussion.tex:66-69 | "... but not verification, whose switch is never read, so what the symbolic checks contribute is not measured." | Verification can now be switched off, leaving a well-formedness guard; until TC and TR run, the checks' contribution is not measured. Keep the todo (Q7). | `B/engine/pipeline.py:345-347`; `B/engine/verify.py:528-546` |
| sections/08-discussion.tex:70-71 | "Repair can lose a legitimate change: ... each gets a duplicate error and may be withdrawn before consolidation would merge them." | Consolidation now merges duplicates before repair, and the repairer never sees a duplicate finding. Remaining limit (verify, NEW-P1): a machine withdrawal of a merged change restores the changes it absorbed but withdraws the keeper's own claim with it. | `B/contracts.py:104-109`; `B/engine/verify.py:523-525`; `B/engine/pipeline.py:479-490`; `B/engine/consolidate.py:61-94` |
| sections/08-discussion.tex:60 | `\todo{tool: sign-off ignores unresolved atoms (Q22)}` | Keep: A9 is still present. | `B/engine/pipeline.py:166-181` |
| sections/11-appendix.tex:133-135 | T2 row: "unsupported, or a facet named unsupported; \emph{warning:} partially supported, or the judge unavailable" | Keep the conditions; add that a T2 warning keeps the change in review (no auto-acceptance without "supported"). | `B/engine/pipeline.py:287-301, 331-336` |
| sections/11-appendix.tex:125-128 | V5 row: "...; two live changes on one element; ..." | "two live changes on one property element (set-level: consolidation merges them or a person decides; never sent to repair)". | `B/engine/verify.py:503-525`; `B/engine/consolidate.py:38-110` |
| sections/11-appendix.tex:99-102 | V1 row: "\emph{warning:} a term not retrieved, a non-IRI value-list entry" | A non-IRI value-list entry is an error at 21c6b5b (cross-area: checks). | `B/engine/verify.py:156-159` |
| sections/11-appendix.tex:25-31 | Table 3 caption: 4 covered, 1 out of scope, 5 of 10 auto-accepted, 5 mints at 0.45 wait | Unchanged at 21c6b5b (probe P10b); refresh the DEMO5 source and the anchors. | `B/engine/pipeline.py:319-342`; P10b |
| sections/12-appendix-cd.tex:97 | Table 7: "Atoms and extension rate as in Sect.~\ref{sec:setup}" | History. Once Sect. 6 adopts the 21c6b5b definition, say "extension rate as these runs' engine computed it: minted properties over included property-level changes". | @5ffd56e `B/engine/pipeline.py:463, 473`; `digests/pilot.md` 1(c) (2b92d77) |
| sections/12-appendix-cd.tex:27-28 | Table 6: "Ext.: extension rate, the reference delta's under the case name" | Same definition as Sect. 6 (classes included) for runs and references. | `B/engine/pipeline.py:615-619` |
| sections/12-appendix-cd.tex:153-156 | tab:steps rows "5.~Repair", "6.~Consolidate" | Swap to "5. Consolidate", "6. Repair" if Fig. 1 is renumbered. | `B/contracts.py:104-109` |
| sections/12-appendix-cd.tex:114 | src comment: "(T2 only without an error, partially supported only warns)" | T2 only without an error of its own; a partial verdict keeps the change in review. | `B/engine/pipeline.py:383-387, 335-336` |
| sections/01-introduction.tex:49-51 | "the rebase of Sect.~\ref{sec:impl} compares each change under both bases." | The staged rebase compares each change, and each atom's class and covered-by-base claim, under both bases before anything changes. | `B/engine/rebase.py:90-218`; `B/engine/pipeline.py:739-756` |
| sections/00-abstract.tex:19-20; sections/09-conclusion.tex:8-9 | "only a person's sign-off releases the extension" | True for the default; optional qualifier, since an auto-release ablation exists and is labelled. | `B/contracts.py:613`; `B/engine/pipeline.py:555-576` |
| README.md:338 (A2) | "Dead switches ... never read" | Fixed. | `B/engine/pipeline.py:345-347, 555-556` |
| README.md:341-342 (A5, A6) | "judge bypassed ..."; "Duplicates go to model repair ..." | Fixed; residual NEW-P1. | `B/engine/pipeline.py:474-476`; `B/contracts.py:104-109` |
| README.md:343-344 (A7, A8) | rebase flags reset; lost claims kept | A7 fixed; A8 fixed for the default, still present with "manual" (NEW-P2). | `B/engine/pipeline.py:309-310, 812-826`; `B/engine/rebase.py:208-217` |
| README.md:345 (A9) | sign-off ignores atoms | Still present. | `B/engine/pipeline.py:166-181` |
| README.md:369 (B19) | three sub-issues | (1) still present; (2) and (3) fixed. | `B/engine/pipeline.py:697, 311-313`; `B/api/app.py:325, 334` |
| README.md:376-378 (C1-C3) | old metric definitions | C1 changed (new definition); C2 split in the metrics; C3 replaced. | `B/engine/pipeline.py:615-636` |
| README.md:247-249 (Q6) | "partially supported ... only warn, and a change cleared by consolidation can be accepted without any judge verdict" | Resolved in the code at 21c6b5b; the paper text changes accordingly. | `B/engine/pipeline.py:331-336, 474-476` |
| README.md:255 (Q7) | "TC/TR need a working verify switch (`PipelineConfig.verify` is never read)" | The switch works (V0 guard); TC/TR are configurable via the run script. | `B/engine/verify.py:528-546`; `scripts/run_reference_case.py:55-58` |
| README.md:75 | "PipelineConfig; at 5ffd56e lines 589-602" | At 21c6b5b lines 601-625 (same defaults: top_k 8, 3 rounds, 1 vote, 0.5, 4 parallel calls). | `B/contracts.py:601-625` |
| README.md:329-331 | "checked ... on a worktree of `main` at **5ffd56e**" | Re-checked at 21c6b5b for this area (this digest). | |
