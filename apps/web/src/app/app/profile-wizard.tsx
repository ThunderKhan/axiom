"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  canConfirmProfile,
  emptyProfileAnswers,
  profileQuestions,
  questionLabel,
  type ProfileAnswers,
  type Stage,
  type TextAnswerKey,
} from "../../lib/profile-questions";
import {
  createProfileApi,
  ProfileApiError,
  type ProfileState,
} from "../../lib/profile-api";
import { publicApiBaseUrl } from "../../lib/public-api";
import { createBrowserAuthClient } from "../../lib/supabase/browser";
import {
  subscribeToLocalSignOutStarted,
  subscribeToSignOut,
} from "../../lib/auth-sync";

type View = "loading" | "ready" | "blocked";
type Mode = "interview" | "review" | "saved";

function statusMessage(error: unknown): string {
  if (error instanceof ProfileApiError) {
    if (error.code === "VERSION_CONFLICT")
      return "This profile was changed in another request. Refresh the profile before continuing.";
    if (error.code === "PROFILE_INCOMPLETE")
      return "Confirm a product stage, name, problem, audience and capabilities.";
    if (error.status === 401 || error.status === 403)
      return "Your access changed. Please sign in again.";
    if (error.code === "NETWORK_UNCERTAIN")
      return "The server may have saved your changes. Refresh and inspect before trying again.";
  }
  return "The profile service could not be verified. No success was assumed.";
}

export function ProfileWizard({
  subject,
  workspaceId,
}: {
  subject: string;
  workspaceId: string;
}) {
  const auth = useMemo(() => createBrowserAuthClient(), []);
  const api = useMemo(
    () =>
      createProfileApi(publicApiBaseUrl, subject, async (expected) => {
        const claims = await auth.auth.getClaims();
        if (
          claims.error ||
          claims.data?.claims?.sub !== expected ||
          claims.data.claims.role !== "authenticated" ||
          claims.data.claims.is_anonymous === true
        ) {
          throw new ProfileApiError("AUTH_REQUIRED", 401);
        }
        const session = await auth.auth.getSession();
        if (
          session.error ||
          !session.data.session ||
          session.data.session.user.id !== expected
        ) {
          throw new ProfileApiError("AUTH_REQUIRED", 401);
        }
        return session.data.session.access_token;
      }),
    [auth, subject],
  );
  const [view, setView] = useState<View>("loading");
  const [mode, setMode] = useState<Mode>("interview");
  const [state, setState] = useState<ProfileState | null>(null);
  const [answers, setAnswers] = useState<ProfileAnswers>(emptyProfileAnswers);
  const [step, setStep] = useState(0);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const active = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const writing = useRef(false);

  const blocked = useCallback(() => {
    sequence.current += 1;
    active.current?.abort();
    writing.current = false;
    setView("blocked");
    setState(null);
    setAnswers(emptyProfileAnswers);
    setMessage("Your account or workspace session changed.");
  }, []);

  const load = useCallback(async () => {
    const generation = ++sequence.current;
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setView("loading");
    setMessage("");
    try {
      const next = await api.read(workspaceId, controller.signal);
      if (sequence.current !== generation) return;
      setState(next);
      setAnswers(
        next.answers ?? next.confirmed?.answers ?? emptyProfileAnswers,
      );
      setMode(next.confirmed ? "saved" : "interview");
      setStep(0);
      setView("ready");
    } catch (error) {
      if (sequence.current !== generation) return;
      setView("blocked");
      setMessage(statusMessage(error));
    }
  }, [api, workspaceId]);

  useEffect(() => {
    let disposed = false;
    const currentSequence = sequence;
    // Keep React's effect free of synchronous state transitions.
    queueMicrotask(() => {
      if (!disposed) void load();
    });
    const unsubscribe = subscribeToSignOut(blocked);
    const unsubscribeLocal = subscribeToLocalSignOutStarted(blocked);
    const { data: listener } = auth.auth.onAuthStateChange((event, session) => {
      if (
        event === "SIGNED_OUT" ||
        (event === "INITIAL_SESSION" && !session) ||
        (session?.user.id && session.user.id !== subject)
      ) {
        blocked();
      }
    });
    return () => {
      disposed = true;
      currentSequence.current += 1;
      active.current?.abort();
      unsubscribe();
      unsubscribeLocal();
      listener.subscription.unsubscribe();
    };
  }, [auth, blocked, load, subject]);

  const save = async (exit: boolean) => {
    if (!state || writing.current) return;
    writing.current = true;
    setBusy(true);
    const generation = sequence.current;
    const controller = new AbortController();
    active.current = controller;
    try {
      const next = await api.save(
        workspaceId,
        answers,
        state.draft_revision,
        controller.signal,
      );
      if (generation !== sequence.current) return;
      setState(next);
      setMessage("Draft saved in your authorized workspace.");
      if (exit) setMode("saved");
    } catch (error) {
      if (generation === sequence.current) setMessage(statusMessage(error));
    } finally {
      writing.current = false;
      if (generation === sequence.current) setBusy(false);
    }
  };

  const confirm = async () => {
    if (!state || writing.current) return;
    if (!canConfirmProfile(answers)) {
      setMessage(
        "Confirm the product stage, name, problem, audience and capabilities.",
      );
      return;
    }
    writing.current = true;
    setBusy(true);
    const generation = sequence.current;
    const controller = new AbortController();
    active.current = controller;
    try {
      // Persist the review first; confirmations only use server-stored answers.
      const draft = await api.save(
        workspaceId,
        answers,
        state.draft_revision,
        controller.signal,
      );
      if (generation !== sequence.current) return;
      setState(draft);
      const next = await api.confirm(
        workspaceId,
        draft.draft_revision,
        controller.signal,
      );
      if (generation !== sequence.current) return;
      setState(next);
      setMode("saved");
      setMessage(
        "Founder-confirmed profile version " +
          next.confirmed_revision +
          " saved.",
      );
    } catch (error) {
      if (generation === sequence.current) setMessage(statusMessage(error));
    } finally {
      writing.current = false;
      if (generation === sequence.current) setBusy(false);
    }
  };

  const question = profileQuestions[step];
  const currentStage = answers.stage as Stage | null;

  return (
    <section className="profile-wizard" aria-labelledby="profile-heading">
      <div className="profile-wizard-heading">
        <div>
          <p className="eyebrow">PRODUCT CONTEXT</p>
          <h3 id="profile-heading">Your product profile</h3>
        </div>
        {state?.confirmed && (
          <span className="workspace-count">
            Version {state.confirmed_revision} confirmed
          </span>
        )}
      </div>
      {view === "loading" && <p role="status">Loading private profile…</p>}
      {view === "blocked" && (
        <div role="alert">
          <p>{message}</p>
          <button
            className="workspace-secondary"
            type="button"
            onClick={() => void load()}
          >
            Check access again
          </button>
        </div>
      )}
      {view === "ready" && state && (
        <>
          {mode === "saved" ? (
            <div className="profile-saved">
              <p>
                {state.confirmed
                  ? "Confirmed founder declaration: " +
                    state.confirmed.answers.name
                  : "Your onboarding draft is saved. It has not been confirmed."}
              </p>
              <p>
                {state.confirmed
                  ? "Capabilities and website details are user-declared, not independently verified."
                  : "Continue the interview to confirm a usable product profile."}
              </p>
              <button
                className="workspace-primary"
                type="button"
                onClick={() => {
                  setMode("interview");
                  setMessage("");
                }}
              >
                {state.confirmed
                  ? "Review or edit profile"
                  : "Resume questions"}
              </button>
            </div>
          ) : mode === "interview" ? (
            <div className="profile-step">
              <p className="profile-progress">
                Question {step + 1} of {profileQuestions.length}
                {question.optional
                  ? " · Optional"
                  : " · Required for confirmation"}
              </p>
              {question.key === "stage" ? (
                <h4>{questionLabel(question, currentStage)}</h4>
              ) : (
                <label htmlFor="profile-answer">
                  {questionLabel(question, currentStage)}
                </label>
              )}
              <p className="profile-hint">{question.why}</p>
              {question.key === "stage" ? (
                <fieldset className="profile-stage-options">
                  <legend>Choose your stage</legend>
                  <label>
                    <input
                      type="radio"
                      name="product-stage"
                      checked={answers.stage === "idea"}
                      onChange={() =>
                        setAnswers((value) => ({ ...value, stage: "idea" }))
                      }
                    />
                    Idea-stage — proposed capabilities
                  </label>
                  <label>
                    <input
                      type="radio"
                      name="product-stage"
                      checked={answers.stage === "live"}
                      onChange={() =>
                        setAnswers((value) => ({ ...value, stage: "live" }))
                      }
                    />
                    Live product — existing capabilities
                  </label>
                </fieldset>
              ) : (
                <textarea
                  id="profile-answer"
                  rows={
                    question.key === "problem" ||
                    question.key === "capabilities"
                      ? 4
                      : 2
                  }
                  maxLength={question.maxLength}
                  placeholder={
                    question.placeholder ??
                    "Your answer, or leave blank if unknown"
                  }
                  value={answers[question.key] ?? ""}
                  onChange={(event) => {
                    const key = question.key as TextAnswerKey;
                    setAnswers((value) => ({
                      ...value,
                      [key]: event.target.value,
                    }));
                  }}
                />
              )}
              <div className="profile-actions">
                <button
                  className="workspace-secondary"
                  type="button"
                  disabled={step === 0 || busy}
                  onClick={() => setStep((value) => value - 1)}
                >
                  Back
                </button>
                {question.optional && (
                  <button
                    className="workspace-secondary"
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      setStep((value) =>
                        Math.min(value + 1, profileQuestions.length - 1),
                      )
                    }
                  >
                    Skip
                  </button>
                )}
                <button
                  className="workspace-primary"
                  type="button"
                  disabled={
                    busy || (question.key === "stage" && answers.stage === null)
                  }
                  onClick={() => {
                    if (step === profileQuestions.length - 1) setMode("review");
                    else setStep((value) => value + 1);
                  }}
                >
                  {step === profileQuestions.length - 1
                    ? "Review answers"
                    : "Next"}
                </button>
              </div>
              <button
                className="workspace-secondary"
                type="button"
                disabled={busy}
                onClick={() => void save(true)}
              >
                Save and resume later
              </button>
            </div>
          ) : (
            <div className="profile-review">
              <h4>Confirm your founder declarations</h4>
              <p>
                Nothing here is automatically verified by a website or AI model.
              </p>
              <dl>
                {profileQuestions.map((item) => (
                  <div key={item.key}>
                    <dt>{questionLabel(item, currentStage)}</dt>
                    <dd>{answers[item.key] ?? "Unknown"}</dd>
                  </div>
                ))}
              </dl>
              <div className="profile-actions">
                <button
                  className="workspace-secondary"
                  type="button"
                  disabled={busy}
                  onClick={() => setMode("interview")}
                >
                  Edit answers
                </button>
                <button
                  className="workspace-primary"
                  type="button"
                  disabled={busy || !canConfirmProfile(answers)}
                  onClick={() => void confirm()}
                >
                  {busy ? "Confirming…" : "Confirm and version profile"}
                </button>
              </div>
            </div>
          )}
          {message && (
            <p className="workspace-notice" role="status">
              {message}
            </p>
          )}
        </>
      )}
    </section>
  );
}
