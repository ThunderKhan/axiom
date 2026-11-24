"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  createLeadApi,
  LeadApiError,
  type LeadEdit,
  type NewLead,
} from "../../lib/lead-api";
import {
  normalizeLeadText,
  resolveFollowUpInstant,
  leadStages,
  type Lead,
  type LeadEvent,
  type LeadStage,
} from "../../lib/lead-contract";
import { publicApiBaseUrl } from "../../lib/public-api";
import type {
  EvidenceAssessment,
  ManualNeed,
} from "../../lib/evidence-contract";
import { createBrowserAuthClient } from "../../lib/supabase/browser";
import {
  subscribeToLocalSignOutStarted,
  subscribeToSignOut,
} from "../../lib/auth-sync";

import { ScenarioPanel } from "./scenario-panel";

function safeMessage(error: unknown): string {
  if (error instanceof LeadApiError) {
    if (error.status === 401 || error.status === 403)
      return "Your application access has changed. Sign in again.";
    if (error.code === "VERSION_CONFLICT")
      return "The lead changed. Review the latest version before trying again.";
    if (error.code === "IDEMPOTENCY_CONFLICT")
      return "This save key is already associated with different data.";
    if (error.code === "LEAD_ALREADY_SAVED")
      return "That source URL is already saved in this workspace. Check the list.";
    if (error.code === "VALIDATION_FAILED")
      return "Check the source URL, text lengths and follow-up details.";
    if (error.code === "NETWORK_UNCERTAIN" || error.status >= 500)
      return "The server may have saved this change. Inspect the records before trying again.";
  }
  return "The CRM response could not be verified. No change is assumed.";
}

function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const timestamp = new Date(iso);
  const local = new Date(
    timestamp.getTime() - timestamp.getTimezoneOffset() * 60_000,
  );
  return local.toISOString().slice(0, 16);
}

type Api = ReturnType<typeof createLeadApi>;

function ManualEvidenceReport({
  lead,
  workspaceId,
  api,
}: {
  lead: Lead;
  workspaceId: string;
  api: Api;
}) {
  const [requirement, setRequirement] = useState("");
  const [locator, setLocator] = useState("");
  const [intent, setIntent] = useState<ManualNeed["intent"]>("unknown");
  const [assessment, setAssessment] = useState<EvidenceAssessment | null>(null);
  const [assessedNeed, setAssessedNeed] = useState<ManualNeed | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => pending.current?.abort();
  }, []);

  const evaluate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    const requested = requirement.trim();
    const cited = locator.trim();
    if (!requested || !cited || requested.length > 120 || cited.length > 200) {
      setStatus(
        "Enter a bounded requirement and exact phrase from the saved excerpt.",
      );
      return;
    }
    const controller = new AbortController();
    pending.current?.abort();
    pending.current = controller;
    setAssessment(null);
    setAssessedNeed(null);
    setStatus("");
    setBusy(true);
    try {
      const report = await api.assess(
        workspaceId,
        lead,
        [{ requirement: requested, locator: cited, intent }],
        controller.signal,
      );
      if (!controller.signal.aborted) {
        setAssessment(report);
        setAssessedNeed({ requirement: requested, locator: cited, intent });
        setStatus("Read-only assessment complete. Nothing was saved or sent.");
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setStatus(
          error instanceof LeadApiError && error.code === "PROFILE_INCOMPLETE"
            ? "Confirm this workspace's product profile before assessing evidence."
            : error instanceof LeadApiError &&
                error.code === "VALIDATION_FAILED"
              ? "The required phrase must appear in the saved source excerpt."
              : "The report could not be verified. Review the source and try again.",
        );
      }
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  return (
    <section className="crm-history" aria-label="Manual evidence report">
      <h4>Evidence assessment</h4>
      <p className="crm-meta">
        Inspect a phrase from this saved citation against your confirmed product
        capabilities. Your citation and intent are not independently verified.
      </p>
      <form className="crm-form" onSubmit={(event) => void evaluate(event)}>
        <label htmlFor="evidence-requirement">Required capability</label>
        <input
          id="evidence-requirement"
          required
          maxLength={120}
          value={requirement}
          onChange={(event) => setRequirement(event.target.value)}
          disabled={busy}
          placeholder="Use an exact capability from your profile"
        />
        <label htmlFor="evidence-locator">
          Exact phrase in the saved excerpt
        </label>
        <input
          id="evidence-locator"
          required
          maxLength={200}
          value={locator}
          onChange={(event) => setLocator(event.target.value)}
          disabled={busy}
        />
        <label htmlFor="evidence-intent">Intent (your interpretation)</label>
        <select
          id="evidence-intent"
          value={intent}
          disabled={busy}
          onChange={(event) =>
            setIntent(event.target.value as ManualNeed["intent"])
          }
        >
          <option value="unknown">Unknown</option>
          <option value="discussion">General discussion</option>
          <option value="seeking_solution">Seeking a solution</option>
          <option value="buying">Buying intent (unverified)</option>
        </select>
        <button className="workspace-secondary" type="submit" disabled={busy}>
          {busy ? "Assessing…" : "Assess saved citation"}
        </button>
      </form>
      {status && (
        <p role="status" className="workspace-notice">
          {status}
        </p>
      )}
      {assessment && (
        <div aria-label="Assessment report">
          <p>
            <strong>Outcome:</strong> {assessment.verdict.replaceAll("_", " ")}
          </p>
          <p className="crm-meta">
            Manual source · Report not persisted · No live evidence verified
          </p>
          <h4>Source-linked relationships</h4>
          {assessment.relationships.length === 0 && (
            <p>No sourced needs linked.</p>
          )}
          <ul>
            {assessment.relationships.map((relation, index) => (
              <li key={index}>
                {relation.need_id}: {relation.relation.replaceAll("_", " ")}
                {relation.capability ? " · " + relation.capability : ""}
                {" — " + relation.explanation}
              </li>
            ))}
          </ul>
          <h4>Reasoned report</h4>
          <ul>
            {assessment.report_lines.map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
        </div>
      )}
      <ScenarioPanel
        api={api}
        workspaceId={workspaceId}
        lead={lead}
        baseline={
          assessment && assessedNeed
            ? {
                need: assessedNeed,
                profileRevision: assessment.confirmed_profile_revision,
              }
            : null
        }
      />
    </section>
  );
}

function LeadDetail({
  lead,
  workspaceId,
  api,
  onSaved,
  onArchived,
}: {
  lead: Lead;
  workspaceId: string;
  api: Api;
  onSaved: (lead: Lead) => void;
  onArchived: (id: string) => void;
}) {
  const [stage, setStage] = useState<LeadStage>(lead.stage);
  const [note, setNote] = useState(lead.note);
  const initialFollowUpLocal = toLocalInput(lead.follow_up_at);
  const [followUp, setFollowUp] = useState(initialFollowUpLocal);
  const [completed, setCompleted] = useState(lead.follow_up_done);
  const [draft, setDraft] = useState(lead.unsent_draft);
  const [history, setHistory] = useState<LeadEvent[] | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const active = useRef<AbortController | null>(null);
  const writing = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      active.current?.abort();
    };
  }, []);

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (writing.current) return;
    let payload: LeadEdit;
    try {
      payload = {
        expected_version: lead.version,
        stage,
        note: normalizeLeadText(note, 2000),
        follow_up_at: resolveFollowUpInstant(
          lead.follow_up_at,
          initialFollowUpLocal,
          followUp,
        ),
        follow_up_done: followUp ? completed : false,
        unsent_draft: normalizeLeadText(draft, 4000),
      };
    } catch {
      setMessage("Review the follow-up time and text fields.");
      return;
    }
    writing.current = true;
    setBusy(true);
    setMessage("");
    const controller = new AbortController();
    active.current = controller;
    try {
      const updated = await api.update(
        workspaceId,
        lead.id,
        payload,
        controller.signal,
      );
      if (!mounted.current || controller.signal.aborted) return;
      onSaved(updated);
      setMessage("Changes saved to your workspace.");
    } catch (error) {
      if (mounted.current && !controller.signal.aborted)
        setMessage(safeMessage(error));
    } finally {
      writing.current = false;
      if (mounted.current && !controller.signal.aborted) setBusy(false);
    }
  };

  const archive = async () => {
    if (writing.current || !window.confirm("Archive this saved lead?")) return;
    writing.current = true;
    setBusy(true);
    setMessage("");
    const controller = new AbortController();
    active.current = controller;
    try {
      await api.archive(workspaceId, lead.id, lead.version, controller.signal);
      if (!mounted.current || controller.signal.aborted) return;
      onArchived(lead.id);
    } catch (error) {
      if (mounted.current && !controller.signal.aborted)
        setMessage(safeMessage(error));
    } finally {
      writing.current = false;
      if (mounted.current && !controller.signal.aborted) setBusy(false);
    }
  };

  const showHistory = async () => {
    if (busy) return;
    setMessage("Loading workspace activity…");
    const controller = new AbortController();
    active.current?.abort();
    active.current = controller;
    try {
      const records = await api.history(
        workspaceId,
        lead.id,
        controller.signal,
      );
      if (!mounted.current || controller.signal.aborted) return;
      setHistory(records);
      setMessage("");
    } catch (error) {
      if (mounted.current && !controller.signal.aborted)
        setMessage(safeMessage(error));
    }
  };

  return (
    <article className="crm-detail" aria-labelledby="crm-lead-heading">
      <header className="crm-detail-heading">
        <div>
          <p className="eyebrow">SAVED OPPORTUNITY</p>
          <h3 id="crm-lead-heading">{lead.title}</h3>
          <p className="crm-meta">
            Manual source · No live verification claimed
          </p>
          <a href={lead.source_url} target="_blank" rel="noopener noreferrer">
            View original public citation
          </a>
        </div>
        <span className="workspace-count">Revision {lead.version}</span>
      </header>
      <blockquote className="crm-evidence">{lead.source_excerpt}</blockquote>
      <form className="crm-form" onSubmit={(event) => void save(event)}>
        <label htmlFor="lead-stage">Stage (recorded by you)</label>
        <select
          id="lead-stage"
          value={stage}
          disabled={busy}
          onChange={(event) => setStage(event.target.value as LeadStage)}
        >
          {leadStages.map((value) => (
            <option key={value} value={value}>
              {value.replace("_", " ")}
            </option>
          ))}
        </select>
        <label htmlFor="lead-note">Research notes</label>
        <textarea
          id="lead-note"
          rows={3}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          disabled={busy}
        />
        <label htmlFor="lead-due">
          Follow-up date and time (your local timezone)
        </label>
        <input
          id="lead-due"
          type="datetime-local"
          value={followUp}
          onChange={(event) => {
            setFollowUp(event.target.value);
            if (!event.target.value) setCompleted(false);
          }}
          disabled={busy}
        />
        <label className="crm-inline-check">
          <input
            type="checkbox"
            checked={completed}
            disabled={busy || !followUp}
            onChange={(event) => setCompleted(event.target.checked)}
          />
          Mark this follow-up completed
        </label>
        <label htmlFor="lead-draft">Outreach draft — not sent</label>
        <textarea
          id="lead-draft"
          rows={5}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={busy}
          placeholder="Write an optional human-reviewed draft. No message is sent."
        />
        <p className="crm-meta">
          Marking a lead contacted records your choice; it does not send a
          message or verify that anyone was contacted.
        </p>
        <div className="crm-actions">
          <button type="submit" className="workspace-primary" disabled={busy}>
            {busy ? "Saving…" : "Save changes"}
          </button>
          <button
            className="workspace-secondary"
            type="button"
            disabled={busy}
            onClick={() => void showHistory()}
          >
            Activity history
          </button>
          <button
            className="workspace-secondary"
            type="button"
            disabled={busy}
            onClick={() => void archive()}
          >
            Archive lead
          </button>
        </div>
      </form>
      <ManualEvidenceReport lead={lead} workspaceId={workspaceId} api={api} />
      {message && (
        <p className="workspace-notice" role="status">
          {message}
        </p>
      )}
      {history !== null && (
        <div className="crm-history" aria-label="Lead activity history">
          <h4>Recent activity</h4>
          {history.length === 0 && <p>No recorded activity.</p>}
          <ol>
            {history.map((event) => (
              <li key={event.id}>
                <strong>{event.event_type}</strong> ·{" "}
                {event.changed_fields.join(", ")}
                <time dateTime={event.created_at}>
                  {" · " + new Date(event.created_at).toLocaleString()}
                </time>
              </li>
            ))}
          </ol>
        </div>
      )}
    </article>
  );
}

export function LeadManager({
  subject,
  workspaceId,
}: {
  subject: string;
  workspaceId: string;
}) {
  const [items, setItems] = useState<Lead[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error" | "blocked">(
    "loading",
  );
  const [notice, setNotice] = useState("");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [creating, setCreating] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [inspectedUncertain, setInspectedUncertain] = useState(false);
  const saving = useRef(false);
  const pendingKey = useRef<string | null>(null);
  const active = useRef<AbortController | null>(null);
  const auth = useMemo(() => createBrowserAuthClient(), []);
  const api = useMemo(
    () =>
      createLeadApi(publicApiBaseUrl, subject, async (expected) => {
        const verified = await auth.auth.getClaims();
        if (
          verified.error ||
          verified.data?.claims?.sub !== expected ||
          verified.data.claims.role !== "authenticated" ||
          verified.data.claims.is_anonymous === true
        )
          throw new LeadApiError("AUTH_REQUIRED", 401);
        const session = await auth.auth.getSession();
        if (
          session.error ||
          !session.data.session ||
          session.data.session.user.id !== expected
        )
          throw new LeadApiError("AUTH_REQUIRED", 401);
        return session.data.session.access_token;
      }),
    [auth, subject],
  );

  const load = useCallback(async () => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setState("loading");
    setItems([]);
    setSelectedId(null);
    try {
      const records = await api.list(workspaceId, controller.signal);
      if (controller.signal.aborted) return;
      setItems(records);
      setState("ready");
      if (pendingKey.current) setInspectedUncertain(true);
      setNotice(
        records.length === 100
          ? "Showing the most recent 100 leads. Older records require API filters."
          : "",
      );
    } catch (error) {
      if (controller.signal.aborted) return;
      setItems([]);
      setSelectedId(null);
      setState(
        error instanceof LeadApiError && [401, 403].includes(error.status)
          ? "blocked"
          : "error",
      );
      setNotice(safeMessage(error));
    }
  }, [api, workspaceId]);

  useEffect(() => {
    let mounted = true;
    queueMicrotask(() => {
      if (mounted) void load();
    });
    const clear = () => {
      active.current?.abort();
      setItems([]);
      setSelectedId(null);
      setState("blocked");
    };
    const unsub = subscribeToSignOut(clear);
    const unsubLocal = subscribeToLocalSignOutStarted(clear);
    return () => {
      mounted = false;
      active.current?.abort();
      unsub();
      unsubLocal();
    };
  }, [load]);

  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (saving.current || uncertain) return;
    let payload: NewLead;
    try {
      payload = {
        title: normalizeLeadText(title.trim(), 180),
        source_url: url.trim(),
        source_excerpt: normalizeLeadText(excerpt.trim(), 500),
      };
      if (
        !payload.title ||
        !payload.source_excerpt ||
        !payload.source_url.startsWith("https://")
      )
        throw new Error("An HTTPS citation is required.");
    } catch {
      setNotice("Enter a title, HTTPS citation and excerpt within the limits.");
      return;
    }
    const key = crypto.randomUUID();
    pendingKey.current = key;
    setInspectedUncertain(false);
    saving.current = true;
    setCreating(true);
    setNotice("");
    const controller = new AbortController();
    active.current?.abort();
    active.current = controller;
    try {
      const result = await api.create(
        workspaceId,
        payload,
        key,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setItems((previous) => [
        result,
        ...previous.filter((item) => item.id !== result.id),
      ]);
      setSelectedId(result.id);
      setTitle("");
      setUrl("");
      setExcerpt("");
      pendingKey.current = null;
      setNotice(
        "Saved to your workspace. Manual citation, not live-verified evidence.",
      );
    } catch (error) {
      if (controller.signal.aborted) return;
      if (
        error instanceof LeadApiError &&
        (error.code === "NETWORK_UNCERTAIN" || error.status >= 500)
      )
        setUncertain(true);
      else pendingKey.current = null;
      setNotice(safeMessage(error));
    } finally {
      saving.current = false;
      if (!controller.signal.aborted) setCreating(false);
    }
  };

  const selected = items.find((item) => item.id === selectedId) ?? null;
  return (
    <section className="crm-panel" id="crm" aria-labelledby="crm-heading">
      <div className="crm-heading">
        <div>
          <p className="eyebrow">WORKSPACE ACTIONS</p>
          <h3 id="crm-heading">Saved opportunities</h3>
          <p className="crm-meta">
            Source links and excerpts here are supplied by you, not fetched or
            verified by Axiom. Records are private to this authorized workspace.
          </p>
        </div>
        <button
          type="button"
          className="workspace-secondary"
          onClick={() => void load()}
          disabled={creating}
        >
          Refresh records
        </button>
      </div>
      {state === "loading" && (
        <p role="status">Loading saved workspace leads…</p>
      )}
      {state === "blocked" && (
        <p role="alert">CRM access cannot be verified. {notice}</p>
      )}
      {state === "error" && <p role="alert">{notice}</p>}
      {state === "ready" && (
        <>
          <div className="crm-layout">
            <div className="crm-list">
              <h4>Most recent saved leads</h4>
              {items.length === 0 && (
                <p>No saved leads in this workspace yet.</p>
              )}
              <ul aria-label="Saved leads">
                {items.map((lead) => (
                  <li key={lead.id}>
                    <button
                      type="button"
                      className="crm-choice"
                      aria-pressed={lead.id === selectedId}
                      onClick={() => setSelectedId(lead.id)}
                    >
                      <strong>{lead.title}</strong>
                      <span>{lead.stage.replace("_", " ")}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
            {selected && (
              <LeadDetail
                key={selected.id + ":" + selected.version}
                lead={selected}
                workspaceId={workspaceId}
                api={api}
                onSaved={(changed) => {
                  setItems((records) =>
                    records.map((row) =>
                      row.id === changed.id ? changed : row,
                    ),
                  );
                  setNotice("Your lead has been updated.");
                }}
                onArchived={(id) => {
                  setItems((records) => records.filter((row) => row.id !== id));
                  setSelectedId(null);
                  setNotice("Lead archived. Its activity remains retained.");
                }}
              />
            )}
          </div>
          <form
            className="crm-form crm-create"
            onSubmit={(event) => void create(event)}
          >
            <h4>Save a source manually</h4>
            <p className="crm-meta">
              No crawling, enrichment or outreach is triggered.
            </p>
            <label htmlFor="crm-title">Opportunity title</label>
            <input
              id="crm-title"
              required
              value={title}
              disabled={creating || uncertain}
              onChange={(event) => setTitle(event.target.value)}
            />
            <label htmlFor="crm-source">Public HTTPS source URL</label>
            <input
              id="crm-source"
              type="url"
              required
              maxLength={2048}
              placeholder="https://example.org/discussion"
              value={url}
              disabled={creating || uncertain}
              onChange={(event) => setUrl(event.target.value)}
            />
            <label htmlFor="crm-excerpt">
              Source excerpt (manually entered)
            </label>
            <textarea
              id="crm-excerpt"
              required
              rows={3}
              value={excerpt}
              disabled={creating || uncertain}
              onChange={(event) => setExcerpt(event.target.value)}
            />
            <button
              type="submit"
              className="workspace-primary"
              disabled={creating || uncertain}
            >
              {creating ? "Saving…" : "Save opportunity"}
            </button>
            {uncertain && (
              <div className="workspace-warning" role="alert">
                <p>
                  The last save outcome is uncertain. Inspect the authorized
                  list before attempting a separate save with a new key.
                </p>
                <button
                  type="button"
                  className="workspace-secondary"
                  onClick={() => void load()}
                >
                  Inspect saved leads
                </button>
                <button
                  type="button"
                  className="workspace-secondary"
                  disabled={!inspectedUncertain}
                  onClick={() => {
                    setUncertain(false);
                    setInspectedUncertain(false);
                    pendingKey.current = null;
                    setNotice(
                      "Start a separate attempt only after checking for duplicates.",
                    );
                  }}
                >
                  I inspected; allow a separate attempt
                </button>
              </div>
            )}
          </form>
        </>
      )}
      {notice && state === "ready" && (
        <p className="workspace-notice" role="status">
          {notice}
        </p>
      )}
    </section>
  );
}
