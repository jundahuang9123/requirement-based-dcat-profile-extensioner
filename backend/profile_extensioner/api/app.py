"""HTTP API of the workbench. Everything the UI shows comes from here.

Run:  uvicorn profile_extensioner.api.app:app --port 8020   (from ``backend/``)
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..contracts import (
    STAGE_ORDER,
    Atom,
    LLMSettings,
    PipelineConfig,
    ProfileChange,
    Project,
    stable_id,
)
from ..engine.intake import lint_atom, parse_atom_set
from ..engine.pipeline import Pipeline
from ..engine.verbalise import verbalise_change
from ..knowledge import DATA_DIR, latest_base_profile_id, list_base_profiles, list_dcat_versions, load_knowledge_base
from ..llm.base import LLMError
from ..llm.registry import PROVIDERS, Credentials, build_provider, default_settings, provider_status
from ..store.blackboard import Store

WORKSPACE = Path(os.environ.get("RBDPE_WORKSPACE", Path.cwd() / ".workspace"))
FRONTEND_DIST = Path(os.environ.get("RBDPE_FRONTEND_DIST", Path(__file__).resolve().parents[3] / "frontend" / "dist"))

app = FastAPI(title="requirement-based-dcat-profile-extensioner", version="0.1.0")
store = Store(WORKSPACE / "blackboard.sqlite3")
credentials = Credentials()
_locks: dict[str, threading.Lock] = {}
_running: dict[str, str] = {}


_locks_guard = threading.Lock()


def _lock(project_id: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(project_id, threading.Lock())


class _Exclusive:
    """Hold the project's lock for a human action; refuse while a run is in progress."""

    def __init__(self, project_id: str) -> None:
        self.lock = _lock(project_id)

    def __enter__(self) -> None:
        if not self.lock.acquire(timeout=5):
            raise HTTPException(409, "A run is in progress for this project; try again when it has finished.")

    def __exit__(self, *exc: object) -> None:
        self.lock.release()


def _pipeline(project_id: str) -> Pipeline:
    try:
        return Pipeline(store, credentials, project_id)
    except KeyError as exc:
        raise HTTPException(404, f"Unknown project or base profile: {exc}") from exc


# -- models -----------------------------------------------------------------


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    base_profile_id: str | None = None           # default: the atom set's base, else the newest DCAT-AP release
    profile_title: str = ""
    profile_namespace: str = "https://example.org/profile#"
    profile_prefix: str = "ex"
    atoms_text: str | None = None      # YAML or JSON atom set
    example: str | None = None         # name of a bundled example atom set


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    profile_title: str | None = None
    config: PipelineConfig | None = None
    llm: LLMSettings | None = None


class AtomsUpload(BaseModel):
    text: str


class RunRequest(BaseModel):
    from_stage: str = "intake"
    only: str | None = None            # run a single stage
    atom_ids: list[str] | None = None  # for propose: only these atoms


class DecisionRequest(BaseModel):
    status: str
    by: str = "reviewer"
    note: str = ""


class RebaseRequest(BaseModel):
    base_profile_id: str
    by: str = "reviewer"
    note: str = ""


class RebaseApplyRequest(BaseModel):
    choices: dict[str, str] = {}                 # plan item id -> choice; the default where missing
    by: str = "reviewer"
    note: str = ""


class EditRequest(BaseModel):
    change: ProfileChange
    by: str = "reviewer"
    note: str = ""


class AssessmentOverride(BaseModel):
    disposition: str
    reason: str
    by: str = "reviewer"


class SignOffRequest(BaseModel):
    by: str
    note: str = ""


class KeyRequest(BaseModel):
    provider: str
    api_key: str = ""
    base_url: str | None = None                  # the endpoint the key is for (OpenAI-compatible); it goes nowhere else


EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples"


# -- system -----------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "workspace": str(WORKSPACE)}


@app.get("/api/base-profiles")
def base_profiles() -> list[dict[str, Any]]:
    return [info.model_dump() for info in list_base_profiles()]


@app.get("/api/dcat-versions")
def dcat_versions() -> list[dict[str, Any]]:
    """Every vendored W3C DCAT version, oldest first; the newest is ``is_latest``."""
    return [info.model_dump() for info in list_dcat_versions(DATA_DIR)]


@app.get("/api/base-profiles/{base_id}")
def base_profile(base_id: str) -> dict[str, Any]:
    try:
        kb = load_knowledge_base(base_id, profile_namespace="https://example.org/x#", profile_prefix="x")
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    info = next((item for item in list_base_profiles() if item.id == base_id), kb.base.info)
    dcat = kb.dcat
    unprofiled = {}
    for cls in kb.base.classes():
        listed = [prop for prop in dcat.properties_for(cls.iri) if kb.base.element(cls.iri, prop.path) is None]
        if listed:
            unprofiled[cls.iri] = [{"path": prop.path, "curie": kb.curie(prop.path), "label": prop.label,
                                    "listed_on": prop.listed_on, "definition": prop.definition} for prop in listed]
    return {
        "info": info.model_dump(),
        "classes": [c.model_dump() for c in kb.base.classes()],
        "elements": [e.model_dump() for e in kb.base.elements()],
        "prefixes": kb.prefixes.as_dict(),
        "dcat": {
            "version": dcat.version.model_dump(),
            "basis": dcat.basis.model_dump(),
            "summary": dcat.summary(kb.base.info.title),
            # DCAT properties of the pinned version that the base does not profile on a class
            # (DCAT-AP 3.x: optional fields of that class by the base's own rule)
            "unprofiled_properties": unprofiled,
        },
    }


@app.get("/api/examples")
def examples() -> list[str]:
    return sorted(path.parent.name for path in EXAMPLES_DIR.glob("*/atoms.yaml"))


@app.get("/api/llm/providers")
def providers() -> list[dict[str, Any]]:
    return provider_status(credentials)


@app.post("/api/llm/key")
def set_key(request: KeyRequest) -> list[dict[str, Any]]:
    """Keeps the key in server memory only. It is never stored, logged or returned."""
    if request.provider not in PROVIDERS:
        raise HTTPException(400, "unknown provider")
    credentials.set(request.provider, request.api_key.strip(), request.base_url)
    return provider_status(credentials)


@app.post("/api/llm/models")
def list_models(settings: LLMSettings) -> list[str]:
    try:
        return build_provider(settings, credentials).list_models()
    except LLMError as exc:
        raise HTTPException(400, str(exc)) from exc


# -- projects ---------------------------------------------------------------


@app.get("/api/projects")
def projects() -> list[dict[str, Any]]:
    return [p.model_dump() for p in store.list_projects()]


@app.post("/api/projects")
def create_project(request: ProjectCreate) -> dict[str, Any]:
    text = request.atoms_text
    if request.example:
        path = EXAMPLES_DIR / request.example / "atoms.yaml"
        if not path.exists():
            raise HTTPException(404, "unknown example")
        text = path.read_text(encoding="utf-8")
    atom_set = None
    if text:
        try:
            atom_set = parse_atom_set(text)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    # The base: as asked; else as the atom set declares it; else the newest DCAT-AP release (on the newest DCAT).
    known = {info.id: info for info in list_base_profiles()}
    titles = {info.title.lower(): info.id for info in known.values()}
    if request.base_profile_id:
        base_id = request.base_profile_id
        if base_id not in known:
            raise HTTPException(400, f"unknown base profile {base_id!r}; known: {', '.join(known)}")
    else:
        declared = [titles.get(str(value).strip().lower(), str(value).strip())
                    for value in (atom_set.base_profile_ids if atom_set else [])]
        base_id = next((value for value in declared if value in known), None) or latest_base_profile_id()
    project = Project(
        id=stable_id("prj", request.name, request.profile_namespace, os.urandom(4).hex()),
        name=request.name, description=request.description or (atom_set.description if atom_set else ""),
        base_profile_id=base_id, profile_title=request.profile_title or request.name,
        profile_namespace=request.profile_namespace, profile_prefix=request.profile_prefix,
        llm=default_settings(),
    )
    store.save_project(project)
    if atom_set:
        store.replace_atoms(project.id, atom_set.atoms)
    _pipeline(project.id)  # validates the base profile id
    return project.model_dump()


@app.get("/api/projects/{project_id}")
def snapshot(project_id: str) -> dict[str, Any]:
    pipeline = _pipeline(project_id)
    data = pipeline.snapshot().model_dump()
    data["running"] = _running.get(project_id)
    data["verbalised"] = {c.id: verbalise_change(c, pipeline.kb) for c in pipeline.changes()}
    data["prefixes"] = pipeline.kb.prefixes.as_dict()
    return data


@app.patch("/api/projects/{project_id}")
def update_project(project_id: str, request: ProjectUpdate) -> dict[str, Any]:
    with _Exclusive(project_id):
        project = store.get_project(project_id)
        if project is None:
            raise HTTPException(404, "unknown project")
        before = project.model_copy(deep=True)
        for field in ("name", "description", "profile_title", "config", "llm"):
            value = getattr(request, field)
            if value is not None:
                setattr(project, field, value)
        _mark_settings_stale(before, project)
        store.save_project(project)
        return project.model_dump()


RETRIEVAL_FIELDS = ("retrieval", "top_k", "use_hints", "exclude_namespaces")
DECISION_FIELDS = ("verify", "repair_rounds", "attribution_check", "votes", "auto_accept", "auto_accept_min_confidence",
                   "later_dcat_terms", "require_human_signoff", "replay_cache")


def _mark_settings_stale(before: Project, after: Project) -> None:
    """A run made under other settings is stale from the first stage those settings feed (and unreleased)."""
    old, new = before.config, after.config
    if any(getattr(old, f) != getattr(new, f) for f in RETRIEVAL_FIELDS):
        first = "retrieve"
    elif before.llm != after.llm or old.votes != new.votes:
        first = "propose"
    elif any(getattr(old, f) != getattr(new, f) for f in DECISION_FIELDS):
        first = "verify"
    else:
        return
    for stage in STAGE_ORDER[STAGE_ORDER.index(first):]:
        if after.stage_states.get(stage) == "done":
            after.stage_states[stage] = "stale"
    after.signoff = None


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str) -> dict[str, str]:
    store.delete_project(project_id)
    return {"deleted": project_id}


@app.put("/api/projects/{project_id}/atoms")
def replace_atoms(project_id: str, request: AtomsUpload) -> list[dict[str, Any]]:
    try:
        atom_set = parse_atom_set(request.text)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    with _Exclusive(project_id):
        store.replace_atoms(project_id, atom_set.atoms)
    return [a.model_dump() for a in atom_set.atoms]


@app.put("/api/projects/{project_id}/atoms/{atom_id}")
def save_atom(project_id: str, atom_id: str, atom: Atom) -> dict[str, Any]:
    atom.id = atom_id
    with _Exclusive(project_id):
        store.save_atom(project_id, atom)
    return {"atom": atom.model_dump(), "lint": [i.model_dump() for i in lint_atom(atom)]}


def _execute(project_id: str, request: RunRequest, lock: threading.Lock) -> None:
    """Run stages while holding ``lock`` (acquired by the caller); releases it at the end."""
    try:
        pipeline = _pipeline(project_id)
        if request.only:
            if request.only not in STAGE_ORDER:
                raise HTTPException(400, "unknown stage")
            _running[project_id] = request.only
            step = getattr(pipeline, f"run_{request.only}", None)
            if step is None:
                raise HTTPException(400, f"stage {request.only} cannot be run on its own")
            step(request.atom_ids) if request.only == "propose" else step()
        else:
            _running[project_id] = request.from_stage
            pipeline.run_all(from_stage=request.from_stage)
    except LLMError as exc:
        raise HTTPException(502, f"Model provider error: {exc}") from exc
    finally:
        _running.pop(project_id, None)
        lock.release()


@app.post("/api/projects/{project_id}/run")
def run(project_id: str, request: RunRequest) -> dict[str, Any]:
    _pipeline(project_id)
    lock = _lock(project_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "A run is already in progress for this project.")
    _execute(project_id, request, lock)
    return snapshot(project_id)


@app.post("/api/projects/{project_id}/run-async")
def run_async(project_id: str, request: RunRequest) -> dict[str, Any]:
    """Start a run in the background; poll the snapshot (``running``) and the log."""
    _pipeline(project_id)
    lock = _lock(project_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "A run is already in progress for this project.")
    _running[project_id] = request.only or request.from_stage

    def work() -> None:
        try:
            _execute(project_id, request, lock)
        except HTTPException as exc:
            store_pipeline = Pipeline(store, credentials, project_id)
            store_pipeline.log(request.only or request.from_stage, "error", str(exc.detail))
        except Exception as exc:  # noqa: BLE001 - the error is reported on the blackboard
            Pipeline(store, credentials, project_id).log(request.only or request.from_stage, "error", f"{exc}")

    threading.Thread(target=work, daemon=True).start()
    return {"started": request.only or request.from_stage}


@app.get("/api/projects/{project_id}/entries")
def entries(project_id: str, after: int = 0, subject_id: str | None = None, stage: str | None = None) -> list[dict[str, Any]]:
    return [e.model_dump() for e in store.list_entries(project_id, after_seq=after, subject_id=subject_id, stage=stage)]


@app.get("/api/projects/{project_id}/calls")
def calls(project_id: str, subject_id: str | None = None) -> list[dict[str, Any]]:
    return [c.model_dump() for c in store.list_llm_calls(project_id, subject_id=subject_id)]


@app.post("/api/projects/{project_id}/rebase/preview")
def rebase_preview(project_id: str, request: RebaseRequest) -> dict[str, Any]:
    """Plan a move onto another base (DCAT-AP release, and so its DCAT): one item per finding, with
    choices and a default. Nothing changes until the plan is applied."""
    try:
        with _Exclusive(project_id):
            return _pipeline(project_id).rebase_preview(request.base_profile_id, request.by).model_dump()
    except KeyError as exc:
        raise HTTPException(404, f"Unknown base profile: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/projects/{project_id}/rebase/{plan_id}/apply")
def rebase_apply(project_id: str, plan_id: str, request: RebaseApplyRequest) -> dict[str, Any]:
    try:
        with _Exclusive(project_id):
            return _pipeline(project_id).rebase_apply(plan_id, request.choices, request.by, request.note).model_dump()
    except KeyError as exc:
        raise HTTPException(404, f"No pending rebase plan {exc}") from exc
    except ValueError as exc:
        raise HTTPException(409 if "preview it again" in str(exc) else 400, str(exc)) from exc


@app.delete("/api/projects/{project_id}/rebase/{plan_id}")
def rebase_cancel(project_id: str, plan_id: str, by: str = "reviewer") -> dict[str, Any]:
    try:
        with _Exclusive(project_id):
            _pipeline(project_id).rebase_cancel(plan_id, by)
            return {"cancelled": plan_id}
    except KeyError as exc:
        raise HTTPException(404, f"No pending rebase plan {exc}") from exc


@app.post("/api/projects/{project_id}/rebase")
def rebase(project_id: str, request: RebaseRequest) -> dict[str, Any]:
    """Preview and apply with every default choice in one step (for scripts)."""
    try:
        with _Exclusive(project_id):
            return _pipeline(project_id).rebase(request.base_profile_id, request.by, request.note).model_dump()
    except KeyError as exc:
        raise HTTPException(404, f"Unknown base profile: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/projects/{project_id}/changes/{change_id}/decision")
def decide(project_id: str, change_id: str, request: DecisionRequest) -> dict[str, Any]:
    try:
        with _Exclusive(project_id):
            return _pipeline(project_id).decide(change_id, request.status, request.by, request.note).model_dump()
    except KeyError as exc:
        raise HTTPException(404, "unknown change") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.put("/api/projects/{project_id}/changes/{change_id}")
def edit(project_id: str, change_id: str, request: EditRequest) -> dict[str, Any]:
    try:
        with _Exclusive(project_id):
            return _pipeline(project_id).edit_change(change_id, request.change, request.by, request.note).model_dump()
    except KeyError as exc:
        raise HTTPException(404, "unknown change") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/projects/{project_id}/atoms/{atom_id}/assessment")
def override(project_id: str, atom_id: str, request: AssessmentOverride) -> dict[str, Any]:
    with _Exclusive(project_id):
        return _pipeline(project_id).override_assessment(atom_id, request.disposition, request.reason, request.by).model_dump()


@app.post("/api/projects/{project_id}/signoff")
def signoff(project_id: str, request: SignOffRequest) -> dict[str, Any]:
    try:
        with _Exclusive(project_id):
            return _pipeline(project_id).sign_off(request.by, request.note).model_dump()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/projects/{project_id}/artifacts/{name}")
def artifact(project_id: str, name: str) -> Response:
    found = store.get_artifact(project_id, name)
    if found is None:
        raise HTTPException(404, "not compiled yet")
    return PlainTextResponse(found.content, media_type=found.media_type,
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/api/projects/{project_id}/export")
def export(project_id: str) -> dict[str, Any]:
    """The full record of a project: state, blackboard log and model calls. Contains no API keys."""
    return store.export_project(project_id)


@app.get("/api/terms")
def search_terms(project_id: str, q: str, kind: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    from ..engine.retrieve import SPECIALISED_VOCABULARIES

    pipeline = _pipeline(project_id)
    hits = []
    for hit in pipeline.kb.vocab.search(q, kind=kind, limit=limit * 3):
        in_base = pipeline.kb.base.uses_term(hit.term.iri)
        weight = 1.0 if in_base else SPECIALISED_VOCABULARIES.get(hit.term.vocabulary, 1.0)
        hits.append({**hit.term.model_dump(), "curie": pipeline.kb.curie(hit.term.iri),
                     "score": round(hit.score * weight, 4), "in_base": in_base})
    return sorted(hits, key=lambda item: -item["score"])[:limit]


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        target = FRONTEND_DIST / path
        return FileResponse(target if path and target.is_file() else FRONTEND_DIST / "index.html")
