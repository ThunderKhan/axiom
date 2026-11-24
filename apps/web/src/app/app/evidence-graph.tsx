"use client";

import { useRef, useState } from "react";
import type { EvidenceAssessment } from "../../lib/evidence-contract";
import type { Lead } from "../../lib/lead-contract";

const relationLabels = {
  supports_need: "Cited need",
  covers: "Declared coverage",
  contradicts: "Missing capability",
  unverified: "Uncertain coverage",
} as const;

export function EvidenceGraph({
  assessment,
  lead,
}: {
  assessment: EvidenceAssessment;
  lead: Lead;
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const buttons = useRef<Array<HTMLButtonElement | null>>([]);
  const relation =
    selected === null ? null : assessment.relationships[selected];
  return (
    <section className="evidence-graph" aria-label="Evidence graph">
      <h4>Evidence graph</h4>
      <p className="crm-meta">
        Select a relationship to inspect its reasoning and original citation.
        Every connection comes from the assessment, not inferred graph links.
      </p>
      {assessment.relationships.length === 0 ? (
        <p>No relationships yet. Add a cited requirement to begin.</p>
      ) : (
        <>
          <div className="evidence-graph-source">
            <span className="crm-meta">SOURCE · USER PROVIDED</span>
            <strong>{lead.title}</strong>
            <a href={lead.source_url} target="_blank" rel="noopener noreferrer">
              Open original citation
            </a>
          </div>
          <ul className="evidence-graph-edges" aria-label="Relationship edges">
            {assessment.relationships.map((edge, index) => (
              <li key={index}>
                <button
                  ref={(element) => {
                    buttons.current[index] = element;
                  }}
                  type="button"
                  className="evidence-edge"
                  aria-pressed={selected === index}
                  onClick={() => setSelected(index)}
                  onKeyDown={(event) => {
                    if (event.key === "Escape") setSelected(null);
                  }}
                >
                  <span className="evidence-edge-label">
                    {relationLabels[edge.relation]}
                  </span>
                  <span className="evidence-node">
                    Need {edge.need_id.replace("need-", "")}
                  </span>
                  {edge.capability && (
                    <>
                      <span aria-hidden="true">→</span>
                      <span className="evidence-node">{edge.capability}</span>
                    </>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      {relation && (
        <section
          className="evidence-inspector"
          aria-label="Selected relationship details"
          onKeyDown={(event) => {
            if (event.key === "Escape" && selected !== null) {
              buttons.current[selected]?.focus();
              setSelected(null);
            }
          }}
        >
          <h4>{relationLabels[relation.relation]}</h4>
          <p>{relation.explanation}</p>
          <blockquote className="crm-evidence">
            {lead.source_excerpt}
          </blockquote>
          <p className="crm-meta">
            Saved{" "}
            <time dateTime={lead.created_at}>
              {new Date(lead.created_at).toLocaleString()}
            </time>
            . Founder-supplied excerpt; not independently retrieved.
          </p>
          <button
            type="button"
            className="workspace-secondary"
            onClick={() => {
              if (selected !== null) buttons.current[selected]?.focus();
              setSelected(null);
            }}
          >
            Close relationship details
          </button>
        </section>
      )}
    </section>
  );
}
