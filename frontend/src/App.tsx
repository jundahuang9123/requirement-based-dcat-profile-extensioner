import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { KeyRound, Play, RefreshCw, ShieldCheck, Upload, Download, Settings2 } from 'lucide-react';
import { api, compact, STAGES, type BaseProfile, type BaseProfileInfo, type Entry, type LLMSettings, type PipelineConfig, type Project, type ProviderStatus, type Snapshot } from './api';
import { ProfileCanvas } from './Canvas';
import { Inspector, type Selection } from './Inspector';

type Tab = 'canvas' | 'review' | 'conformance' | 'artefacts' | 'log';
const STAGE_LABEL: Record<string, string> = {
  intake: 'Intake', retrieve: 'Retrieve', propose: 'Propose', verify: 'Verify', repair: 'Repair',
  consolidate: 'Consolidate', compile: 'Compile', conformance: 'Conformance', review: 'Review & sign-off',
};

function Pill({ value }: { value: string }) {
  return <span className={`pill pill--${value}`}>{value.replace(/_/g, ' ')}</span>;
}

function NewProject({ onCreated, notify }: { onCreated: (p: Project) => void; notify: (m: string) => void }) {
  const [examples, setExamples] = useState<string[]>([]);
  const [bases, setBases] = useState<BaseProfileInfo[]>([]);
  // '' = the base the atom set declares, otherwise the newest DCAT-AP release (decided by the server)
  const [form, setForm] = useState({ name: '', base_profile_id: '', profile_namespace: 'https://example.org/profile#', profile_prefix: 'ex', example: '', atoms_text: '' });
  useEffect(() => { api.examples().then(setExamples); api.baseProfiles().then(setBases); }, []);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const latest = bases.find((b) => b.is_latest);
  const chosen = bases.find((b) => b.id === form.base_profile_id) ?? latest;
  const describe = (b: BaseProfileInfo) => `${b.title}${b.release_date ? ` (${b.release_date})` : ''}${b.dcat ? ` · on ${b.dcat.label}` : ''}`;
  return (
    <div className="new-project">
      <h2>New extension project</h2>
      <label>Name <input value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="e.g. Materials-testing lab profile" /></label>
      <label>Base profile
        <select value={form.base_profile_id} onChange={(e) => set('base_profile_id', e.target.value)}>
          <option value="">{latest ? `as the atoms declare, else the newest: ${describe(latest)}` : 'as the atoms declare, else the newest'}</option>
          {[...bases].reverse().map((b) => <option key={b.id} value={b.id}>{describe(b)}{b.is_latest ? ' · newest' : ''}</option>)}</select></label>
      {chosen?.dcat && <p className="muted small">{chosen.title} builds on W3C {chosen.dcat.label}
        {chosen.dcat.dcat_status_at_release ? ` (status then: ${chosen.dcat.dcat_status_at_release})` : ''}.
        {chosen.dcat.unlisted_dcat_properties === 'optional' ? ' DCAT properties it does not list for a class are optional fields of that class.' : ''}</p>}
      <div className="row">
        <label>Namespace for new terms <input value={form.profile_namespace} onChange={(e) => set('profile_namespace', e.target.value)} /></label>
        <label>Prefix <input value={form.profile_prefix} onChange={(e) => set('profile_prefix', e.target.value)} /></label>
      </div>
      <label>Requirement atoms
        <select value={form.example} onChange={(e) => set('example', e.target.value)}>
          <option value="">paste YAML / JSON below</option>
          {examples.map((x) => <option key={x} value={x}>example: {x}</option>)}</select></label>
      {!form.example && <textarea rows={8} value={form.atoms_text} onChange={(e) => set('atoms_text', e.target.value)}
        placeholder={'atoms:\n  - id: a1\n    statement: Each distribution must state its licence.\n    subject: distribution\n    modality: must'} />}
      <button type="button" className="primary" disabled={!form.name} onClick={async () => {
        try {
          const created = await api.createProject({ ...form, base_profile_id: form.base_profile_id || undefined,
            example: form.example || undefined, atoms_text: form.atoms_text || undefined });
          onCreated(created);
        } catch (e) { notify(String(e)); }
      }}>Create</button>
    </div>
  );
}

const CHOICE_LABEL: Record<string, string> = {
  keep: 'keep', withdraw: 'withdraw the change', replace: 'replace the term', manual: 'decide later (review queue)',
  repropose: 'propose again', keep_claim: 'keep "covered by the base"',
};

function RebasePanel({ project, reviewer, onDone, notify }: { project: Project; reviewer: string; onDone: () => void; notify: (m: string) => void }) {
  const [bases, setBases] = useState<BaseProfileInfo[]>([]);
  const [target, setTarget] = useState('');
  const [busy, setBusy] = useState(false);
  const plan = project.pending_rebase ?? null;
  const [choices, setChoices] = useState<Record<string, string>>({});
  useEffect(() => { api.baseProfiles().then((list) => { setBases(list); setTarget(list.find((b) => b.is_latest && b.id !== project.base_profile_id)?.id ?? ''); }); }, [project.base_profile_id]);
  useEffect(() => { setChoices(Object.fromEntries((plan?.items ?? []).map((item) => [item.id, item.default_choice]))); }, [plan?.plan_id]);
  const act = async (fn: () => Promise<unknown>, done: string) => {
    setBusy(true);
    try { await fn(); notify(done); onDone(); } catch (e) { notify(String(e)); } finally { setBusy(false); }
  };
  return (
    <div className="panel">
      <h3>Base profile</h3>
      <p className="muted small">This extension builds on <b>{project.base_profile_id}</b>. Rebasing moves it onto another DCAT-AP release
        (and so onto that release's DCAT). Preview first: nothing changes until you apply the plan. Your earlier decisions stay.</p>
      {!plan && (
        <div className="row">
          <select value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="">choose a base…</option>
            {[...bases].reverse().filter((b) => b.id !== project.base_profile_id).map((b) =>
              <option key={b.id} value={b.id}>{b.title} ({b.release_date}) · on {b.dcat?.label}{b.is_latest ? ' · newest' : ''}</option>)}
          </select>
          <button type="button" disabled={!target || busy} onClick={() => act(() => api.rebasePreview(project.id, target, reviewer), 'Rebase plan ready')}>
            {busy ? 'Working…' : 'Preview rebase'}</button>
        </div>)}
      {plan && (<>
        <p><b>Plan {plan.from_base} → {plan.to_base}</b> <span className="muted small">({plan.from_dcat} → {plan.to_dcat}) {plan.summary}</span></p>
        {plan.items.length === 0 && <p className="muted">Nothing is affected.</p>}
        {plan.items.map((item) => (
          <div key={item.id} className={`issue issue--${item.severity === 'error' ? 'error' : item.severity === 'warning' ? 'warning' : 'info'}`}>
            <div><b>{item.finding.replace(/_/g, ' ')}</b> {item.change_id ?? item.atom_id}{item.human_decided ? ' · decided by a person earlier' : ''}</div>
            <div className="small">{item.message}</div>
            {item.choices.length > 1 ? (
              <select value={choices[item.id] ?? item.default_choice} onChange={(e) => setChoices({ ...choices, [item.id]: e.target.value })}>
                {item.choices.map((c) => <option key={c} value={c}>{CHOICE_LABEL[c] ?? c}{c === 'replace' && item.replacement ? ` → ${compact(item.replacement, {})}` : ''}{c === item.default_choice ? ' (default)' : ''}</option>)}
              </select>) : <span className="muted small">{CHOICE_LABEL[item.default_choice] ?? item.default_choice}</span>}
          </div>))}
        <div className="row">
          <button type="button" className="primary" disabled={busy}
            onClick={() => act(() => api.rebaseApply(project.id, plan.plan_id, choices, reviewer), `Moved onto ${plan.to_base}`)}>
            {busy ? 'Applying…' : `Apply and move to ${plan.to_base}`}</button>
          <button type="button" disabled={busy} onClick={() => act(() => api.rebaseCancel(project.id, plan.plan_id, reviewer), 'Rebase cancelled')}>Cancel</button>
        </div>
      </>)}
    </div>
  );
}

function ModelPanel({ project, onSaved, notify }: { project: Project; onSaved: () => void; notify: (m: string) => void }) {
  const [settings, setSettings] = useState<LLMSettings>(project.llm);
  const [config, setConfig] = useState<PipelineConfig>(project.config);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [key, setKey] = useState('');
  const [models, setModels] = useState<string[]>([]);
  useEffect(() => { api.providers().then(setProviders); }, []);
  const status = providers.find((x) => x.provider === settings.provider);
  return (
    <div className="panel model-panel">
      <h3>Model provider</h3>
      <p className="muted">The model makes the decisions; you review. API keys stay in the server's memory only: never stored, logged or exported.</p>
      <label>Provider
        <select value={settings.provider} onChange={(e) => setSettings({ ...settings, provider: e.target.value as LLMSettings['provider'], model: null })}>
          {providers.map((x) => <option key={x.provider} value={x.provider}>{x.label}</option>)}</select></label>
      {status && <p className="muted">{status.note} Key: <b>{status.key_source}</b></p>}
      {settings.provider === 'openai-compatible' && <label>Base URL <input value={settings.base_url ?? ''} onChange={(e) => setSettings({ ...settings, base_url: e.target.value || null })} placeholder="https://host/v1" /></label>}
      {settings.provider !== 'mock' && (<>
        <label>API key <input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder={status?.key_source !== 'none' ? '(a key is set)' : 'paste key'} /></label>
        <button type="button" disabled={settings.provider === 'openai-compatible' && !settings.base_url}
          title={settings.provider === 'openai-compatible' ? 'The key is sent to this base URL only' : ''}
          onClick={async () => { try { setProviders(await api.setKey(settings.provider, key, settings.base_url)); setKey(''); notify('Key set for this server session'); } catch (e) { notify(String(e)); } }}>
          <KeyRound size={15} /> Use key</button>
      </>)}
      <label>Model
        <div className="row"><input value={settings.model ?? ''} placeholder={status?.default_model ?? ''} list="models" onChange={(e) => setSettings({ ...settings, model: e.target.value || null })} />
          {settings.provider !== 'mock' && <button type="button" onClick={async () => { try { setModels(await api.models(settings)); } catch (e) { notify(String(e)); } }}>List</button>}</div>
        <datalist id="models">{models.map((m) => <option key={m} value={m} />)}</datalist></label>
      <label>Effort <select value={settings.effort} onChange={(e) => setSettings({ ...settings, effort: e.target.value })}>
        {['low', 'medium', 'high', 'xhigh', 'max'].map((x) => <option key={x}>{x}</option>)}</select></label>
      <h3>Pipeline</h3>
      <div className="grid2">
        <label><input type="checkbox" checked={config.retrieval} onChange={(e) => setConfig({ ...config, retrieval: e.target.checked })} /> Retrieval</label>
        <label><input type="checkbox" checked={config.attribution_check} onChange={(e) => setConfig({ ...config, attribution_check: e.target.checked })} /> Judge: atom supports change</label>
        <label title="DCAT terms that only a DCAT version later than the base's own DCAT defines (check D1)">Later DCAT terms
          <select value={config.later_dcat_terms ?? 'review'} onChange={(e) => setConfig({ ...config, later_dcat_terms: e.target.value as PipelineConfig['later_dcat_terms'] })}>
            <option value="review">a human decides</option><option value="forbid">not allowed</option><option value="allow">allowed (note only)</option>
          </select></label>
        <label><input type="checkbox" checked={config.auto_accept} onChange={(e) => setConfig({ ...config, auto_accept: e.target.checked })} /> Model decisions stand unless overruled</label>
        <label><input type="checkbox" checked={config.use_hints} onChange={(e) => setConfig({ ...config, use_hints: e.target.checked })} /> Show upstream term hints</label>
        <label>Top-k <input type="number" value={config.top_k} onChange={(e) => setConfig({ ...config, top_k: Number(e.target.value) })} /></label>
        <label>Repair rounds <input type="number" value={config.repair_rounds} onChange={(e) => setConfig({ ...config, repair_rounds: Number(e.target.value) })} /></label>
        <label>Votes per atom <input type="number" min={1} value={config.votes} onChange={(e) => setConfig({ ...config, votes: Number(e.target.value) })} /></label>
        <label>Min confidence to stand <input type="number" step="0.05" value={config.auto_accept_min_confidence} onChange={(e) => setConfig({ ...config, auto_accept_min_confidence: Number(e.target.value) })} /></label>
      </div>
      <label>Hide namespaces from the index (one per line)
        <textarea rows={2} value={config.exclude_namespaces.join('\n')} onChange={(e) => setConfig({ ...config, exclude_namespaces: e.target.value.split('\n').map((x) => x.trim()).filter(Boolean) })} /></label>
      <button type="button" className="primary" onClick={async () => { await api.updateProject(project.id, { llm: settings, config }); notify('Settings saved'); onSaved(); }}>Save</button>
    </div>
  );
}

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<string | null>(() => localStorage.getItem('rbdpe.project'));
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [base, setBase] = useState<BaseProfile | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [selection, setSelection] = useState<Selection>(null);
  const [tab, setTab] = useState<Tab>('canvas');
  const [panel, setPanel] = useState<'none' | 'new' | 'model'>('none');
  const [message, setMessage] = useState('');
  const [reviewer, setReviewer] = useState(() => localStorage.getItem('rbdpe.reviewer') || 'reviewer');
  const [showRejected, setShowRejected] = useState(false);
  const [artefact, setArtefact] = useState('README.md');
  const fileInput = useRef<HTMLInputElement>(null);
  const notify = useCallback((m: string) => { setMessage(m); window.setTimeout(() => setMessage(''), 6000); }, []);

  const loadProjects = useCallback(() => api.projects().then(setProjects), []);
  const refresh = useCallback(async () => {
    if (!projectId) return;
    try {
      const snap = await api.snapshot(projectId);
      setSnapshot(snap);
      setEntries(await api.entries(projectId));
    } catch (e) { notify(String(e)); }
  }, [projectId, notify]);

  useEffect(() => { loadProjects(); }, [loadProjects]);
  useEffect(() => { if (projectId) localStorage.setItem('rbdpe.project', projectId); setSelection(null); refresh(); }, [projectId, refresh]);
  useEffect(() => { localStorage.setItem('rbdpe.reviewer', reviewer); }, [reviewer]);
  useEffect(() => { if (snapshot) api.baseProfile(snapshot.project.base_profile_id).then(setBase); }, [snapshot?.project.base_profile_id]);
  useEffect(() => {   // poll while a run is going
    if (!snapshot?.running) return;
    const timer = window.setInterval(refresh, 1500);
    return () => window.clearInterval(timer);
  }, [snapshot?.running, refresh]);

  const run = async (body: { from_stage?: string; only?: string }) => {
    if (!projectId) return;
    try { await api.runAsync(projectId, body); notify(`Running ${body.only ?? `from ${body.from_stage}`}…`); window.setTimeout(refresh, 400); }
    catch (e) { notify(String(e)); }
  };

  const queue = useMemo(() => (snapshot?.changes ?? []).filter((c) => c.decision.status === 'needs_review'), [snapshot]);
  const decided = useMemo(() => (snapshot?.changes ?? []).filter((c) => ['auto_accepted', 'accepted', 'rejected'].includes(c.decision.status)), [snapshot]);
  const p = snapshot?.prefixes ?? {};

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand"><strong>Profile Extensioner</strong><span className="muted">requirement-based DCAT profile extension</span></div>
        <select value={projectId ?? ''} onChange={(e) => setProjectId(e.target.value || null)}>
          <option value="">— choose a project —</option>
          {projects.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
        </select>
        <button type="button" onClick={() => setPanel(panel === 'new' ? 'none' : 'new')}>New project</button>
        {snapshot && base && <span className="base-chip" title={base.dcat?.summary ?? ''}>
          {base.info.title}{base.dcat ? <> · <b>{base.dcat.version.label}</b></> : null}</span>}
        {snapshot && <button type="button" onClick={() => setPanel(panel === 'model' ? 'none' : 'model')}><Settings2 size={15} /> Model &amp; pipeline</button>}
        <label className="reviewer">Reviewer <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></label>
        {message && <span className="toast">{message}</span>}
      </header>

      {panel === 'new' && <NewProject notify={notify} onCreated={(created) => { setPanel('none'); loadProjects(); setProjectId(created.id); }} />}
      {panel === 'model' && snapshot && <ModelPanel project={snapshot.project} notify={notify} onSaved={() => { setPanel('none'); refresh(); }} />}
      {panel === 'model' && snapshot && <RebasePanel project={snapshot.project} reviewer={reviewer} notify={notify} onDone={() => { setPanel('none'); refresh(); }} />}

      {!snapshot ? <p className="empty">Choose or create a project. The bundled example is a fictional materials-testing laboratory.</p> : (<>
        <nav className="stepper">
          {STAGES.map((stage, index) => {
            const state = snapshot.running === stage ? 'running' : snapshot.project.stage_states[stage] ?? 'pending';
            return (
              <button key={stage} type="button" className={`step step--${state}`} disabled={!!snapshot.running || stage === 'review'}
                onClick={() => run({ only: stage })} title={stage === 'review' ? 'Review happens on the workbench' : `Run ${stage} only`}>
                <span className="step__n">{index + 1}</span><span>{STAGE_LABEL[stage]}</span><Pill value={state} />
              </button>);
          })}
          <button type="button" className="primary" disabled={!!snapshot.running} onClick={() => run({ from_stage: 'intake' })}><Play size={15} /> Run all</button>
          <button type="button" onClick={refresh}><RefreshCw size={15} /></button>
        </nav>

        <main className="workspace">
          <aside className="atoms">
            <div className="atoms__head"><h3>Requirement atoms</h3>
              <button type="button" title="Replace atoms from a YAML / JSON file" onClick={() => fileInput.current?.click()}><Upload size={15} /></button>
              <input ref={fileInput} type="file" accept=".yaml,.yml,.json" hidden onChange={async (e) => {
                const file = e.target.files?.[0]; if (!file) return;
                try { await api.replaceAtoms(snapshot.project.id, await file.text()); notify('Atoms replaced'); refresh(); } catch (err) { notify(String(err)); }
              }} /></div>
            {snapshot.atoms.map((atom) => {
              const assessment = snapshot.assessments.find((a) => a.atom_id === atom.id);
              const lint = assessment?.lint.filter((i) => i.severity !== 'info') ?? [];
              return (
                <button key={atom.id} type="button" className={`atom ${selection?.type === 'atom' && selection.id === atom.id ? 'is-selected' : ''} ${atom.active ? '' : 'atom--inactive'}`}
                  onClick={() => setSelection({ type: 'atom', id: atom.id })}>
                  <div className="atom__head"><b>{atom.id}</b><span className={`modality modality--${atom.modality}`}>{atom.modality}</span>
                    {atom.active ? <Pill value={snapshot.coverage[atom.id] ?? 'pending'} /> : <span className="muted">inactive</span>}</div>
                  <div className="atom__text">{atom.statement}</div>
                  {lint.length > 0 && <div className="atom__lint">⚠ {lint.map((i) => i.code).join(', ')}</div>}
                </button>);
            })}
          </aside>

          <section className="center">
            <div className="tabs">
              {(['canvas', 'review', 'conformance', 'artefacts', 'log'] as Tab[]).map((t) => (
                <button key={t} type="button" className={tab === t ? 'is-active' : ''} onClick={() => setTab(t)}>
                  {t === 'canvas' ? 'Profile canvas' : t === 'review' ? `Review queue (${queue.length})` : t === 'conformance' ? 'Conformance' : t === 'artefacts' ? 'Artefacts' : 'Blackboard log'}
                </button>))}
            </div>

            {tab === 'canvas' && (<>
              <div className="legend"><span className="class-row--refine_property">refine (tightens base)</span><span className="class-row--reuse_property">reuse existing term</span>
                <span className="class-row--mint_property">new term</span>
                <label><input type="checkbox" checked={showRejected} onChange={(e) => setShowRejected(e.target.checked)} /> show rejected</label></div>
              <ProfileCanvas snapshot={snapshot} base={base} showRejected={showRejected}
                selected={selection?.type === 'change' ? selection.id : null} onSelect={(id) => setSelection({ type: 'change', id })} />
            </>)}

            {tab === 'review' && (
              <div className="review">
                <p className="muted">The model decided everything that passed its checks. Only what it could not settle is queued here; you can overrule any decision at any time.</p>
                <h4>Waiting for you ({queue.length})</h4>
                {queue.length === 0 && <p className="muted">Nothing waits for review.</p>}
                {queue.map((c) => (
                  <button key={c.id} type="button" className="review-card" onClick={() => setSelection({ type: 'change', id: c.id })}>
                    <div><Pill value={c.kind} /> <b>{c.covers.map((l) => l.atom_id).join(', ')}</b> <span className="muted">{c.decision.note}</span></div>
                    <div>{snapshot.verbalised[c.id]}</div>
                  </button>))}
                {snapshot.conflicts.length > 0 && (<><h4>Conflicts</h4>{snapshot.conflicts.map((x) => <div key={x.id} className="issue issue--error">{x.description}</div>)}</>)}
                {snapshot.project.pending_rebase && <div className="issue issue--warning">A rebase onto {snapshot.project.pending_rebase.to_base} is
                  planned ({snapshot.project.pending_rebase.items.length} item(s)); open <b>Model &amp; pipeline</b> to apply or cancel it. Sign-off waits for it.</div>}
                {(snapshot.project.rebases ?? []).length > 0 && (() => {
                  const last = snapshot.project.rebases![snapshot.project.rebases!.length - 1];
                  return (<><h4>Rebase {last.from_base} → {last.to_base} ({last.items.length} finding(s))</h4>
                    <p className="muted small">{last.summary}</p>
                    {last.items.map((item, i) => (
                      <button key={i} type="button" className={`issue issue--${item.severity === 'error' ? 'error' : item.severity === 'warning' ? 'warning' : 'info'}`}
                        onClick={() => item.change_id ? setSelection({ type: 'change', id: item.change_id }) : item.atom_id ? setSelection({ type: 'atom', id: item.atom_id }) : undefined}>
                        <b>{item.finding.replace(/_/g, ' ')}</b> · {item.chosen ? `chosen: ${item.chosen}` : `suggested: ${item.suggestion}`}{item.replacement ? ` ${compact(item.replacement, p)}` : ''} — {item.message}
                      </button>))}</>);
                })()}
                <h4>Decided ({decided.length})</h4>
                {decided.map((c) => (
                  <button key={c.id} type="button" className="review-card review-card--decided" onClick={() => setSelection({ type: 'change', id: c.id })}>
                    <div><Pill value={c.decision.status} /> <b>{c.covers.map((l) => l.atom_id).join(', ')}</b> <span className="muted">by {c.decision.decided_by}</span></div>
                    <div>{snapshot.verbalised[c.id]}</div>
                  </button>))}
                <div className="signoff">
                  <h4><ShieldCheck size={16} /> Final review</h4>
                  {snapshot.project.signoff ? <p>Released by <b>{snapshot.project.signoff.by}</b> on {snapshot.project.signoff.at} (change set {snapshot.project.signoff.change_set_hash}).</p> : (
                    <button type="button" className="primary" onClick={async () => {
                      const note = window.prompt('Release note (optional)') ?? '';
                      try { await api.signoff(snapshot.project.id, reviewer, note); notify('Profile released'); refresh(); } catch (e) { notify(String(e)); }
                    }}>Sign off and release as {reviewer}</button>)}
                </div>
              </div>)}

            {tab === 'conformance' && (
              <div className="conformance">
                {!snapshot.conformance ? <p className="empty">Not checked yet. Run the Conformance stage.</p> : (<>
                  <h3><Pill value={snapshot.conformance.verdict} /> {snapshot.conformance.summary}</h3>
                  {snapshot.project.stage_states.conformance === 'stale' && <p className="issue issue--warning">Decisions changed since this check. Run it again before release.</p>}
                  <table className="checks"><thead><tr><th>Rule</th><th>Result</th><th>Details</th><th>Source</th></tr></thead><tbody>
                    {snapshot.conformance.checks.map((c) => (
                      <tr key={c.id}><td><b>{c.id}</b> {c.title}</td><td><Pill value={c.passed ? 'passed' : c.severity === 'error' ? 'failed' : 'warning'} /></td>
                        <td>{c.message}{c.items.length > 0 && <ul className="plain">{c.items.slice(0, 12).map((i, k) => (
                          <li key={k}>{[compact(i.target_class, p), compact(i.path, p), i.facet].filter(Boolean).join(' · ')} {i.base_value ? `${compact(i.base_value, p)} → ${compact(i.new_value, p)}` : ''} {i.message}</li>))}</ul>}</td>
                        <td className="muted">{c.source}</td></tr>))}
                  </tbody></table>
                  {snapshot.conformance.witness_turtle && <details><summary>Witness data validated against the base</summary><pre>{snapshot.conformance.witness_turtle}</pre></details>}
                </>)}
              </div>)}

            {tab === 'artefacts' && (
              <div className="artefacts">
                <div className="row">{snapshot.artifacts.map((a) => (
                  <button key={a.name} type="button" className={artefact === a.name ? 'is-active' : ''} onClick={() => setArtefact(a.name)}>{a.title}</button>))}
                  {snapshot.artifacts.length > 0 && <a className="button" href={`/api/projects/${snapshot.project.id}/artifacts/${artefact}`}><Download size={15} /> Download</a>}
                  <a className="button" href={`/api/projects/${snapshot.project.id}/export`} target="_blank" rel="noreferrer">Full record (JSON)</a></div>
                {snapshot.artifacts.length === 0 ? <p className="empty">Nothing compiled yet.</p> :
                  <pre className="code">{snapshot.artifacts.find((a) => a.name === artefact)?.content}</pre>}
              </div>)}

            {tab === 'log' && (
              <div className="log">
                {entries.slice().reverse().map((e) => (
                  <div key={e.seq} className={`entry entry--${e.kind}`}>
                    <span className="muted">#{e.seq} {e.created_at.slice(11, 19)}</span> <Pill value={e.stage} /> <b>{e.kind}</b>{' '}
                    {e.subject_id && <button type="button" className="link" onClick={() => setSelection(e.subject_type === 'atom' ? { type: 'atom', id: e.subject_id } : { type: 'change', id: e.subject_id })}>{e.subject_id}</button>}{' '}
                    <span className="muted">{e.author}</span><div>{e.summary}</div>
                  </div>))}
              </div>)}
          </section>

          <Inspector snapshot={snapshot} selection={selection} select={setSelection} reviewer={reviewer} refresh={refresh} notify={notify} />
        </main>
      </>)}
    </div>
  );
}
