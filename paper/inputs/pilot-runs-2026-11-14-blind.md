<!-- Provenance (paper session, 14 Nov 2026): received from the tool session as a numbers-only file and committed
     verbatim below this comment. Checks made here before use:
     - the two rules (mock) rows were reproduced independently at 21c6b5b, offline, from blind imports of the same two
       development reference sets: identical in every cell, including the kind breakdown, the input sha256 prefixes
       (67e47c2f282ac972, 3a43c65d45034701) and the modality counts (JRC 12/4/1, Stat 13/1);
     - the gpt-oss-120b rows (not re-run here: no model call from this session) are internally consistent: the atom
       counts sum to 17 and 14, the kind counts sum to the included changes, both extension rates follow from the
       kinds and the live changes, uncached calls equal the stop-reason and served-model counts, and the wall times
       match the call timestamps.
     The table is turned into macros by paper/scripts/make_pilot_tables.py and checked by check_pilot_macros.py. -->
# Blind pilot runs on two RQ1 development cases (14 Nov 2026)

Development-case pilots, not the RQ2 evaluation: no gold delta was scored and no person reviewed anything (every
"auto accepted" is a machine decision, so "rejected by human" is 0 by construction). These runs replace runs 1-3
(13 and 14 Nov), which are contaminated (case names and source references reached the prompts) and stay debugging
history only. Numbers only: atom ids, statements, change lists and generated profiles are left out; regenerate them
with scripts/run_reference_case.py from blind imports.

## Setup

- Tool: requirement-based-dcat-profile-extensioner at commit 21c6b5b (main), clean tree.
- Inputs: the default-scored content atoms of benchmark-data/reference-sets-v3/jrc-research.json (17) and
  statdcat.json (14) in jundahuang9123/requirements-benchmark-references, imported with
  scripts/import_rq1_reference.py in blind mode: opaque atom ids, no source references, no case or profile names;
  modality mapping 'map' (the importer's default). Modalities after mapping: JRC 12 unspecified, 4 must, 1 should;
  Stat 13 unspecified, 1 may. The run script refuses inputs that are not blind and scans every
  prompt for the case name, the original atom ids, source locators, reference documents and published-profile names
  (LEAKCHECK).
- Base: DCAT-AP 1.1 (the reference sets' base field), which builds on W3C DCAT 2014 (Recommendation 2014-01-16);
  official SEMICeu shacl-201706 shapes, unmodified. DCAT terms later than DCAT 2014 are flagged for review (D1).
- Model: KI:connect inferenz-gpt-oss-120b through the OpenAI-compatible provider, reasoning_effort medium and
  max_tokens 16000 sent with every call. The endpoint reported the served model under two names (counts per run
  below); that both names are the same weights is **verify**.
- Pipeline: default settings (retrieval with top-k 8, symbolic verification, T2 judge, 1 vote, up to 3 repair
  rounds, auto-accept), one call at a time per run, blind mode on.
- Stores: the two LLM runs used one new store created empty for them, the two rules runs another. Each run is its
  own project and the replay cache is project-scoped, so no run reused another run's answers ("answers replayed
  from other projects": 0 in every run). The two LLM runs ran at the same time against the same endpoint (JRC from
  20:42, Stat from 20:46 UTC), so their wall times include waiting on each other.
- Rules baseline: the offline mock provider (lexical rules proposer, repairer and judge), same commit and inputs.

## Results

| case | provider | wall s | calls (cached) | judge calls | in / out tokens | covered by base | addressed | partial | pending review | unaddressed | included | auto accepted | needs review | rejected by human | withdrawn by machine | repair calls | repaired and included | ext. rate (included / proposed) | conformance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| JRC | rules (mock) | 1 | 34 (0) | 15 | 0 / 0 | 0 | 2 | 0 | 13 | 2 | 2 | 2 | 13 | 0 | 2 | 2 | 0 | 0.000 / 0.765 | conformant (2 added, 0 tightened, 0 loosened, 0 failing, 0 warning(s)) |
| JRC | gpt-oss-120b | 890 | 69 (4) | 22 | 107,304 / 65,645 | 0 | 8 | 0 | 8 | 1 | 8 | 8 | 7 | 0 | 2 | 30 | 6 | 0.500 / 0.588 | conformant with warnings (6 added, 2 tightened, 0 loosened, 0 failing, 1 warning(s); C7) |
| Stat | rules (mock) | 1 | 29 (0) | 14 | 0 / 0 | 0 | 2 | 0 | 11 | 1 | 1 | 1 | 11 | 0 | 1 | 1 | 0 | 0.000 / 0.846 | conformant (0 added, 1 tightened, 0 loosened, 0 failing, 0 warning(s)) |
| Stat | gpt-oss-120b | 800 | 73 (4) | 25 | 107,370 / 65,423 | 0 | 7 | 0 | 5 | 2 | 8 | 8 | 6 | 0 | 3 | 34 | 8 | 0.750 / 0.529 | conformant with warnings (5 added, 2 tightened, 0 loosened, 0 failing, 1 warning(s); C7) |

Columns: covered by base / addressed / partial / pending review / unaddressed count atoms by coverage; included,
auto accepted, needs review, rejected by human and withdrawn by machine count live (not superseded) changes;
"calls (cached)" counts replays inside the same run; "repaired and included" counts included changes written by
an LLM repair round; the extension rate is the share of minted terms (mint property, mint class) among the
included changes that add or constrain elements, and among all machine proposals for "proposed". C7 is the
witness-data check of the conformance report (a warning, not a failing rule).

Changes included, by kind:

- JRC, rules (mock): reuse 2.
- JRC, gpt-oss-120b: mint property 4, refine 2, reuse 2.
- Stat, rules (mock): refine 1.
- Stat, gpt-oss-120b: mint property 5, refine 2, mint class 1.

Run settings:

- JRC, rules (mock) (jrc-research-mock-rules; store rules.sqlite3):
  - tool 21c6b5b; base dcat-ap-1.1 on dcat-2014; provider mock (the offline lexical rules proposer, repairer and judge, rules-v1 34; effort and token limits do not apply);
  - prompts: judge-v2, propose-v3, repair-v3; call statuses {'ok': 34}; stop reasons {'end_turn': 34};
  - input: 17 atoms, sha256 67e47c2f282ac972..., import flags: modality 'map', all=false (default-scored atoms only);
  - config: retrieval on (top-k 8), verify on, judge on, votes 1, repair rounds 3, auto-accept on (min confidence 0.5), later DCAT terms 'review', max parallel calls 1, blind true;
  - store and replay: replay cache 'project'; answers replayed from other projects: 0; calls from 2026-11-14T20:52:34+00:00 to 2026-11-14T20:52:34+00:00;
  - LEAKCHECK: clean.
- JRC, gpt-oss-120b (jrc-research-kiconnect-inferenz-gpt-oss-120b-blind; store pilot.sqlite3):
  - tool 21c6b5b; base dcat-ap-1.1 on dcat-2014; provider openai-compatible, model inferenz-gpt-oss-120b, effort medium, max output tokens 16000; served model as reported by the endpoint (uncached calls): openai-gpt-oss-120b 42, openai/gpt-oss-120b 23;
  - prompts: judge-v2, propose-v3, repair-v3; call statuses {'ok': 69}; stop reasons {'stop': 65};
  - input: 17 atoms, sha256 67e47c2f282ac972..., import flags: modality 'map', all=false (default-scored atoms only);
  - config: retrieval on (top-k 8), verify on, judge on, votes 1, repair rounds 3, auto-accept on (min confidence 0.5), later DCAT terms 'review', max parallel calls 1, blind true;
  - store and replay: replay cache 'project'; answers replayed from other projects: 0; calls from 2026-11-14T20:42:46+00:00 to 2026-11-14T20:57:24+00:00;
  - LEAKCHECK: clean.
- Stat, rules (mock) (statdcat-mock-rules; store rules.sqlite3):
  - tool 21c6b5b; base dcat-ap-1.1 on dcat-2014; provider mock (the offline lexical rules proposer, repairer and judge, rules-v1 29; effort and token limits do not apply);
  - prompts: judge-v2, propose-v3, repair-v3; call statuses {'ok': 29}; stop reasons {'end_turn': 29};
  - input: 14 atoms, sha256 3a43c65d45034701..., import flags: modality 'map', all=false (default-scored atoms only);
  - config: retrieval on (top-k 8), verify on, judge on, votes 1, repair rounds 3, auto-accept on (min confidence 0.5), later DCAT terms 'review', max parallel calls 1, blind true;
  - store and replay: replay cache 'project'; answers replayed from other projects: 0; calls from 2026-11-14T20:52:36+00:00 to 2026-11-14T20:52:36+00:00;
  - LEAKCHECK: clean.
- Stat, gpt-oss-120b (statdcat-kiconnect-inferenz-gpt-oss-120b-blind; store pilot.sqlite3):
  - tool 21c6b5b; base dcat-ap-1.1 on dcat-2014; provider openai-compatible, model inferenz-gpt-oss-120b, effort medium, max output tokens 16000; served model as reported by the endpoint (uncached calls): openai-gpt-oss-120b 47, openai/gpt-oss-120b 22;
  - prompts: judge-v2, propose-v3, repair-v3; call statuses {'ok': 73}; stop reasons {'stop': 69};
  - input: 14 atoms, sha256 3a43c65d45034701..., import flags: modality 'map', all=false (default-scored atoms only);
  - config: retrieval on (top-k 8), verify on, judge on, votes 1, repair rounds 3, auto-accept on (min confidence 0.5), later DCAT terms 'review', max parallel calls 1, blind true;
  - store and replay: replay cache 'project'; answers replayed from other projects: 0; calls from 2026-11-14T20:46:45+00:00 to 2026-11-14T21:00:05+00:00;
  - LEAKCHECK: clean.
