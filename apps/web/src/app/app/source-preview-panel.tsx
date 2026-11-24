"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { LeadApiError, type createLeadApi } from "../../lib/lead-api";
import {
  claimKinds,
  type ClaimKind,
  type CompetitorPreview,
  type SourcePreview,
} from "../../lib/source-preview-contract";

type Api = ReturnType<typeof createLeadApi>;
type Result =
  | { kind: "source"; source: SourcePreview }
  | { kind: "competitor"; preview: CompetitorPreview };

function failureMessage(error: unknown): string {
  if (error instanceof LeadApiError) {
    if (error.code === "SOURCE_BLOCKED")
      return "This exact URL is not approved for this operation.";
    if (error.code === "SOURCE_RATE_LIMITED")
      return "The source request limit was reached. Try again later.";
    if (error.code === "SOURCE_UNAVAILABLE")
      return "The reviewed source could not be retrieved.";
    if (error.status === 401 || error.status === 403)
      return "Your workspace access could not be verified.";
  }
  return "No verified preview is available. Check the URL and try again.";
}

function SourceDetails({ source }: { source: SourcePreview }) {
  return (
    <div className="crm-history">
      <h4>{source.title || "Retrieved source"}</h4>
      <p className="crm-meta">
        Publisher: {source.publisher} · Retrieved{" "}
        <time dateTime={source.retrieved_at}>
          {new Date(source.retrieved_at).toLocaleString()}
        </time>
      </p>
      <p className="crm-meta">{source.source_url}</p>
      <blockquote className="crm-evidence">{source.excerpt}</blockquote>
      <p className="crm-meta">Review: {source.policy_review_id}</p>
      <p className="crm-meta">
        Live retrieval preview · Not independently fact-verified · Not saved
      </p>
    </div>
  );
}

export function SourcePreviewPanel({
  api,
  workspaceId,
}: {
  api: Api;
  workspaceId: string;
}) {
  const [mode, setMode] = useState<"source" | "competitor">("source");
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [phrases, setPhrases] = useState<Record<ClaimKind, string>>({
    features: "",
    pricing: "",
    positioning: "",
  });
  const [result, setResult] = useState<Result | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  const clearResult = () => {
    setResult(null);
    setMessage("");
  };

  const preview = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending.current) return;
    const requested = url.trim();
    let parsed: URL;
    try {
      parsed = new URL(requested);
      if (
        parsed.protocol !== "https:" ||
        parsed.username ||
        parsed.password ||
        parsed.search ||
        parsed.hash ||
        (parsed.port && parsed.port !== "443")
      )
        throw new Error("Unsupported URL");
    } catch {
      setMessage("Enter an exact HTTPS URL without credentials or query.");
      setResult(null);
      return;
    }
    if (mode === "competitor" && (!name.trim() || !confirmed)) {
      setMessage("Confirm the named competitor and its URL first.");
      setResult(null);
      return;
    }
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    clearResult();
    try {
      const next: Result =
        mode === "source"
          ? {
              kind: "source",
              source: await api.previewSource(
                workspaceId,
                requested,
                controller.signal,
              ),
            }
          : {
              kind: "competitor",
              preview: await api.previewCompetitor(
                workspaceId,
                requested,
                name.trim(),
                claimKinds
                  .filter((kind) => phrases[kind].trim())
                  .map((kind) => ({ kind, locator: phrases[kind].trim() })),
                controller.signal,
              ),
            };
      if (!controller.signal.aborted) setResult(next);
    } catch (error) {
      if (!controller.signal.aborted) setMessage(failureMessage(error));
    } finally {
      pending.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  return (
    <section className="crm-history" aria-labelledby="source-preview-heading">
      <h4 id="source-preview-heading">Reviewed source research</h4>
      <p className="crm-meta">
        Only URLs approved by the server can be retrieved. No search coverage,
        saved research or independent claim verification is implied.
      </p>
      <form className="crm-form" onSubmit={(event) => void preview(event)}>
        <label htmlFor="source-preview-mode">Research type</label>
        <select
          id="source-preview-mode"
          value={mode}
          disabled={busy}
          onChange={(event) => {
            setMode(event.target.value === "competitor" ? "competitor" : "source");
            setConfirmed(false);
            clearResult();
          }}
        >
          <option value="source">Public source preview</option>
          <option value="competitor">Competitor claim preview</option>
        </select>
        <label htmlFor="source-preview-url">Exact reviewed HTTPS URL</label>
        <input
          id="source-preview-url"
          type="url"
          required
          maxLength={2048}
          value={url}
          disabled={busy}
          onChange={(event) => {
            setUrl(event.target.value);
            setConfirmed(false);
            clearResult();
          }}
        />
        {mode === "competitor" && (
          <>
            <label htmlFor="source-preview-name">Competitor name</label>
            <input
              id="source-preview-name"
              required
              maxLength={120}
              value={name}
              disabled={busy}
              onChange={(event) => {
                setName(event.target.value);
                setConfirmed(false);
                clearResult();
              }}
            />
            {claimKinds.map((kind) => (
              <div className="crm-form" key={kind}>
                <label htmlFor={"claim-" + kind}>
                  Exact {kind} phrase to check (optional)
                </label>
                <input
                  id={"claim-" + kind}
                  maxLength={200}
                  value={phrases[kind]}
                  disabled={busy}
                  onChange={(event) => {
                    setPhrases((previous) => ({
                      ...previous,
                      [kind]: event.target.value,
                    }));
                    clearResult();
                  }}
                />
              </div>
            ))}
            <label className="crm-inline-check">
              <input
                type="checkbox"
                required
                checked={confirmed}
                disabled={busy}
                onChange={(event) => setConfirmed(event.target.checked)}
              />
              I confirm this competitor and source URL.
            </label>
          </>
        )}
        <button type="submit" className="workspace-secondary" disabled={busy}>
          {busy ? "Retrieving…" : "Retrieve reviewed source"}
        </button>
      </form>
      {message && <p role="status">{message}</p>}
      {result && (
        <div aria-label="Source preview result">
          <SourceDetails
            source={result.kind === "source" ? result.source : result.preview.source}
          />
          {result.kind === "competitor" && (
            <>
              <h4>{result.preview.competitor_name} — publisher claims</h4>
              <p className="crm-meta">
                Exact phrases found in the excerpt; categories are supplied by
                you, not inferred by Axiom.
              </p>
              <ul>
                {result.preview.claims.map((claim) => (
                  <li key={claim.kind + ":" + claim.locator}>
                    {claim.kind}: {claim.locator}
                  </li>
                ))}
                {result.preview.unknowns.map((kind) => (
                  <li key={kind}>{kind}: Unknown</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </section>
  );
}
