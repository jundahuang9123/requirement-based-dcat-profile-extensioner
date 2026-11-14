# Delta 5ffd56e -> 21c6b5b, area "blind": benchmark runs, leakage, independence

Scope: what a model sees of an atom (prompts, offline-provider context), `NEW:localName`, prompt versions, the
profile-name lint, blind project mode (API, frontend), the importer and the run script, request parameters
(`max_tokens`, `reasoning_effort`, cut-off answers), the replay cache, key binding. Everything else in the tool
session's message (pipeline order, decision policy, conditions, metrics, release gating, DCAT/bases/conformance,
Dataspecer) belongs to other areas and is only pointed at in Sect. 7.

`B/` = `backend/profile_extensioner/`. Anchors without a commit are at **21c6b5b** (worktree `main-wt2`, HEAD
21c6b5b). `@5ffd56e`, `@2b92d77`, `@a52df71`: older commits, read with `git show` in the same worktree.

## 0. Method

- `git -C main-wt2 log 5ffd56e..21c6b5b`: 9321951, 40a5d5d ("No answer leaks, independent runs, real request
  parameters; staged rebase"), a3d8098, 913bea2 ("Pipeline integrity, blind benchmark runs, imports that resolve"),
  21c6b5b ("Close the adversarial review's findings"). The leak fix lands in 40a5d5d (source line removed, neutral
  title, project-scoped cache, request parameters), 913bea2 (prompt versions bumped, `for_model`, opaque ids,
  evaluator map, blind mode, refusals, LEAKCHECK) and 21c6b5b (more neutralisation, profile-name lint, UI).
  Commit messages name the endpoint operator and an author: keep them out of the paper (anonymity).
- Code read in full: `B/engine/prompts.py`, `B/knowledge/__init__.py`, `B/engine/intake.py` (diff + lint),
  `scripts/import_rq1_reference.py`, `scripts/run_reference_case.py`, `B/llm/client.py`,
  `B/llm/openai_compatible.py`, `B/llm/registry.py` (diff), `B/store/blackboard.py` (diff), blind parts of
  `B/api/app.py`, `B/engine/pipeline.py`, `B/contracts.py`, `frontend/src/{Inspector.tsx,App.tsx,api.ts}` (diff).
- Probes: offline, mock provider or a replaced `httpx.post`, `Store(":memory:")`, only the synthetic demo
  (`examples/materials-testing-lab`) and an invented reference set. No external model, no benchmark material.
  Scripts: `scratchpad/probes-delta-blind/scripts/p1..p6*.py`. The tool's dependencies are not installed in this
  environment; they were installed into `scratchpad/pydeps-delta` (PYTHONPATH), nothing into either worktree.
- Full suite rerun offline at 21c6b5b: **170 passed in 24.01 s** (matches
  `paper/inputs/tests-main-21c6b5b-2026-11-14.txt:6`, "170 passed in 25.02s"). Area tests
  (`tests/test_openai_params.py`, `test_blind_prompts.py`, `test_store.py`, `test_providers.py`): 29 passed.
  `git status --porcelain --ignored` in `main-wt2` empty afterwards.

## 1. What changed in this area

| Topic | 5ffd56e | 21c6b5b | Anchor |
|---|---|---|---|
| Atom in prompts | id, statement, subject, modality **and `source: <document>, <locator>`** | id, statement, subject, modality (+ licensed obligation) only | `B/engine/prompts.py:111-121`; old `@5ffd56e :105-115` |
| Atom in the offline provider's context | `atom.model_dump()` (all fields) | `_model_atom`: `{id, statement, subject, modality}` | `B/engine/prompts.py:105-108, 201, 255, 284` |
| Project title / prefix in prompts | propose: "Extension: <title>; ... minted as <prefix>:localName"; repair: "minted as <prefix>"; context `profile_prefix` | "New terms are written NEW:localName." only; no title, no prefix | `B/engine/prompts.py:177-181, 231-236`; old `@5ffd56e :174-175, 229, 208` |
| Minted terms in model input | CURIEs with the project prefix | `kb.for_model()` binds `NEW` to the project namespace; `kb.neutral()` rewrites namespace and prefix in the repairer's JSON, failure messages, coverage reasons, judge/repair contexts | `B/knowledge/__init__.py:38-56`; `B/engine/prompts.py:167, 228-229, 247, 253-254, 270, 276, 283` |
| Prompt versions | propose-v2, repair-v2, judge-v1 | **propose-v3, repair-v3, judge-v2** (bumped at 913bea2; system prompts lines 24-96 byte-identical to 5ffd56e) | `B/engine/prompts.py:20-22` |
| Intake | no profile-name check | warning `contains_profile_name` (regex of DCAT-AP-<Name> and Stat/Geo/Health/mobility/BReg-DCAT, NAPCORE) | `B/engine/intake.py:28-33, 58-65` |
| Importer ids | reference id kept (`[atom id]`) | `A-` + first 6 hex of SHA-256("rq2-blind\|case\|id"), sorted by that id | `scripts/import_rq1_reference.py:64-69` |
| Importer output | id, statement, subject, modality, `source_reference {document: case, locator}`, `benchmark_id`, case-naming title | id, statement, subject, modality; title "Requirement atoms"; no benchmark_id | `scripts/import_rq1_reference.py:70-87` |
| Evaluator map | none | `<out>.evalmap.json`: case, base, atoms-file sha256, import flags, per atom: case, original id, locator, reference document, raw/mapped modality, mode, standard-form resource | `scripts/import_rq1_reference.py:78-95` |
| Modality | conservative map | same map (`:40-46`) + `--modality unspecified` (all atoms unspecified), recorded | `scripts/import_rq1_reference.py:22-26, 56, 75-77, 80, 93` |
| Run script | positional args; project title "<case> extension", namespace `https://example.org/<case>#`; deletes the earlier project silently; global cache; one shared store | CLI; neutral title "Extension under test", namespace `https://example.org/ext#`, prefix `ext`; `blind=True`; refusals; records; LEAKCHECK | `scripts/run_reference_case.py:37-39, 42-133`; old: `paper/inputs/run_reference_case.py:22-34` |
| Blind mode | none | `PipelineConfig.blind`; snapshot and export drop source_reference, expected_change, counterfactual_of, hints; Inspector hides source and counterfactual | `B/contracts.py:623-625`; `B/engine/pipeline.py:644-648`; `B/api/app.py:494-509`; `frontend/src/Inspector.tsx:112-113` |
| Replay cache | global: any project's answer with the same hash | `PipelineConfig.replay_cache` "project" (default), "global", "off"; only original calls are sources; replay records `replayed_from`, `replayed_from_project` | `B/contracts.py:578-579, 620-622`; `B/engine/pipeline.py:86-90`; `B/llm/client.py:40-48, 96-110`; `B/store/blackboard.py:344-360` |
| Cache key | provider, model, effort, prompt version, schema, prompts, variant | + the provider's request signature: `openai-chat/2\|max=<max_output_tokens>\|effort=<mapped>\|temperature=<t>` | `B/llm/client.py:79-83`; `B/llm/openai_compatible.py:26-30, 47-50`; `B/llm/anthropic_provider.py:35-37` |
| Request body (OpenAI-compatible) | model, messages, response_format (+temperature if set) | + `max_tokens` = max_output_tokens, + `reasoning_effort` (low/medium/high; xhigh and max sent as high) | `B/llm/openai_compatible.py:103-117` |
| Rejected parameter | json_schema -> json_object fallback only | 400 ladder: the parameter the error names, else json_schema, reasoning_effort, token limit; each dropped once, noted in the record, remembered per model (token limit not remembered) | `B/llm/openai_compatible.py:118-131, 169-207` |
| Cut-off answer | accepted (the finish reason reached the `Completion` only, not the call record) | `LLMError` "cut off at the output token limit (N)" | `B/llm/openai_compatible.py:146-149` |
| Call record | no stop reason | `stop_reason` (last attempt), `notes` (request adaptations), replay origin | `B/contracts.py:578-581`; `B/llm/client.py:153-154` |
| Keys | one key per provider, sent to any base URL | an OpenAI-compatible key is bound to the origin it was entered for; the environment key only to the origin of `RBDPE_LLM_BASE_URL` | `B/llm/registry.py:26-79, 115-118`; `B/api/app.py:140-143, 208-217` |
| Docs | `docs/design.md:73` "Leakage controls ... implemented" | row still at `docs/design.md:77`, plus "Benchmark hygiene (blind runs)" | `docs/design.md:92-106` |

## 2. Claims of the tool session's message, verified

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | A model sees of an atom only id, statement, subject, modality; also the offline provider's context | **confirmed** | `B/engine/prompts.py:105-121, 201, 255, 284`. P1: 25 calls on the synthetic demo, every context's atom keys = {id, modality, statement, subject}; `tests/test_blind_prompts.py:22` |
| 2 | No source reference, project title, namespace or prefix reaches a prompt | **confirmed** | P1: canaries planted in source document/locator/quote, hints, tags, counterfactual fields, project id, name, title, namespace and prefix; 0 hits in 25 stored prompts (15 propose, 10 judge) and in 25 contexts |
| 3 | Minted terms always appear as `NEW:localName`, including judge and repair prompts and verifier messages | **confirmed** (prompt paths) | `B/knowledge/__init__.py:38-56`; `B/engine/prompts.py:228-229, 247, 253-254, 276, 283`. P2: repair line reads "- V1: The class NEW:Machine (<NEW:Machine>) is used ..."; 0 canaries in judge/repair prompts and contexts; `neutral()` leaves `index:`, `text:`, `next:` alone. Verifier messages shown to the reviewer keep the project prefix (by design) |
| 4 | Prompt versions propose-v3, repair-v3, judge-v2 | **confirmed** | `B/engine/prompts.py:20-22`; P1 records carry propose-v3 and judge-v2. System prompts unchanged since 5ffd56e (lines 24-96 identical): only the user-prompt builders changed |
| 5 | Importer writes opaque ids, "a keyed hash such as A-01b6c5, stable across selections" | **partly** | `scripts/import_rq1_reference.py:64-69`: SHA-256 of a fixed, public salt "rq2-blind", the case name and the reference id, truncated to 6 hex digits (24 bits). Stable across selections: P4 (default vs `--all`: same ids). Not a secret-keyed hash; no collision check. `docs/design.md:98` says `A-001` (mismatch) |
| 6 | The atom set carries no source reference, case name or benchmark id | **confirmed** (for the file's fields) | `scripts/import_rq1_reference.py:77, 82-87`; P4: keys title/description/base_profile_ids/atoms, atom keys id/modality/statement/subject; the case name, original ids, locators and document absent from the file. A statement can still name a profile (only the lint flags it) |
| 7 | The join is a separate evaluator map; the tool never reads it | **partly** | `scripts/import_rq1_reference.py:90-95`. No backend module reads it (grep: only `scripts/run_reference_case.py`). The run script reads it (refusal without it, sha256 check, import flags in the summary, canaries: `:61, 67-78, 112, 157-168`); nothing from it enters the project (`:96-102`) |
| 8 | `--modality unspecified` withholds the mapped modality | **confirmed** | `scripts/import_rq1_reference.py:56, 76`; P4: all atoms unspecified |
| 9 | "That matters where the reference document is the published profile itself (StatDCAT-AP, HealthDCAT-AP)" | **not verifiable here (verify)** | Only the importer's docstring says so (`scripts/import_rq1_reference.py:24-25`). The paper says the atoms of GeoDCAT-AP, StatDCAT-AP and DCAT-AP-JRC are worded from the profile's own specification or paper (`sections/06-setup.tex:45-47`, from RQ1 L383, L386-387). The two lists differ; the reference sets were not opened (held out) |
| 10 | The pilots use the default mapping; the import flags are recorded | **partly** | Recorded: evaluator map `import` and per-atom `modality_mode` (`scripts/import_rq1_reference.py:80, 93`), summary `INPUT ... import=` (`scripts/run_reference_case.py:112`; P4). The pilots' choice: no file yet (verify) |
| 11 | Run script runs a blind project, so the workbench hides sources from the reviewer | **confirmed, with limits** | `scripts/run_reference_case.py:101` (`blind=True`); `B/engine/pipeline.py:644-648`; `B/api/app.py:494-509`; `frontend/src/Inspector.tsx:112-113`; P6: 0 of 16 atoms show a source in snapshot and export. Limits: the run script's atoms carry no sources anyway (refused, `:147-151`); `blind` is a view filter that an unauthenticated PATCH switches off (P6: sources back, log says only "the decision settings changed"); the project id is `<case>-<provider>-<model>` (`:80-81`) and appears in workbench URLs and the export |
| 12 | Refuses non-blind inputs | **confirmed** | `scripts/run_reference_case.py:64-73, 136-154`: non-opaque id, source_reference, expected_change, counterfactual_of, hints, benchmark_id -> exit 4. P4: the demo set refused with 11 problem lines. Not checked: profile names in statements (lint warning only), tags (never shown) |
| 13 | Refuses to run without the evaluator map | **confirmed** | `:69-73` (exit 4); also refuses a map whose `atoms_file_sha256` differs (`:75-78`, exit 4). P4: both |
| 14 | Records the input sha256, the import flags and the full PipelineConfig | **confirmed** | `:108-112` SETTINGS (base, dcat, provider, model, effort, max_output_tokens, replay), CONFIG (full `PipelineConfig` JSON), INPUT (sha256, import flags, atom count); written to `<dir>/<pid>.txt` (`:131`). P4 shows the three lines |
| 15 | Scans every stored prompt for canaries (case name, original ids, locators, reference document, profile names), reported as LEAKCHECK | **confirmed, with blind spots** | `:129-133, 136-137, 157-175`: system+user prompt of every call record (`limit=None`); "LEAKCHECK clean" or "LEAK {...}", exit 3. P4: clean on a mock run; fabricated records hit case, id, locator, profile name. Blind spots: canaries under 4 characters are dropped and a canary that occurs in any atom statement is not counted (`:167-168`); corrective-retry prompts are not stored, so not scanned (`B/llm/client.py:143-165`). The vendored data mention "GeoDCAT-AP" only in DCAT 3 scope notes and the specs, which are not shown in prompts (definition = skos:definition/rdfs:comment/dcterms:description, `B/knowledge/vocab_index.py:176`) |
| 16 | Replay cache project-scoped by default; a replay records the call it came from | **confirmed** | Anchors in Sect. 1. P3 (one store, mock): project run-b after run-a: 0 of 25 calls replayed (at 5ffd56e README A3: 25 of 25); run-c with `global`: 25 of 25, each with `replayed_from` set, origin run-b; re-running run-a replays its own 25, each pointing at an original call of run-a. `delete_project` removes the call records (`B/store/blackboard.py:120-126`), so `--replace` starts empty |
| 17 | The OpenAI-compatible endpoint (vLLM) now receives `max_tokens` and `reasoning_effort` | **confirmed for the request; endpoint behaviour unverified** | `B/llm/openai_compatible.py:103-117`; P5: body keys max_tokens, messages, model, reasoning_effort, response_format; `tests/test_openai_params.py:40-53`. Dropped again if the endpoint answers 400 naming them (noted in the record). "vLLM" and whether the endpoint honours `reasoning_effort`: not checkable offline (verify) |
| 18 | These are part of the cache key | **confirmed** | `B/llm/client.py:79-83`; `B/llm/openai_compatible.py:47-50`. P5: five settings (default, 8000 tokens, medium, temperature 0, max) give five keys; `tests/test_openai_params.py:143-150` |
| 19 | A cut-off answer is reported as an error | **confirmed** | `B/llm/openai_compatible.py:146-149` -> `B/llm/client.py:125-129` (record status "error", message kept). Effect: propose -> atom unclear "The model gave no usable answer: ..." (`B/engine/propose.py:79-88`); repair -> failed (`B/engine/repair.py:88-89`); judge -> T2 warning "Judge unavailable", review (`B/engine/pipeline.py:287-290`). P5: record status error, `stop_reason` empty (the cause is in `error`) |
| 20 | Pilots: clean blind pilots of JRC and StatDCAT-AP on DCAT-AP 1.1 / DCAT 2014, gpt-oss-120b, effort medium, 16k output tokens, fresh store | **not verifiable (no file; verify)** | Run-script defaults are effort medium and **8000** tokens (`scripts/run_reference_case.py:50-51`); 16k needs `--max-output-tokens 16000` (LLMSettings default 16000, `B/contracts.py:596`). The default store is the shared file `/tmp/rbdpe-ws/blackboard.sqlite3` (`:49`); with project scope that no longer couples runs (P3) |

## 3. Probe results (offline)

- **P1** `p1_leak.py`: synthetic demo (16 atoms in the file, 15 active: lab-02-cf is inactive; base 3.0.1), mock, full `run_all`, canaries everywhere the
  model must not look: 25 calls (15 propose-v3, 10 judge-v2), NEW: in all 15 propose and 5 judge prompts, 0
  canary hits in prompts and in the 25 offline contexts; atom keys always {id, modality, statement, subject}.
- **P2** `p2_repair_judge.py`: minted change with the namespace and prefix planted in the coverage reason, mint
  reason, engine notes and the failure message: 0 canaries in judge/repair prompts and contexts; NEW: 4 / 12 / 7 /
  16 times.
- **P3** `p3_replay.py`: replay scope as in claim 16; metrics `llm_calls` 50, `llm_calls_cached` 25 after the
  re-run (calls without replays = `llm_calls - llm_calls_cached`).
- **P4** `p4_run_script.py` (invented reference set "zzsynth-case", 4 atoms, 3 scored by default): importer
  output and map as in claims 5-10; run exit 0; `SETTINGS base=dcat-ap-3.0.1 dcat=dcat-3 provider=mock ...
  replay=project`; `CONFIG {... "exclude_namespaces":[], ... "replay_cache":"project","blind":true}`; `INPUT
  atoms_sha256=... import={"all": false, "modality": "map", ...} atoms=3`; `CALLS 4 {"ok": 4}
  replayed_from_other_projects=0`; `LEAKCHECK clean`. Refusals: demo set exit 4; no map exit 4; wrong sha exit 4.
  `leak_scan` on fabricated records: hits StatDCAT, case, ZZ-1.1, "Section 9.9", "p. 3"; the 2-character id "R1"
  is dropped.
- **P5** `p5_client_records.py`: corrective retry sent (2 attempts) but the record keeps only the original user
  prompt and the final answer (the invalid first answer is overwritten); tokens summed (20/6); `stop_reason`
  "stop"; notes kept. Cut-off: `LLMError`, record status error. Keys: same origin yes, other host None; env key
  only to `RBDPE_LLM_BASE_URL`'s origin; a provider for a user-set foreign base URL gets no key but still targets
  it.
- **P6** `p6_blind_api.py` (FastAPI TestClient, in-memory store): blind on -> 0 of 16 sources in snapshot and
  export, none in the log; blind off by PATCH -> 16 sources back; log entry "the decision settings changed:
  stages from verify on are out of date".
- Lint probe: "StatDCAT-AP", "DCAT-AP-JRC", "geodcat" flagged; "DCAT-AP 3.0.1" not; "DCAT-AP Catalogue" flagged
  (false positive).

## 4. New issues and doc/code mismatches at 21c6b5b

1. `docs/design.md:98` says the importer writes ids `A-001` ...; the code writes `A-` + 6 hex digits
   (`scripts/import_rq1_reference.py:66-67`) and the run script accepts only that form
   (`scripts/run_reference_case.py:138`). Confidence high; documentation only.
2. `scripts/run_reference_case.py:80-81`: the project id is `<case>-<provider>-<model>[-tag]`. It never reaches a
   prompt (P1), but a reviewer of the blind project sees it in workbench URLs (`frontend/src/App.tsx:343-344`) and
   the export, and every blind project shows the same name. Confidence high; low impact (reviewer side only).
3. Blind mode is a view filter, not access control: `PATCH /api/projects/{id}` (`B/api/app.py:294-308`, no
   authentication) switches it off and the log names only "the decision settings changed"
   (`B/engine/pipeline.py:146-158`). Confidence high (P6); moot for run-script projects, whose atoms carry no
   sources (`scripts/run_reference_case.py:147-151`).
4. LEAKCHECK blind spots: canaries under 4 characters and canaries that occur in any statement are dropped
   (`scripts/run_reference_case.py:167-168`); corrective-retry prompts are not stored and so not scanned
   (`B/llm/client.py:143-165`). By design for statements, so LEAKCHECK does not measure the plain-word leak.
   Confidence high.
5. Importer ids: fixed public salt, 24-bit truncation, no collision check; on a collision the evaluator map keeps
   one entry silently (`scripts/import_rq1_reference.py:66-78`) and the run fails at parse time with "Duplicate
   atom id" (`B/engine/intake.py:180-181`). Confidence high; low probability.
6. A cut-off call's record has an empty `stop_reason`; the cause is only in `error`
   (`B/llm/openai_compatible.py:146-149`, raised before a `Completion` exists; P5). Low.
7. The run script's CLI defaults (effort medium, `--max-output-tokens 8000`, `scripts/run_reference_case.py:50-51`)
   differ from `LLMSettings` (high, 16000, `B/contracts.py:594-596`); the token limit of any run must be read from
   its SETTINGS line. Not a defect.
8. `PROFILE_NAMES` flags any capitalised word after "DCAT-AP " (`B/engine/intake.py:31-32`), e.g. "DCAT-AP
   Catalogue". Low (warning only).
9. Conflicting lists of cases whose reference document is the published profile: importer docstring StatDCAT-AP,
   HealthDCAT-AP (`scripts/import_rq1_reference.py:24-25`) vs paper GeoDCAT-AP, StatDCAT-AP, DCAT-AP-JRC
   (`sections/06-setup.tex:45-47`). Medium for the paper; verify against RQ1 Table 1.
10. SSRF without the key remains: the server still sends requests to any user-set base URL (`B/api/app.py:220-225`
    lists models there; runs too), but no stored or environment key goes with them (`B/llm/registry.py:67-79,
    115-118`; P5). D2 changed, not closed.
11. The run script sets no `exclude_namespaces` (P4 CONFIG `[]`; `scripts/run_reference_case.py:99-101`); the
    paper's "the index hides the target profile's namespace" is not done by the run script. The index holds the 12
    vocabularies of `paper/inputs/tool-facts-main-21c6b5b.txt:2-3` (verify per case that none is a target profile's
    own namespace). Medium for the paper's wording.

## 5. README tool issues in this area (status at 21c6b5b)

- **A1 answer-in-input leak: fixed.** Source line gone (`B/engine/prompts.py:111-121`); no title or prefix
  (`:177-181, 231-236`); `NEW:` everywhere the model reads (`B/knowledge/__init__.py:38-56`); opaque ids and
  evaluator map (`scripts/import_rq1_reference.py:62-95`); neutral title/namespace, refusals, LEAKCHECK
  (`scripts/run_reference_case.py:37-39, 64-78, 96-101, 129-175`); P1, P2, P4. Residual: plain-word leak in
  statements (only a lint warning, `B/engine/intake.py:28-33, 58-65`; not counted by LEAKCHECK, `:167-168`); the
  project id names the case on the reviewer side (`:80-81`). `docs/design.md:77` still says "implemented"; the
  blind-run section is `docs/design.md:92-106`. The development runs stay contaminated (history).
- **A3 replay cache global: fixed.** Project scope by default (`B/contracts.py:620-622`; `B/engine/pipeline.py:86-90`;
  `B/llm/client.py:96-110`; `B/store/blackboard.py:344-360`); judge-v1 -> judge-v2 (`B/engine/prompts.py:22`); run
  script default `--replay project` (`scripts/run_reference_case.py:52`), `--replace` deletes the old project's
  calls (`:83-87`; `B/store/blackboard.py:120-126`). P3: 0 of 25 (was 25 of 25). The default store is still one
  shared file (`:49`), harmless under project scope.
- **A4 no output limit or effort; truncation accepted: fixed.** `B/llm/openai_compatible.py:103-117, 146-149`;
  cache key `:47-50` and `B/llm/client.py:79-83`; `tests/test_openai_params.py`. Caveats: a parameter the endpoint
  rejects is dropped (noted per call, `:118-131, 169-207`); xhigh/max are sent as high (`:30`); endpoint behaviour
  unverified.
- **C4 call records: changed (partly fixed).** `stop_reason` of the last attempt and request notes are recorded
  (`B/contracts.py:580-581`; `B/llm/client.py:153-154`); the corrective retry's prompt and the first invalid
  answer are still not stored (`B/llm/client.py:143-165`; P5); a cut-off call has an empty `stop_reason`.
- **D1 no authentication: still present** (no auth in `B/api/app.py`); now also: blind mode can be switched off
  by anyone (P6).
- **D2 user-set base_url: changed.** Keys are bound to their origin (`B/llm/registry.py:26-79`;
  `B/api/app.py:208-217`); requests still go to any user-set base URL (`B/api/app.py:220-225`).
- **Q5 / Q15** (leak, three channels): closed at 21c6b5b (source line, title, case-naming ids). **Q20** (modality):
  a third option exists (`--modality unspecified`), recorded; the choice stays with the author. **Q22**: A1, A3,
  A4 fixed; C4 changed. **Q32** "hide the target namespace per case": still open (new issue 11).

## 6. Paper impact

| # | file:line | current (short quote) | replacement fact | anchor @21c6b5b |
|---|---|---|---|---|
| 1 | sections/04-pipeline.tex:1-3 (comment) | "Describes the tool at commit 5ffd56e of the main branch" | describes 21c6b5b; re-tag the `@5ffd56e` src anchors (line shifts listed in rows 3-6) | git log 5ffd56e..21c6b5b |
| 2 | sections/04-pipeline.tex:31-33 | "A subject that is not a plain word, a very short statement, a compound statement and a modality the wording contradicts are warnings" | add: a statement that names a published profile is a warning too (it hints at the answer in an evaluation) | B/engine/intake.py:28-33, 58-65 |
| 3 | sections/04-pipeline.tex:29-31 (src) | "@5ffd56e B/engine/intake.py:1-7, 108-131"; ":39-51, 115-116"; ":52-87" | intake.py:1-7, 122-145; 44-57, 129-130; 66-101 | B/engine/intake.py (diff inserts 28-33, 58-65) |
| 4 | sections/04-pipeline.tex:41 | "The proposer sees one atom per call, without the other atoms' changes" | still true; can add: and of that atom only its identifier, statement, subject and modality; src "pipeline.py:188-191" -> 243-246 | B/engine/prompts.py:111-121; B/engine/pipeline.py:243-246 |
| 5 | sections/04-pipeline.tex:38 (src) | "B/engine/prompts.py:136-138" | 141-145 (LATER DCAT / DEPRECATED markers at 143, 145) | B/engine/prompts.py:141-145 |
| 6 | sections/04-pipeline.tex:61 (src) | "B/engine/prompts.py:238-242" | 244-248; failure messages are neutralised there (247) | B/engine/prompts.py:244-248 |
| 7 | sections/04-pipeline.tex:101-102 | "with prompts, answers and tokens, and serves a replay cache" | with prompts, answers, tokens and the provider's stop reason, and serves a replay cache scoped to the project; a replay names the call it repeats (the corrective retry's prompt is not kept) | B/contracts.py:577-581, 620-622; B/llm/client.py:96-110, 143-165; B/store/blackboard.py:344-360 |
| 8 | sections/04-pipeline.tex:105 | "The 98 tests pass without a model." | "The 170 tests pass without a model." | paper/inputs/tests-main-21c6b5b-2026-11-14.txt:6; rerun here 170 passed |
| 9 | sections/04-pipeline.tex:111 (comment) | "the described commit is 5ffd56e (main)" | 21c6b5b (main); Q14 (merge into the paper branch) stays open | git rev-parse 21c6b5b |
| 10 | figures/pipeline.tex:50 | "model calls with prompts, answers, tokens and a replay cache" | optional: "... and a project-scoped replay cache" | B/contracts.py:620-622 |
| 11 | sections/05-benchmark.tex:62-64 | "An importer keeps each atom's identifier, statement, subject, modality and source reference and drops the evaluator fields" | the importer keeps statement, subject and modality, gives each atom an opaque identifier, and writes the case, the original identifier, the locator and the reference document into a separate evaluator map for scoring that the pipeline never reads; evaluator fields dropped | scripts/import_rq1_reference.py:5-20, 62-95 |
| 12 | sections/05-benchmark.tex:65, 69 (src) | "@5ffd56e scripts/import_rq1_reference.py:1-16, 47-59"; ":12-14, 26-32, 56" | :1-30, 62-95; :22-26, 40-46, 75-76 | scripts/import_rq1_reference.py |
| 13 | sections/05-benchmark.tex:66-70 | "The importer maps explicit requirements and mandatory items to must ..." / "\todo{modality from the reference's obligation? (Q20)}" | mapping unchanged; add: an option withholds the mapped modality (every atom unspecified), and the choice is recorded with the import; which one the runs use: verify (tool session says the default mapping) | scripts/import_rq1_reference.py:40-46, 56, 75-77, 80, 93; scripts/run_reference_case.py:112 |
| 14 | sections/06-setup.tex:2 (comment) | "Settings are those of the tool at 5ffd56e." | 21c6b5b | — |
| 15 | sections/06-setup.tex:8, 16 (src) | "@5ffd56e B/contracts.py:592-606"; "B/engine/prompts.py:179-188" | B/contracts.py:601-625 (top_k 606, repair_rounds 608, votes 610, threshold 612, later_dcat_terms 619); prompts.py:184-193 | B/contracts.py:601-625; B/engine/prompts.py:184-193 |
| 16 | sections/06-setup.tex:28-30 | "The provider sends no reasoning effort, no output limit and, by default, no temperature, so the endpoint's defaults apply. \verify{endpoint defaults} \todo{provider: effort and output limit (Q22)}" | The provider sends an output limit and a reasoning effort (low, medium or high) and, by default, no temperature. An answer cut off at the limit is a failed call (the atom stays unclear, a repair fails, a judge verdict is missing); a parameter the endpoint rejects is dropped and noted in the call record. The runs use effort medium and 16,000 output tokens \verify{from each run's SETTINGS line}; keep \verify{endpoint honours reasoning effort; default temperature}; drop the todo | B/llm/openai_compatible.py:103-117, 118-131, 146-149, 169-207; B/llm/client.py:125-129; B/engine/propose.py:79-88; B/engine/repair.py:88-89; B/engine/pipeline.py:287-290; B/contracts.py:594-596; scripts/run_reference_case.py:50-51, 93-95, 109-110 |
| 17 | sections/06-setup.tex:31-34 | "Each run gets a fresh store: the replay cache answers identical requests across a store's projects and, under an unchanged prompt version, across code versions. \todo{fresh store per run (Q22)}" | Each run is a new project, and the replay cache answers only identical requests of the same project, so runs share no answers; a replay names the call it repeats. The cache key holds the prompt version, prompts, schema, model and the configured output limit, effort and temperature (also when the endpoint made the provider drop one; the call record notes that). Drop the todo | B/contracts.py:620-622; B/engine/pipeline.py:86-90; B/llm/client.py:79-83, 96-110; B/store/blackboard.py:120-126, 344-360; scripts/run_reference_case.py:52, 80-87 |
| 18 | sections/06-setup.tex:33 (src) | "B/engine/prompts.py:20-22 (judge-v1 unchanged)" | propose-v3, repair-v3, judge-v2 | B/engine/prompts.py:20-22 |
| 19 | sections/06-setup.tex:35-36 | "Code commit, prompt versions and base hashes are frozen before the first run." | may name the versions: propose-v3, repair-v3, judge-v2 | B/engine/prompts.py:20-22 |
| 20 | sections/06-setup.tex:38-40 | "L2 holds the answer out: atoms carry no IRIs or prefixed names (Sect. 4.1), the index hides the target profile's namespace, and no prompt carries an atom's source reference or a case-naming title or identifier." | L2 holds the answer out: atoms carry no IRIs or prefixed names, and their identifiers are opaque; a prompt shows of an atom only identifier, statement, subject and modality; no prompt shows a source reference or the project's title, namespace or prefix (minted terms read NEW:localName, also for the judge, the repairer and in verifier messages). The run script refuses an atom set that is not blind or lacks its evaluator map, and searches every stored prompt for the case name, original identifiers, locators, reference document and published-profile names. "the index hides the target profile's namespace": not done by the run script (keep the todo; verify that no vendored vocabulary is a target namespace) | B/engine/prompts.py:105-121, 177-181, 228-236, 247, 253-255, 270-286; B/knowledge/__init__.py:38-56; scripts/import_rq1_reference.py:62-95; scripts/run_reference_case.py:64-78, 99-101, 129-175; paper/inputs/tool-facts-main-21c6b5b.txt:2-3 |
| 21 | sections/06-setup.tex:41, 44 (src) | "@5ffd56e B/engine/intake.py:39-51; ... B/engine/prompts.py:108, 113-115, 174"; "@5ffd56e scripts/import_rq1_reference.py:57-58" | new anchors of row 20; for the history keep @5ffd56e and add the runs' engine: @2b92d77 B/engine/prompts.py:112 (source line), 154-155 (title, prefix); @a52df71 same lines (run 1) | git show 2b92d77/a52df71:B/engine/prompts.py |
| 22 | sections/06-setup.tex:42-45 | "In the development runs every proposer, repairer and judge prompt printed the atom's source reference ... \todo{leak fix and its commit (Q5)}" | history stays; add "The described version prints none of it" and drop the todo (no hash in print; the src comment can name 21c6b5b) | B/engine/prompts.py:111-121 |
| 23 | sections/06-setup.tex:45-47 | "A plain-word leak remains: the reference atoms are worded from the companion's reference documents, for GeoDCAT-AP, StatDCAT-AP and DCAT-AP-JRC the profile's own specification or paper" | stays; add: intake warns when a statement names a published profile, and the prompt scan does not count a name that occurs in a statement, so it does not measure this leak. The importer's docstring names StatDCAT-AP and HealthDCAT-AP as cases whose reference document is the published profile: \verify{reconcile with RQ1 Table 1} | B/engine/intake.py:28-33, 58-65; scripts/run_reference_case.py:167-168; scripts/import_rq1_reference.py:22-26 |
| 24 | sections/07-results.tex:93-94 | "\todo{development cases: leak-free, DCAT-pinned reruns}" | keep the todo until the numbers file exists; blind reruns at the described version are reported as running (tool session; no file: verify) | — |
| 25 | sections/07-results.tex:97-98 (src) | "@5ffd56e B/engine/prompts.py:105-115 (source line), 177, 231, 265" | history: add @2b92d77 B/engine/prompts.py:112, 154-155 (the runs' engine) | git show 2b92d77:B/engine/prompts.py |
| 26 | sections/07-results.tex:104-106 | "Removing the leak is a precondition of the evaluation; ... the last two are open (Sect. 8). \todo{leak fix commit (Q5)}" | the described version removes the leak (Sect. 6); "duplicates sent to repair before consolidation": consolidation now runs before repair (pipeline area: verify there); C7: conformance area; drop the todo | B/contracts.py:104-109 |
| 27 | sections/08-discussion.tex:92-93 (src) | "@5ffd56e B/engine/prompts.py:113-115 ... :174" | keep as history; add @2b92d77 B/engine/prompts.py:112, 154-155 | git show 2b92d77:B/engine/prompts.py |
| 28 | sections/08-discussion.tex:94 | "Intake lints the statement, not the source reference." | no prompt shows the source reference any more, and intake warns when a statement names a published profile | B/engine/prompts.py:111-121; B/engine/intake.py:28-33, 58-65 |
| 29 | sections/08-discussion.tex:95-97 | "removing it, with case-naming identifiers, is a precondition of the evaluation. \verify{how the leak was found ...} \todo{leak fix commit (Q5)}" | the described version removes it: opaque identifiers, a neutral title and namespace, NEW: for minted terms, and a scan of every stored prompt before a run counts (Sect. 6); keep the verify, drop the todo | scripts/run_reference_case.py:37-39, 64-78, 96-101, 129-133; B/engine/prompts.py:105-121 |
| 30 | sections/08-discussion.tex:107-108 | "anyone who reaches the server can use the key entered there, so the final say is organizational, not enforced" | still true; may add: a key goes only to the endpoint it was entered for, and blind mode hides sources from the reviewer, but without authentication anyone can switch it off | B/llm/registry.py:26-79, 115-118; B/engine/pipeline.py:644-648; B/api/app.py:294-308, 494-509 |
| 31 | sections/12-appendix-cd.tex:91-98 (Table 7 caption) | "every proposer, repairer and judge prompt printed each atom's source reference, the case and the section of the published profile" | caption stays (history). If Sect. 6 now says the provider sends a limit and an effort, add for runs 1-3: the provider sent no output limit or reasoning effort, and the replay cache spanned all projects of a store (run 2's replays) | @2b92d77 B/llm/openai_compatible.py:83-91; @2b92d77 B/store/blackboard.py:341-349; RUN3:16-17; @2b92d77 B/engine/prompts.py:112, 154-155 |
| 32 | sections/12-appendix-cd.tex:116-117 | "G1-S17: the prompt's feedback section is never filled." / "G1-S23: the development runs printed each atom's source reference" | both stay; G1-S17 src: prompts.py:190 -> 195, pipeline.py:188-191 -> 243-246; G1-S23 may add "the described version prints none" | B/engine/prompts.py:195; B/engine/pipeline.py:243-246; B/engine/prompts.py:111-121 |
| 33 | README.md:73 | "98 tests ... inputs/tool-facts-main-5ffd56e.txt" | 170 tests; inputs/tool-facts-main-21c6b5b.txt, inputs/tests-main-21c6b5b-2026-11-14.txt | paper/inputs/tests-main-21c6b5b-2026-11-14.txt:6 |
| 34 | README.md:76 | "PipelineConfig; at 5ffd56e lines 589-602" | at 21c6b5b lines 601-625; new defaults replay_cache "project", blind false | B/contracts.py:601-625 |
| 35 | README.md:241-246, 274 | Q5 "Fix it in the tool before any evaluation run. Three channels"; Q15 "The leak persists at 5ffd56e" | closed at 21c6b5b (all three channels); what stays: plain-word leak, LEAKCHECK lines of the first blind runs to be checked | Sect. 5 above |
| 36 | README.md:286-289 | Q20 options 1 and 2 | add option 3: `--modality unspecified` withholds the modality; recorded in the map and the summary | scripts/import_rq1_reference.py:56, 76, 80, 93 |
| 37 | README.md:337, 339, 340, 379, 393 | A1, A3, A4, C4, D2 rows (status "still present") | A1 fixed, A3 fixed, A4 fixed, C4 changed, D2 changed (Sect. 5) | Sect. 5 above |
| 38 | README.md:320 | Q32 "hide the target namespace per case" | still open: the run script sets no exclude_namespaces | scripts/run_reference_case.py:99-101 |

## 7. Notes

- History stays history: runs 1-3 ran engines (a52df71, 2b92d77) whose prompts printed the source line and the
  proposer's prompt the case-naming title (`@2b92d77 B/engine/prompts.py:112, 154-155`; same at a52df71), whose
  provider sent neither limit nor effort (`@2b92d77 B/llm/openai_compatible.py:83-91`), and whose replay cache
  was global (`@2b92d77 B/store/blackboard.py:341-349`). The fix does not change them.
- Out of this area but touched by the same sentences: stage order verify -> consolidate -> repair
  (`B/contracts.py:104-109`), `verify=False` now read (`B/engine/pipeline.py:149, 255, 347`), metrics fields. Leave to
  the pipeline/conditions digests.
- One model still plays all three roles in the runs; a separate judge model is configurable
  (`LLMSettings.step_models["judge"]`, `B/contracts.py:598`; `B/llm/client.py:54-58`), not used: no change needed
  in 08-discussion.tex:51 or the Fig. 1 caption.
- The cost measure "calls without cached replays" = metrics `llm_calls - llm_calls_cached` (both count records;
  P3); the run script's `CALLS` count includes replays.
- Anonymity: the run script's endpoint constant and the commit messages name the endpoint operator; the paper
  should keep saying "an OpenAI-compatible endpoint" and not "vLLM" unless verified.
