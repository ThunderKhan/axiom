export type CapabilityState = "available" | "unavailable";

export interface Capability {
  readonly id: "foundation" | "authentication" | "research";
  readonly title: string;
  readonly description: string;
  readonly state: CapabilityState;
}

/** Current, factual capability states. Do not mark unimplemented features as available. */
export const capabilities: readonly Capability[] = [
  {
    id: "foundation",
    title: "Web foundation",
    description: "The application shell is running.",
    state: "available",
  },
  {
    id: "authentication",
    title: "Authentication",
    description: "Sign-in and account access are not yet implemented.",
    state: "unavailable",
  },
  {
    id: "research",
    title: "Research and workspace features",
    description: "Live intelligence, workspaces, and CRM are not yet implemented.",
    state: "unavailable",
  },
];

export function statusLabel(state: CapabilityState): string {
  return state === "available" ? "Available" : "Not yet available";
}
