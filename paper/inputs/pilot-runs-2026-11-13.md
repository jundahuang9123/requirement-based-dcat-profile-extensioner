# Pilot runs on two RQ1 development cases (13 Nov 2026)

These are development-case pilot runs, not the RQ2 evaluation. No gold delta was scored, no human
reviewed anything (every "auto_accepted" is a machine decision), and the importer's modality mapping
leaves most atoms "unspecified". Only numbers are kept here. The atom statements, generated changes
and generated profiles are reference-derived, so they stay out of this repository. Regenerate them
with `paper/inputs/run_reference_case.py`.

## Setup

- Inputs: the default-scored content atoms of `reference-sets-v3/jrc-research.json` (17 atoms) and
  `reference-sets-v3/statdcat.json` (14 atoms) in `jundahuang9123/requirements-benchmark-references`.
  They were imported with `scripts/import_rq1_reference.py`, which drops the evaluator fields.
- Base: DCAT-AP 1.1, using the official SEMICeu `shacl-201706` shapes, unmodified.
- Model: KI:connect `inferenz-gpt-oss-120b` through the OpenAI-compatible provider
  (base URL `https://chat.kiconnect.nrw/api/v1`), `max_output_tokens` 8000.
- Pipeline settings:
  - default `PipelineConfig`;
  - `max_parallel_calls` 1, because of KI:connect rate limits;
  - judge on;
  - 1 vote;
  - up to 3 repair rounds.
- Runs:
  - Run 1: code before the V5 normalisation of "recommended + minCount 1" (about commit a52df71, **verify**).
  - Run 2: commit 2b92d77, which normalises "recommended + minCount 1" to the DCAT-AP convention
    instead of rejecting it. Run 2 replayed unchanged prompts from the LLM cache.
- Rules baseline: the offline `mock` provider (lexical rules proposer, repairer and judge) at 2b92d77.

## Results

| case | provider | wall s | calls (cached) | in / out tokens | addressed | partial | pending review | unaddressed | included | rejected | needs review | ext. rate | conformance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| JRC | rules (mock) | 1 | 38 (0) | 0 / 0 | 2 | 0 | 15 | 0 | 2 | 0 | 14 | 0.000 | conformant (2 added, 0 tightened) |
| JRC | gpt-oss-120b run 1 | 1018 | 83 (2) | 133,326 / 81,993 | 10 | 1 | 4 | 2 | 12 | 3 | 5 | 0.364 | conformant with warnings (8 added, 3 tightened, 0 loosened, 1 warning) |
| JRC | gpt-oss-120b run 2 | 461 | 74 (30) | 65,985 / 38,247 | 11 | 1 | 2 | 3 | 13 | 4 | 3 | 0.417 | conformant with warnings (9 added, 3 tightened, 0 loosened, 1 warning) |
| Stat | rules (mock) | 1 | 32 (0) | 0 / 0 | 2 | 1 | 11 | 0 | 2 | 0 | 11 | 0.000 | conformant (1 added, 1 tightened) |
| Stat | gpt-oss-120b run 1 | 892 | 64 (0) | 105,086 / 67,732 | 7 | 0 | 1 | 6 | 9 | 8 | 1 | 0.857 | conformant with warnings (6 added, 1 tightened, 0 loosened, 1 warning) |
| Stat | gpt-oss-120b run 2 | 482 | 64 (20) | 67,528 / 39,879 | 10 | 0 | 3 | 1 | 11 | 3 | 4 | 0.556 | conformant (6 added, 3 tightened, 0 loosened, 0 warnings) |

Changes included, by kind:

- JRC run 1: reuse 4, mint property 4, refine 3, mint class 1.
- JRC run 2: reuse 4, refine 3, mint property 5, mint class 1.
- Stat run 1: mint property 6, mint class 2, refine 1.
- Stat run 2: refine 3, mint property 5, mint class 2, reuse 1.
- Both rules runs: reuse or refine only.

Metric `repaired` counts non-superseded changes produced by a repair round (round > 0): 19 on JRC and 17 on Stat in
both LLM runs, and 1 in each rules run. The "extension rate" is the share of included changes that mint new terms.
The single conformance warning in the JRC runs and in Stat run 1 is C7 ("No valid witness could be generated for the
extension"). C1–C6 passed in every run.

## Qualitative observations (from reading the run outputs; check them against a rerun before quoting)

- Retrieval is lexical, so "authors" was not linked to `dcterms:creator` on JRC; the model then minted a property.
- The published DCAT-AP-JRC mints no new terms. The JRC mints are therefore probably unjustified,
  which makes them candidate false positives once the gold delta is scored.
- Data Cube (qb) and DQV are not in the vendored vocabularies. On Stat, the model minted dimension,
  attribute, quality and unit terms where the published StatDCAT-AP reuses qb and DQV.
- The T2 judge rejected constraints the atom did not license. One example is S-18.1, a
  `dcterms:issued` change from optional to recommended plus an `xsd:dateTime` range.
- V1 errors after 3 repair rounds sent changes that referenced unminted classes to human review,
  instead of letting them in.
- Several rejections are not yet diagnosed: JRC-6.2 `adms:identifier` (V5), JRC-6.4
  `dcterms:bibliographicCitation`, and S-18.1 (T2).
- Without the LLM, the rules baseline addresses only 2 atoms per case, against 10–11 with
  gpt-oss-120b in run 2. Everything else waits for human review.
