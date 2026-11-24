"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { LeadApiError, type createLeadApi } from "../../lib/lead-api";
import type { Lead } from "../../lib/lead-contract";
import type { ManualNeed } from "../../lib/evidence-contract";
import type {
  SavedComparison,
  ScenarioAssumption,
  ScenarioRequest,
} from "../../lib/scenario-contract";

type Api = ReturnType<typeof createLeadApi>;
type Baseline = { need: ManualNeed; profileRevision: number };
type Draft = {
  name: string;
  action: "add" | "remove";
  pricing: string;
  positioning: string;
};

function initialDraft(name: string, action: Draft["action"]): Draft {
  return { name, action, pricing: "", positioning: "" };
}

function assumptions(draft: Draft, need: ManualNeed): ScenarioAssumption {
  return {
    name: draft.name.trim(),
    features: [{ name: need.requirement, action: draft.action }],
    pricing: draft.pricing.trim() || null,
    positioning: draft.positioning.trim() || null,
  };
}

function ComparisonDetails({ saved }: { saved: SavedComparison }) {
  const result = saved.comparison;
  return (
    <article className="crm-history">
      <h4>Saved hypothetical comparison</h4>
      <p className="crm-meta">
        Profile revision {saved.confirmed_profile_revision} · Lead revision{" "}
        {saved.lead_version} · Manual evidence, not live verified
      </p>
      <blockquote className="crm-evidence">{saved.source_excerpt}</blockquote>
      <p>Baseline: {result.baseline_verdict.replaceAll("_", " ")}</p>
      <ul>
        {result.baseline_requirements.map((need) => (
          <li key={need.need_id}>
            {need.requirement}: {need.state.replaceAll("_", " ")}
          </li>
        ))}
      </ul>
      {result.scenarios.map((scenario) => (
        <section key={scenario.name} className="crm-history">
          <h4>{scenario.name}</h4>
          <p>
            Hypothetical verdict:{" "}
            {scenario.projected_verdict.replaceAll("_", " ")}
          </p>
          <ul>
            {scenario.requirements.map((need, index) => (
              <li key={need.need_id}>
                {need.requirement}:{" "}
                {result.baseline_requirements[index].state.replaceAll("_", " ")}
                {" → "}
                {need.state.replaceAll("_", " ")}
              </li>
            ))}
          </ul>
          <h5>Unsupported assumptions and limitations</h5>
          <ul>
            {[...scenario.unsupported_assumptions, ...scenario.limitations].map(
              (line, index) => (
                <li key={index}>{line}</li>
              ),
            )}
          </ul>
        </section>
      ))}
    </article>
  );
}

export function ScenarioPanel({
  api,
  workspaceId,
  lead,
  baseline,
}: {
  api: Api;
  workspaceId: string;
  lead: Lead;
  baseline: Baseline | null;
}) {
  const [drafts, setDrafts] = useState<Draft[]>([
    initialDraft("Add capability", "add"),
    initialDraft("Remove capability", "remove"),
  ]);
  const [items, setItems] = useState<SavedComparison[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef<AbortController | null>(null);
  const [retry, setRetry] = useState<{
    key: string;
    payload: ScenarioRequest;
  } | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  const update = (index: number, patch: Partial<Draft>) => {
    setDrafts((previous) =>
      previous.map((draft, i) => (i === index ? { ...draft, ...patch } : draft)),
    );
  };

  const load = async () => {
    if (pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    setNotice("");
    try {
      const records = await api.listComparisons(
        workspaceId,
        lead,
        controller.signal,
      );
      if (!controller.signal.aborted) {
        setItems(records);
        setSelected(records[0]?.id ?? null);
        setNotice(
          records.length
            ? "Saved comparisons loaded."
            : "No saved comparisons yet.",
        );
      }
    } catch {
      if (!controller.signal.aborted)
        setNotice("Saved comparisons could not be verified.");
    } finally {
      pending.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending.current) return;
    let attempt = retry;
    if (!attempt) {
      if (!baseline) return;
      const scenarios = drafts.map((draft) => assumptions(draft, baseline.need));
      if (
        scenarios.some(
          (item) => !item.name || (!item.pricing && !item.positioning),
        ) ||
        scenarios[0].name.toLowerCase() === scenarios[1].name.toLowerCase()
      ) {
        setNotice(
          "Use distinct names and a qualitative assumption for each alternative.",
        );
        return;
      }
      attempt = {
        key: crypto.randomUUID(),
        payload: {
          needs: [baseline.need],
          expected_lead_version: lead.version,
          expected_profile_revision: baseline.profileRevision,
          scenarios,
        },
      };
      setRetry(attempt);
    }
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    setNotice("");
    try {
      const saved = await api.saveComparison(
        workspaceId,
        lead,
        attempt.payload,
        attempt.key,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setRetry(null);
      setItems((previous) =>
        [saved, ...previous.filter((item) => item.id !== saved.id)].slice(0, 5),
      );
      setSelected(saved.id);
      setNotice("Both alternatives and their frozen baseline were saved.");
    } catch (error) {
      if (controller.signal.aborted) return;
      if (
        error instanceof LeadApiError &&
        error.status >= 400 &&
        error.status < 500
      ) {
        setRetry(null);
        setNotice(
          error.code === "VERSION_CONFLICT"
            ? "Baseline changed. Assess the current citation again before saving."
            : "The comparison was rejected. Review your inputs and access.",
        );
      } else {
        setNotice(
          "Save outcome uncertain. Retry the exact same request and key.",
        );
      }
    } finally {
      pending.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  const viewed = items.find((item) => item.id === selected);
  const locked = busy || retry !== null;
  return (
    <section className="crm-history" aria-label="Counterfactual Lab">
      <h4>Counterfactual Lab</h4>
      <p className="crm-meta">
        Explore two named alternatives using fixed cited evidence. These are
        hypothetical capability changes, never commercial forecasts.
      </p>
      {baseline ? (
        <form className="crm-form" onSubmit={(event) => void save(event)}>
          <p>
            Baseline: {baseline.need.requirement} · Profile revision{" "}
            {baseline.profileRevision}
          </p>
          {drafts.map((draft, index) => (
            <fieldset className="crm-form" key={index} disabled={locked}>
              <legend>Alternative {index + 1}</legend>
              <label>
                Name
                <input
                  required
                  maxLength={80}
                  value={draft.name}
                  onChange={(e) => update(index, { name: e.target.value })}
                />
              </label>
              <label>
                Capability change
                <select
                  value={draft.action}
                  onChange={(event) =>
                    update(index, {
                      action: event.target.value === "add" ? "add" : "remove",
                    })
                  }
                >
                  <option value="add">Add cited capability</option>
                  <option value="remove">Remove cited capability</option>
                </select>
              </label>
              <label>
                Qualitative pricing hypothesis
                <input
                  maxLength={300}
                  value={draft.pricing}
                  onChange={(event) =>
                    update(index, { pricing: event.target.value })
                  }
                />
              </label>
              <label>
                Positioning hypothesis
                <input
                  maxLength={300}
                  value={draft.positioning}
                  onChange={(event) =>
                    update(index, { positioning: event.target.value })
                  }
                />
              </label>
            </fieldset>
          ))}
          <button className="workspace-primary" disabled={busy} type="submit">
            {busy
              ? "Working…"
              : retry
                ? "Retry exact save"
                : "Save two alternatives"}
          </button>
        </form>
      ) : (
        <p>Assess the saved citation to establish a new comparison baseline.</p>
      )}
      <button
        type="button"
        className="workspace-secondary"
        disabled={busy}
        onClick={() => void load()}
      >
        Reopen recent saved comparisons
      </button>
      {notice && <p role="status">{notice}</p>}
      {items.length > 0 && (
        <ul aria-label="Saved scenario comparisons">
          {items.map((item) => (
            <li key={item.id}>
              <button
                className="workspace-secondary"
                type="button"
                aria-pressed={selected === item.id}
                onClick={() => setSelected(item.id)}
              >
                {item.comparison.scenarios
                  .map((scenario) => scenario.name)
                  .join(" / ")}
                {" · "}
                {new Date(item.created_at).toLocaleString()}
              </button>
            </li>
          ))}
        </ul>
      )}
      {viewed && <ComparisonDetails saved={viewed} />}
    </section>
  );
}
