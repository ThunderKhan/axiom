/** Deterministic, stage-aware founder interview. No AI calls or URL inference. */

export type Stage = "idea" | "live";

export type ProfileAnswers = Readonly<{
  stage: Stage | null;
  name: string;
  problem: string;
  audience: string;
  industry: string;
  geography: string;
  alternatives: string;
  capabilities: string;
  missing_capabilities: string;
  differentiators: string;
  pricing_hypothesis: string;
  website_url: string;
  competitors: string;
  desired_signals: string;
  restrictions: string;
}>;

export type TextAnswerKey = Exclude<keyof ProfileAnswers, "stage">;

export const emptyProfileAnswers: ProfileAnswers = {
  stage: null,
  name: "",
  problem: "",
  audience: "",
  industry: "",
  geography: "",
  alternatives: "",
  capabilities: "",
  missing_capabilities: "",
  differentiators: "",
  pricing_hypothesis: "",
  website_url: "",
  competitors: "",
  desired_signals: "",
  restrictions: "",
};

export type Question = Readonly<{
  key: keyof ProfileAnswers;
  label: string;
  why: string;
  optional: boolean;
  maxLength?: number;
  placeholder?: string;
  liveLabel?: string;
  ideaLabel?: string;
}>;

export const profileQuestions: readonly Question[] = [
  {
    key: "stage",
    label: "What are you building?",
    why: "We distinguish proposed capabilities from those already available.",
    optional: false,
  },
  {
    key: "name",
    label: "What is your product or idea called?",
    why: "Names help identify your workspace when returning.",
    optional: false,
    maxLength: 120,
  },
  {
    key: "problem",
    label: "What problem do you want to solve?",
    liveLabel: "What problem do your customers solve with your product?",
    why: "We compare observed customer needs with this problem.",
    optional: false,
    maxLength: 2000,
  },
  {
    key: "audience",
    label: "Who faces this problem?",
    liveLabel: "Who currently uses or buys the product?",
    why: "Customer fit is not the same as keyword overlap.",
    optional: false,
    maxLength: 1000,
  },
  {
    key: "industry",
    label: "Which market or industry?",
    why: "We disclose where our available sources have limited coverage.",
    optional: true,
    maxLength: 300,
  },
  {
    key: "geography",
    label: "Which locations matter?",
    why: "Regional restrictions may affect compatibility.",
    optional: true,
    maxLength: 300,
  },
  {
    key: "alternatives",
    label: "What are people using today instead?",
    why: "Alternatives clarify the competitive context.",
    optional: true,
    maxLength: 1000,
  },
  {
    key: "capabilities",
    label: "What capabilities do you propose?",
    liveLabel: "Which capabilities actually work today?",
    why: "We never promote proposed ideas into verified product claims.",
    optional: false,
    maxLength: 2000,
  },
  {
    key: "missing_capabilities",
    label: "Which capabilities will be missing?",
    liveLabel: "Which capabilities are not supported yet?",
    why: "Missing features can rule out high-intent leads.",
    optional: true,
    maxLength: 1000,
  },
  {
    key: "differentiators",
    label: "What might make this different?",
    liveLabel: "How is it different from existing alternatives?",
    why: "Differentiators are founder declarations until sourced.",
    optional: true,
    maxLength: 1000,
  },
  {
    key: "pricing_hypothesis",
    label: "What pricing do you expect?",
    liveLabel: "What is your current price or pricing model?",
    why: "Unknown is acceptable; hypothetical pricing is not verified.",
    optional: true,
    maxLength: 500,
  },
  {
    key: "website_url",
    label: "Is there a public product website?",
    why: "A link is saved as an unverified declaration, not automatically scraped.",
    optional: true,
    maxLength: 2048,
    placeholder: "https://example.org",
  },
  {
    key: "competitors",
    label: "Which competitors or alternatives do you know?",
    why: "Suggested competitors will require confirmation.",
    optional: true,
    maxLength: 1000,
  },
  {
    key: "desired_signals",
    label: "What customer requests should we investigate?",
    why: "A search goal helps keep discovery relevant.",
    optional: true,
    maxLength: 1000,
  },
  {
    key: "restrictions",
    label: "What constraints or tradeoffs matter?",
    why: "Constraints can change an opportunity decision.",
    optional: true,
    maxLength: 1000,
  },
];

export function canConfirmProfile(answers: ProfileAnswers): boolean {
  return (
    answers.stage !== null &&
    answers.name.trim() !== "" &&
    answers.problem.trim() !== "" &&
    answers.audience.trim() !== "" &&
    answers.capabilities.trim() !== ""
  );
}

export function questionLabel(question: Question, stage: Stage | null): string {
  if (stage === "idea" && question.ideaLabel) return question.ideaLabel;
  if (stage === "live" && question.liveLabel) return question.liveLabel;
  return question.label;
}
