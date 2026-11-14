export const meta = {
  name: 'rq2-edit-to-budget',
  description: 'Section editors cut the RQ2 draft to its word and page budget, shorten markers and apply cross-cutting corrections',
  phases: [{ title: 'Edit', detail: 'one editor per file group' }],
}
const S = args.S
const REPO = args.repo
const P = `${REPO}/paper`
const COMMON = `You are one of several section editors of the RQ2 paper draft (Springer LNCS, anonymous, ESWC 2027 research track), the companion of the RQ1 paper. The full draft exists and compiles; it is too long. RQ1's body (Sects. 1-9) ends on page 15; ours ends on page 19, and its appendix runs 11 pages against RQ1's 3.5. Your job: edit ONLY your files so that they meet the budgets below, keeping every required fact, and apply the cross-cutting corrections. Cut; do not add content, facts, numbers or citations.

Read first: ${S}/outline-final.md sections 0 (rules, voice, placeholders, which tool version, "do not write") and 5 (page plan), the brief(s) of your file(s) in section 6, and ${S}/outline-addendum.md. Then read your file(s) and the files that refer to them (grep for their labels in ${P}/sections/*.tex) so that you do not cut something another section points to.

Word counts: measure with  python3 ${S}/scripts/wc_body.py <files>  (prose = running text without comments, markers, citations and floats; floats and markers counted apart). Report before and after.

How to cut, in this order:
1. Markers: every \\todo becomes a short label, at most about 8 words, ending with the question number where one exists: \\todo{conditions: final set (Q7)}. The details live in ${P}/README.md (questions Q1-Q30 and the tool-issue table), so do not repeat them in the text. A \\verify keeps the claim recognizable in at most about 10 words. Never delete a marker whose open point is still in your text; if you cut the sentence it marks, report the marker as removed.
2. Repetition: a fact that another section states in full is referred to, not restated (Sect. 3 defines, Sect. 4 describes the tool, Sect. 6 the conditions and measures, Sect. 8 discusses). Keep the definition where the outline puts it.
3. Detail that belongs in an appendix table or the README (long lists of literature steps, per-check conditions already in Table 4, tool defects already in the tool-issue table): replace it with a pointer (Table~\\ref{...}, Appendix~\\ref{...}).
4. Long sentences: split or tighten any sentence over about 35 words; keep RQ1's voice (concise, exact denominators, "X, not Y" scoping, models judge / program code checks / a person decides).
Keep: every label and every \\ref target others use; every "% src:" comment for a fact you keep (comments do not count and do not print); every \\res slot that still has a sentence; the binding test-case wording of Sect. 5; the disclosure of the development-run leak and contamination; the honesty statements (what is designed versus implemented, what is not built).

Cross-cutting corrections (apply wherever they occur in your files):
- Do not print the plan's names "A-gold" or "A-rq1" (they contain or stand for a banned word); print "reference atoms" and "extracted atoms". The plan names may stay in % comments.
- Check identifiers (V1-V6, D1-D3, T1, T2, B1, C1-C8) are plain text, not \\term{}; \\term{} is for prefixed names and code identifiers.
- The development-run leak: every proposer, repairer and judge prompt printed the atom's source reference (document and locator); the case-naming project title appeared only in the proposer prompt (@5ffd56e B/engine/prompts.py:113-115, :174). Do not write that every prompt printed the title.
- The 98 tests pass at 5ffd56e (offline run record ${P}/inputs/tests-main-5ffd56e-2026-11-14.txt); a \\verify about the tests passing can be replaced by that source in a % src: comment.
- Counterfactual tasks: the key wu2024reciting exists; replace any \\verify{new bib entry: Wu et al. ...} with \\cite{wu2024reciting}.
- The synthetic demo was re-run at 5ffd56e: ${P}/inputs/demo-materials-testing-lab-5ffd56e-2026-11-14.json (same metrics, dispositions and changes as the 0d7aadc record, plus intake lint, per-change checks with D1, and C8); Fig. 3's screenshots are from 5ffd56e.
- Anonymity also in comments: no repository names of the author (visual-profile-editor, requirement-based-dcat-profile-extensioner, reqs_extract_run_store, requirements-benchmark-references), no KI:connect, no institution or person names. Write "the profile editor's repository" or similar in comments.
- No text recycled from RQ1 beyond the four allowed pick-ups (outline 0.3): reword any caption or sentence that copies RQ1 nearly word for word.

Hard rules (never break): no invented numbers, results or citations; every number has a source; unverified content is \\verify; test cases (mobilityDCAT-AP, GeoDCAT-AP, HealthDCAT-AP) nothing beyond what RQ1 reports; no base or reference version chosen; development-run numbers only in Appendix C.1; no reference-derived example (benchmark atom identifier with a generated change) in a committed file; no footnotes, displayed equations, "e.g.", "i.e.", "etc.", "gold", "ground truth", "F1"; American spelling.

Before you finish: compile the whole paper into your own build directory and fix every LaTeX error or overfull box over 5pt that comes from your files:
  cd ${P} && latexmk -pdf -interaction=nonstopmode -outdir=${S}/build-edit-$KEY main.tex
Then report, from ${S}/build-edit-$KEY/main.pdf (pdftotext), on which page your section starts and ends. Other editors work in parallel on other files; ignore their transient errors. Final answer: the structured summary.`

const RETURN = {
  type: 'object',
  properties: {
    files: { type: 'array', items: { type: 'string' } },
    words_before: { type: 'string', description: 'wc_body.py output lines before' },
    words_after: { type: 'string', description: 'wc_body.py output lines after' },
    removed: { type: 'array', items: { type: 'string' }, description: 'content removed or moved, one line each (what, and where it is still stated if anywhere)' },
    markers_removed: { type: 'array', items: { type: 'string' } },
    corrections: { type: 'array', items: { type: 'string' }, description: 'cross-cutting corrections applied' },
    pages: { type: 'string' },
    notes: { type: 'array', items: { type: 'string' }, description: 'anything other editors or the main loop must know' },
  },
  required: ['files', 'words_before', 'words_after', 'removed', 'markers_removed', 'corrections', 'pages', 'notes'],
}
phase('Edit')
const results = await parallel(args.editors.map(e => () =>
  agent(`${COMMON.replace(/\$KEY/g, e.key)}\n\nYOUR FILES AND BUDGETS (${e.key}):\n${e.task}`, { label: `edit:${e.key}`, phase: 'Edit', schema: RETURN })
    .then(r => ({ key: e.key, ...r }))))
return results.filter(Boolean)
