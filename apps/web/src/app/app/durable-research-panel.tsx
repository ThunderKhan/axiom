"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { LeadApiError, type createLeadApi } from "../../lib/lead-api";
import type { Lead } from "../../lib/lead-contract";
import type { ResearchRequest, ResearchRun, SignalAssessment } from "../../lib/research-contract";

type Api = ReturnType<typeof createLeadApi>;

function failure(error: unknown): string {
  if (error instanceof LeadApiError) {
    if (error.code === "PROFILE_INCOMPLETE")
      return "Confirm your founder profile before starting research.";
    if (error.code === "SOURCE_BLOCKED")
      return "This feed is not approved for persistent research.";
    if (error.code === "SOURCE_RATE_LIMITED")
      return "Source request limit reached. Retry later with the same request.";
    if (error.code === "LEAD_ALREADY_SAVED")
      return "This citation is already saved in the workspace.";
    if (error.code === "VERSION_CONFLICT")
      return "The profile changed. Reopen the workspace and start a new research request.";
    if (error.status === 401 || error.status === 403)
      return "Access could not be verified.";
  }
  return "The request was not confirmed. Retry the same operation or reopen its saved record.";
}

export function DurableResearchPanel({
  api, workspaceId, onSaved,
}: {
  api: Api;
  workspaceId: string;
  onSaved: (lead: Lead) => void;
}) {
  const [url, setUrl] = useState("");
  const [query, setQuery] = useState("");
  const [runId, setRunId] = useState("");
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [requirement, setRequirement] = useState("");
  const [locator, setLocator] = useState("");
  const [report, setReport] = useState<SignalAssessment | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const pending = useRef<AbortController | null>(null);
  const [retry, setRetry] = useState<{ request: ResearchRequest; key: string } | null>(null);
  const saves = useRef(new Map<string, string>());
  useEffect(() => () => pending.current?.abort(), []);

  const execute = async (action: (signal: AbortSignal) => Promise<void>) => {
    if (pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    setMessage("");
    try {
      await action(controller.signal);
    } catch (error) {
      if (!controller.signal.aborted) setMessage(failure(error));
    } finally {
      pending.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  const discover = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void execute(async (signal) => {
      const requested = url.trim();
      const parsed = new URL(requested);
      if (parsed.protocol !== "https:" || parsed.username || parsed.password ||
          parsed.search || parsed.hash || (parsed.port && parsed.port !== "443"))
        throw new Error("Invalid reviewed URL");
      let attempt = retry;
      if (!attempt) {
        const profile = await api.confirmedProfileId(workspaceId, signal);
        if (signal.aborted) return;
        attempt = {
          request: { profile_version_id: profile, url: requested, query: query.trim(), limit: 10 },
          key: crypto.randomUUID(),
        };
        setRetry(attempt);
      }
      const result = await api.discoverFeed(workspaceId, attempt.request, attempt.key, signal);
      if (signal.aborted) return;
      setRetry(null);
      setRun(result);
      setSelected(null);
      setReport(null);
      setRunId(result.run_id);
      setMessage("Research run saved. No buying intent inferred.");
    });
  };

  const reopen = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void execute(async (signal) => {
      const result = await api.reopenResearch(workspaceId, runId.trim(), signal);
      if (signal.aborted) return;
      setRun(result);
      setSelected(null);
      setReport(null);
      setMessage("Saved research reopened.");
    });
  };

  const chosen = run?.items.find((item) => item.signal_id === selected);
  const assess = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!run || !chosen) return;
    void execute(async (signal) => {
      setReport(null);
      const next = await api.assessResearchSignal(
        workspaceId, run, chosen, requirement.trim(), locator.trim(), signal,
      );
      if (!signal.aborted) setReport(next);
    });
  };

  const save = (item: ResearchRun["items"][number]) => {
    if (!run) return;
    void execute(async (signal) => {
      const identity = run.run_id + ":" + item.signal_id;
      const key = saves.current.get(identity) ?? crypto.randomUUID();
      saves.current.set(identity, key);
      const lead = await api.saveResearchSignal(workspaceId, run.run_id, item, key, signal);
      if (signal.aborted) return;
      onSaved(lead);
      setMessage("Citation saved to CRM with its original research provenance.");
    });
  };

  return (
    <section className="crm-history" aria-labelledby="durable-research-heading">
      <h4 id="durable-research-heading">Saved feed research</h4>
      <p className="crm-meta">
        Only feeds approved for retention are available. Each run uses a confirmed profile.
        An article citation is not verified customer demand.
      </p>
      <form className="crm-form" onSubmit={discover}>
        <label htmlFor="durable-feed-url">Exact approved feed URL</label>
        <input id="durable-feed-url" type="url" required maxLength={2048}
          value={url} disabled={busy || retry !== null}
          onChange={(event) => setUrl(event.target.value)} />
        <label htmlFor="durable-feed-query">Literal filter terms</label>
        <input id="durable-feed-query" maxLength={120} value={query}
          disabled={busy || retry !== null}
          onChange={(event) => setQuery(event.target.value)} />
        <button className="workspace-secondary" disabled={busy} type="submit">
          {retry ? "Retry same research request" : "Retrieve and save research"}
        </button>
        {retry && (
          <button className="workspace-secondary" type="button" disabled={busy}
            onClick={() => {
              setRetry(null);
              setMessage("Previous request may have completed. A new request uses a new key.");
            }}>
            Start a different request
          </button>
        )}
      </form>
      <form className="crm-form" onSubmit={reopen}>
        <label htmlFor="research-run-id">Saved run ID</label>
        <input id="research-run-id" required maxLength={36} value={runId}
          disabled={busy} onChange={(event) => setRunId(event.target.value)} />
        <button className="workspace-secondary" type="submit" disabled={busy}>
          Reopen research
        </button>
      </form>
      {message && <p role="status">{message}</p>}
      {run && (
        <div className="crm-history">
          <h4>Saved results</h4>
          <p className="crm-meta">
            {run.publisher} · Profile revision {run.profile_revision} ·{" "}
            {new Date(run.retrieved_at).toLocaleString()}
          </p>
          <p className="crm-meta">Review: {run.policy_review_id}</p>
          <p className="crm-meta">Run ID: {run.run_id}</p>
          {!run.items.length && <p>No matching entries in the retrieved feed.</p>}
          <ul>
            {run.items.map((item) => (
              <li key={item.signal_id}>
                <strong>{item.title}</strong>
                <blockquote className="crm-evidence">{item.excerpt}</blockquote>
                <a href={item.source_url} target="_blank" rel="noopener noreferrer">
                  Original article citation
                </a>
                <button type="button" className="workspace-secondary" disabled={busy}
                  onClick={() => {
                    setSelected(item.signal_id);
                    setRequirement("");
                    setLocator("");
                    setReport(null);
                  }}>
                  Assess citation
                </button>
                <button type="button" className="workspace-secondary" disabled={busy}
                  onClick={() => save(item)}>
                  Save citation to CRM
                </button>
              </li>
            ))}
          </ul>
          {chosen && (
            <form className="crm-form" onSubmit={assess}>
              <h4>Assess {chosen.title}</h4>
              <blockquote className="crm-evidence">{chosen.excerpt}</blockquote>
              <label htmlFor="signal-requirement">Requirement in the excerpt</label>
              <input id="signal-requirement" required maxLength={120} value={requirement}
                disabled={busy} onChange={(event) => {
                  setRequirement(event.target.value);
                  setReport(null);
                }} />
              <label htmlFor="signal-locator">Exact supporting phrase</label>
              <input id="signal-locator" required maxLength={200} value={locator}
                disabled={busy} onChange={(event) => {
                  setLocator(event.target.value);
                  setReport(null);
                }} />
              <button className="workspace-secondary" type="submit" disabled={busy}>
                Assess against original founder profile
              </button>
              {report && (
                <div aria-label="Retrieved evidence assessment">
                  <h4>{report.verdict.replaceAll("_", " ")}</h4>
                  <p>Compatibility: {report.compatibility}. Intent: unknown.</p>
                  <p className="crm-meta">Computed report; article claims not independently verified.</p>
                  <ul>{report.report_lines.map((line, index) => <li key={index}>{line}</li>)}</ul>
                </div>
              )}
            </form>
          )}
        </div>
      )}
    </section>
  );
}
