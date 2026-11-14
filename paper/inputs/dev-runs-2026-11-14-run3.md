# Run 3 of the two development cases (14 Nov 2026): debugging history, contaminated

A fresh third run of the development runs in `pilot-runs-2026-11-13.md`, made while drafting the paper to re-check
the qualitative observations. **Contaminated, like runs 1 and 2:** the importer and the run script put the atom's
source reference (the case name and the section of the published profile) and a project title naming the case into
every proposer, repairer and judge prompt (`backend/profile_extensioner/engine/prompts.py`, source line;
`scripts/import_rq1_reference.py`, document and locator; `paper/inputs/run_reference_case.py`, profile title). Use
these numbers only as a debugging history, never as results. Only numbers are kept here: the atom statements and the
generated changes are reference-derived.

## Setup

- Inputs: as runs 1 and 2 (17 JRC and 14 Stat atoms, imported with `scripts/import_rq1_reference.py`).
- Base: DCAT-AP 1.1 (from the reference sets' `base` field), engine before DCAT-state pinning: the code of
  2b92d77 (the paper branch at 0d7aadc adds only paper inputs).
- Model: `inferenz-gpt-oss-120b` through the OpenAI-compatible provider; `max_output_tokens` 8000 in the settings,
  which this provider does not send.
- Pipeline settings: default `PipelineConfig`, `max_parallel_calls` 1, judge on, 1 vote, up to 3 repair rounds.
- Fresh blackboard, so no answer was replayed from runs 1 or 2 (JRC: 1 cache hit inside the run; Stat: none).
- Run with `paper/inputs/run_reference_case.py <case> kiconnect inferenz-gpt-oss-120b <dir> run3`, JRC first, one
  after the other.

## Results

| case | provider | wall s | calls (cached) | in / out tokens | addressed | partial | pending review | unaddressed | covered by base | included | rejected | needs review | ext. rate | conformance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| JRC | gpt-oss-120b run 3 | 1961 | 74 (1) | 122,356 / 76,346 | 8 | 0 | 4 | 5 | 0 | 8 | 4 | 4 | 0.571 | conformant with warnings (5 added, 2 tightened, 0 loosened, 1 warning) |
| Stat | gpt-oss-120b run 3 | 1937 | 57 (0) | 90,564 / 61,846 | 5 | 2 | 1 | 5 | 1 | 7 | 7 | 3 | 0.500 | conformant with warnings (5 added, 1 tightened, 0 loosened, 1 warning) |

Changes included, by kind:

- JRC run 3: reuse 1, refine 2, mint property 4, mint class 1.
- Stat run 3: reuse 2, refine 1, mint property 3, mint class 1.

Metric `repaired`: 16 on JRC and 15 on Stat. All `rejected` changes are withdrawals by the model repairer; no person
reviewed anything. One Stat repair call failed with an endpoint error (502). The single C7 warning of each run came
from the witness generator, not from a constraint no data can meet: on JRC a nested dataset node left unfilled at the
generator's depth limit, on Stat a value-list member used as a value without the class the range requires.
