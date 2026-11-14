# Handover: RQ2 paper draft, paused 14 Nov 2026 (about 21:35 UTC)

These are working notes to resume the draft. They are not part of the paper. Atom identifiers are redacted to
`[atom id]`.

## State

- **The draft.** The draft compiles. It was cut to budget: 36 → 29 pages in the committed build without local examples.
  - The body ends on page 17. RQ1's body ends on page 15, so about one page must still go.
  - The text still describes the tool at `main` 5ffd56e.
- **The tool moved on.** The tool's `main` is now 21c6b5b. Its 170 tests pass offline
  (`paper/inputs/tests-main-21c6b5b-2026-11-14.txt`), and its facts are in `paper/inputs/tool-facts-main-21c6b5b.txt`.
  - Four verified digests in `delta-21c6b5b/` list what changed and which paper sentences must change, in their
    "paper impact" tables.
  - The main changes: the leak is closed, the order is verify → consolidate → repair, no auto-acceptance without a
    "supported" verdict, a new extension-rate definition, owl:imports for 8 of 9 bases, and C7 can now fail.
  - New defects found at 21c6b5b are listed there. The most serious is that C7 now raises false errors, which block
    release.
- **Blind pilots.** The development-case pilots at 21c6b5b (leak closed) are committed:
  - the numbers: `paper/inputs/pilot-runs-2026-11-14-blind.md`;
  - the macros `\pilotb{}{}{}` and the table `paper/tables/pilot-blind.tex`;
  - the checker covers 296 values, with 0 mismatches.
  - The rules rows were reproduced here, offline, and match in every cell.
  - These numbers are not yet in the paper text.
- **Review.** The review is paused at its verification step. `review-2026-11-14/findings.json` holds 175 findings from
  six lenses, each with a status:

  | Status | Count | By lens |
  |---|---|---|
  | confirmed | 60 | citations 9, latex 23, numbers 8, rules 7, technical 13 |
  | refuted | 31 | |
  | not yet checked | 84 | reviewer 53, rules 15, citations 8, latex 8 |

  The fix pass must not apply an unchecked finding without verifying it first. Some technical findings concern
  5ffd56e and will be overtaken by the 21c6b5b update.
- **Messages from the tool session.** Any message that arrives from now on is left unread and unacted on until Junda
  says otherwise.

## Next steps, in order (when Junda says to continue)

1. **Verify the 84 unchecked findings.**
   - Script: `workflows/verify-workflow.js`.
   - Each skeptic reads one batch file. Rebuild the batch files from `findings.json`: one file per lens and paper file.
2. **One fix pass per file group.** Script: `workflows/fix-workflow.js`; groups and budgets: `workflows/editors.json`.
   Each fixer applies:
   - the confirmed findings;
   - the 21c6b5b update (the delta digests);
   - the blind pilots (Sect. 7 development-case paragraph with `\pilotb` macros; Appendix C.1 table `pilot-blind.tex`;
     the contaminated runs 1-3 reduced to one sentence);
   - the operations renumbered (5 Consolidate, 6 Repair) in Fig. 1, the text and Table 8;
   - a last cut, so that the body ends on page 15. Measure with `workflows/wc_body.py`.
3. **Re-check the method against 21c6b5b.** Rerun the technical lens of `workflows/review-workflow.js`.
4. **README.**
   - Rewrite the tool-issue table at 21c6b5b: fixed items, still-present items and the new ones from the digests.
   - Update Q14 (described commit: 21c6b5b, not merged into `paper-draft`) and Q16 (the blind pilots replace the
     contaminated table).
   - Regenerate the marker list with `python paper/scripts/list_markers.py`.
5. **Build both PDFs.**
   - Public: a copy of `paper/` without `sections/local/`, saved as `paper/main.pdf`.
   - Full: with the local examples, for chat only.
   - Then commit and push, and send the PDF.

## Things to know

- `paper/inputs/pilot-runs-2026-11-13.md` has a "Qualitative observations" section. It pairs a few atom ids with
  their generated changes.
  - The task's rule allows individual examples in qualitative analysis.
  - The outline is stricter: such examples only in the local, gitignored file.
  - The rules lens flagged it. Junda decides whether to remove that section from the committed input file.
- The workbench figure's screenshots are from 5ffd56e. An in-memory run at 21c6b5b gives byte-identical content for
  the figured change. Only the provenance comment needs updating.
- Merging `main` into `paper-draft` is waiting on Junda (Q14). Do not touch `main`.
