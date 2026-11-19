export type CapabilityState = "available" | "unavailable";

export interface Capability {
  readonly id: "foundation" | "authentication" | "research";
  readonly title: string;
  readonly description: string;
  readonly state: CapabilityState;
}

/** Status is deployment/provider evidence, not a count of source files committed. */
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
    description:
      "Login and server-verified session code is implemented. Live provider operation requires configuration and separate verification.",
    state: "unavailable",
  },
  {
    id: "research",
    title: "Research and workspace features",
    description:
      "Workspace HTTP APIs, onboarding, live research, and CRM are not yet implemented.",
    state: "unavailable",
  },
];

export function statusLabel(state: CapabilityState): string {
  return state === "available" ? "Available" : "Not yet available";
}
