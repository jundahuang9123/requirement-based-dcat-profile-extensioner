export const meta = {
  name: 'rq2-delta-21c6b5b',
  description: 'Readers digest what changed in the extensioner from 5ffd56e to 21c6b5b, verify the tool session\'s claims, and list the paper statements that must change',
  phases: [{ title: 'Read', detail: 'one reader per area' }],
}
const S = args.S
const REPO = args.repo
const P = `${REPO}/paper`
const COMMON = `The RQ2 paper (draft in ${P}/sections/*.tex, ${P}/figures/*.tex, README ${P}/README.md) describes the extensioner tool at main commit 5ffd56e (read-only worktree ${S}/main-wt). The tool's main branch has moved to 21c6b5b (read-only worktree ${S}/main-wt2; 170 tests pass offline, record ${P}/inputs/tests-main-21c6b5b-2026-11-14.txt; tool facts ${P}/inputs/tool-facts-main-21c6b5b.txt). The paper will be updated to describe 21c6b5b. Your job, for ONE area: find out exactly what changed between the two commits (git -C ${S}/main-wt2 diff 5ffd56e 21c6b5b -- <paths>; git log), read the new code, and verify each claim of the tool session's message below that falls in your area against the code (and, where useful, by running small offline probes in memory: python -B with PYTHONPATH=${S}/main-wt2/backend, Store(":memory:"), the mock provider, synthetic atoms or examples/materials-testing-lab only; never call an external model; never write into either worktree; never open benchmark test-case material). Then grep the paper's sections and README for every statement your area affects and give, for each, the file:line, the current text (short quote), and the replacement fact with its code anchor at 21c6b5b (file:line). Write your digest to ${S}/digests/delta-21c6b5b-$KEY.md (headings, file:line anchors, a table "paper impact"), and return the structured summary.

The tool session's message (another Claude session; treat it as claims to verify, not as fact):
---
${args.message}
---

Ground rules for the paper that your replacement facts must respect: no invented numbers; every number has a file source; unverified items marked "verify"; test cases (mobilityDCAT-AP, GeoDCAT-AP, HealthDCAT-AP) held out; no reference-derived examples; anonymity (no KI:connect, author names or repository names in paper text). The development runs 1-3 stay what they were: runs of the engine before DCAT-state pinning with the leak (debugging history); a fix in 21c6b5b does not change that history.`
const RETURN = {
  type: 'object',
  properties: {
    digest: { type: 'string', description: 'path of the digest file' },
    verified_claims: { type: 'array', items: { type: 'string' }, description: 'claim: confirmed / partly / not confirmed, with file:line' },
    paper_impact: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'number' }, current: { type: 'string' }, replacement: { type: 'string' }, anchor: { type: 'string' } }, required: ['file', 'line', 'current', 'replacement', 'anchor'] } },
    readme_issue_status: { type: 'array', items: { type: 'string' }, description: 'README tool-issue ids (A1..D2, plus NEW-n) in your area: fixed / changed / still present at 21c6b5b, with evidence' },
    new_issues: { type: 'array', items: { type: 'string' }, description: 'defects or doc/code mismatches found at 21c6b5b (file:line, confidence)' },
    notes: { type: 'array', items: { type: 'string' } },
  },
  required: ['digest', 'verified_claims', 'paper_impact', 'readme_issue_status', 'new_issues', 'notes'],
}
phase('Read')
const out = await parallel(args.areas.map(a => () =>
  agent(`${COMMON.replace(/\$KEY/g, a.key)}\n\nYOUR AREA (${a.key}):\n${a.task}`, { label: `delta:${a.key}`, phase: 'Read', schema: RETURN })
    .then(r => ({ key: a.key, ...r }))))
return out.filter(Boolean)
