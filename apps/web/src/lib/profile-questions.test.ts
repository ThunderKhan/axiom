import assert from "node:assert/strict";
import test from "node:test";
import {
  canConfirmProfile,
  emptyProfileAnswers,
  profileQuestions,
  questionLabel,
} from "./profile-questions.ts";
import { InvalidProfileResponse, parseProfileState } from "./profile-api.ts";

test("deterministic onboarding covers 15 stage-aware steps", () => {
  assert.equal(profileQuestions.length, 15);
  assert.equal(new Set(profileQuestions.map((q) => q.key)).size, 15);
  const question = profileQuestions.find((q) => q.key === "capabilities");
  assert.ok(question);
  assert.match(questionLabel(question, "idea"), /propose/);
  assert.match(questionLabel(question, "live"), /actually work/);
});

test("only full minimum founder context can be confirmed", () => {
  assert.equal(canConfirmProfile(emptyProfileAnswers), false);
  assert.equal(
    canConfirmProfile({
      ...emptyProfileAnswers,
      stage: "idea",
      name: "Study tool",
      problem: "Lack of offline notes",
      audience: "Students",
      capabilities: "Planned offline access",
    }),
    true,
  );
});

test("profile transport refuses malformed or contradictory responses", () => {
  const valid = {
    draft_revision: 1,
    answers: { ...emptyProfileAnswers, stage: "idea" },
    confirmed_revision: 0,
    confirmed: null,
  };
  assert.equal(parseProfileState(valid).draft_revision, 1);
  assert.throws(
    () => parseProfileState({ ...valid, confirmed_revision: 1 }),
    InvalidProfileResponse,
  );
  assert.throws(
    () =>
      parseProfileState({
        ...valid,
        answers: { ...valid.answers, stage: "fake" },
      }),
    InvalidProfileResponse,
  );
  assert.throws(
    () =>
      parseProfileState({
        ...valid,
        answers: { ...valid.answers, user_id: "foreign" },
      }),
    InvalidProfileResponse,
  );
});
