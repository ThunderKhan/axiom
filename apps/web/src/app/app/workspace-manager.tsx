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
  canonicalWorkspaceName,
  isWorkspaceId,
  type Workspace,
} from "../../lib/workspace-contract";
import {
  availablePreferenceStorage,
  chooseRequestedWorkspace,
  makeCreateAttempt,
  mergeOwnedWorkspaces,
  readWorkspacePreference,
  RequestGeneration,
  saveWorkspacePreference,
  uncertainCreationState,
  type CreateAttempt,
  type UncertainCreation,
} from "../../lib/workspace-context";
import {
  createWorkspaceApi,
  isUncertainCreateFailure,
  WorkspaceApiError,
} from "../../lib/workspace-api";
import { clearBrowserPrivateState } from "../../lib/private-state";
import {
  subscribeToLocalSignOutStarted,
  subscribeToSignOut,
} from "../../lib/auth-sync";
import { publicApiBaseUrl } from "../../lib/public-api";
import { createBrowserAuthClient } from "../../lib/supabase/browser";

type ReadyView = {
  kind: "ready";
  items: Workspace[];
  selected: Workspace | null;
  notice: string;
};
type View =
  | ReadyView
  | { kind: "loading"; message: string }
  | {
      kind: "blocked";
      reason: "expired" | "disabled" | "unavailable" | "error";
      message: string;
    };

type CreateState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | UncertainCreation
  | { kind: "error"; message: string };

const emptyForm: CreateState = { kind: "idle" };

function errorText(error: unknown): string {
  if (error instanceof WorkspaceApiError) {
    switch (error.code) {
      case "VALIDATION_FAILED":
        return "The workspace request was rejected. Check the name and try again.";
      case "IDEMPOTENCY_CONFLICT":
        return "That creation attempt conflicts with a different request. Inspect your workspaces.";
      case "VERSION_CONFLICT":
        return "This workspace changed. Reload its details before editing.";
      case "AUTH_UNAVAILABLE":
      case "DATABASE_UNAVAILABLE":
      case "NETWORK_FAILED":
        return "The workspace service is unavailable. Please check the connection.";
    }
  }
  return "Workspace information could not be verified. No private data was restored.";
}

function sessionPreference(): Storage | null {
  return availablePreferenceStorage(() => window.sessionStorage);
}

/** A signed-in Supabase session is not proof of active application/workspace access. */
export function WorkspaceManager({
  subject,
  requestedWorkspace,
}: {
  subject: string;
  requestedWorkspace: string | null;
}) {
  const [view, setView] = useState<View>({
    kind: "loading",
    message: "Verifying application access…",
  });
  const [name, setName] = useState("");
  const [switching, setSwitching] = useState<string | null>(null);
  const [creation, setCreation] = useState<CreateState>(emptyForm);
  const generation = useRef(new RequestGeneration());
  const activeRequest = useRef<AbortController | null>(null);
  const createRequest = useRef<AbortController | null>(null);
  const pendingCreation = useRef<CreateAttempt | null>(null);

  const auth = useMemo(() => createBrowserAuthClient(), []);
  const api = useMemo(
    () =>
      createWorkspaceApi(publicApiBaseUrl, subject, async (expected) => {
        const verified = await auth.auth.getClaims();
        if (
          verified.error ||
          verified.data?.claims?.sub !== expected ||
          verified.data.claims.role !== "authenticated" ||
          verified.data.claims.is_anonymous === true
        ) {
          throw new WorkspaceApiError("AUTH_REQUIRED", 401);
        }
        const session = await auth.auth.getSession();
        if (
          session.error ||
          !session.data.session ||
          session.data.session.user.id !== expected
        ) {
          throw new WorkspaceApiError("AUTH_REQUIRED", 401);
        }
        return session.data.session.access_token;
      }),
    [auth, subject],
  );

  const invalidate = useCallback(() => {
    generation.current.next();
    activeRequest.current?.abort();
    createRequest.current?.abort();
    pendingCreation.current = null;
    clearBrowserPrivateState();
    setName("");
    setSwitching(null);
    setCreation(emptyForm);
    setView({
      kind: "blocked",
      reason: "expired",
      message: "This account session changed. Sign in again to verify access.",
    });
  }, []);

  const reject = useCallback(
    (error: unknown) => {
      if (error instanceof WorkspaceApiError && error.code === "CANCELLED")
        return;
      if (error instanceof WorkspaceApiError && error.status === 401) {
        invalidate();
        window.location.replace("/login?notice=session-expired");
        return;
      }
      if (error instanceof WorkspaceApiError && error.status === 403) {
        pendingCreation.current = null;
        setCreation(emptyForm);
        setView({
          kind: "blocked",
          reason: "disabled",
          message:
            "This application account is disabled. Contact your administrator.",
        });
        return;
      }
      setView({
        kind: "blocked",
        reason:
          error instanceof WorkspaceApiError &&
          (error.status === 503 || error.code === "NETWORK_FAILED")
            ? "unavailable"
            : "error",
        message: errorText(error),
      });
    },
    [invalidate],
  );

  const load = useCallback(
    async (requested: string | null = null) => {
      const pending = pendingCreation.current;
      if (pending) {
        // Revalidation can interrupt an already-committed POST. Keep the
        // original guard until the owner verifies the actual workspace list.
        createRequest.current?.abort();
        createRequest.current = null;
        const uncertain = uncertainCreationState(pending, subject, false);
        if (uncertain) setCreation(uncertain);
        else {
          pendingCreation.current = null;
          setCreation(emptyForm);
        }
      }
      const seq = generation.current.next();
      activeRequest.current?.abort();
      const controller = new AbortController();
      activeRequest.current = controller;
      setSwitching(null);
      setView({ kind: "loading", message: "Checking application account…" });
      try {
        await api.bootstrap(controller.signal);
        if (!generation.current.current(seq)) return;
        setView({ kind: "loading", message: "Loading authorized workspaces…" });
        const items = await api.list(controller.signal);
        if (!generation.current.current(seq)) return;
        const saved = readWorkspacePreference(sessionPreference(), subject);
        const candidate = chooseRequestedWorkspace(requested, saved);
        let selected: Workspace | null = null;
        let notice = "";
        if (candidate) {
          try {
            selected = await api.read(candidate, controller.signal);
          } catch (error) {
            if (error instanceof WorkspaceApiError && error.status === 404) {
              // Foreign and missing workspace IDs are intentionally identical.
              saveWorkspacePreference(sessionPreference(), subject, null);
              notice =
                "Your previous workspace is unavailable. Choose an authorized workspace.";
            } else {
              throw error;
            }
          }
        } else if (items.length === 1) {
          selected = items[0]; // Fresh owner-filtered FastAPI list.
        } else if (requested !== null) {
          notice =
            "The requested workspace is invalid. Choose a workspace below.";
        }
        if (!generation.current.current(seq)) return;
        const inspected = uncertainCreationState(
          pendingCreation.current,
          subject,
          true,
        );
        if (inspected) setCreation(inspected);
        const nextItems = selected
          ? mergeOwnedWorkspaces(items, selected)
          : items;
        saveWorkspacePreference(
          sessionPreference(),
          subject,
          selected?.id ?? null,
        );
        window.history.replaceState(
          null,
          "",
          selected
            ? "/app?workspace=" + encodeURIComponent(selected.id)
            : "/app",
        );
        setView({ kind: "ready", items: nextItems, selected, notice });
      } catch (error) {
        if (generation.current.current(seq)) reject(error);
      }
    },
    [api, reject, subject],
  );

  useEffect(() => {
    // Defer the first state transition until after the effect has subscribed.
    // Synchronous setState inside an effect is not allowed by the React lint gate.
    let disposed = false;
    const currentGeneration = generation.current;
    queueMicrotask(() => {
      if (!disposed) void load(requestedWorkspace);
    });
    const unsubscribe = subscribeToSignOut(invalidate);
    const unsubscribeLocal = subscribeToLocalSignOutStarted(invalidate);
    const { data: listener } = auth.auth.onAuthStateChange((event, session) => {
      if (
        event === "SIGNED_OUT" ||
        (event === "INITIAL_SESSION" && !session) ||
        (session?.user.id && session.user.id !== subject)
      ) {
        invalidate();
      }
    });
    return () => {
      disposed = true;
      currentGeneration.next();
      activeRequest.current?.abort();
      createRequest.current?.abort();
      // Do not discard a pending attempt on a same-user URL/query change.
      unsubscribe();
      unsubscribeLocal();
      listener.subscription.unsubscribe();
    };
  }, [auth, invalidate, load, requestedWorkspace, subject]);

  const select = async (id: string) => {
    if (
      view.kind !== "ready" ||
      creation.kind === "submitting" ||
      !isWorkspaceId(id)
    )
      return;
    const items = view.items;
    const seq = generation.current.next();
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    // Keep the owner-filtered switcher usable while denying access to the old
    // active context. B may supersede an unresolved A request.
    setSwitching(id);
    setView({ ...view, selected: null, notice: "Verifying workspace access…" });
    try {
      const selected = await api.read(id, controller.signal);
      if (!generation.current.current(seq)) return;
      setSwitching(null);
      saveWorkspacePreference(sessionPreference(), subject, selected.id);
      window.history.replaceState(
        null,
        "",
        "/app?workspace=" + encodeURIComponent(selected.id),
      );
      setView({
        kind: "ready",
        items: mergeOwnedWorkspaces(items, selected),
        selected,
        notice: "Workspace switched.",
      });
    } catch (error) {
      if (!generation.current.current(seq)) return;
      setSwitching(null);
      if (error instanceof WorkspaceApiError && error.status === 404) {
        saveWorkspacePreference(sessionPreference(), subject, null);
        window.history.replaceState(null, "", "/app");
        await load();
      } else {
        reject(error);
      }
    }
  };

  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (
      view.kind !== "ready" ||
      creation.kind === "submitting" ||
      creation.kind === "uncertain" ||
      switching !== null ||
      pendingCreation.current
    )
      return;
    let attempt: CreateAttempt;
    try {
      attempt = makeCreateAttempt(
        subject,
        canonicalWorkspaceName(name),
        Date.now(),
        () => crypto.randomUUID(),
      );
    } catch (error) {
      setCreation({
        kind: "error",
        message:
          error instanceof Error ? error.message : "Invalid workspace name.",
      });
      return;
    }
    pendingCreation.current = attempt; // Synchronous double-submit guard.
    const seq = generation.current.next();
    activeRequest.current?.abort();
    const controller = new AbortController();
    createRequest.current = controller;
    setCreation({ kind: "submitting" });
    try {
      const created = await api.create(
        attempt.name,
        attempt.key,
        controller.signal,
      );
      if (!generation.current.current(seq)) return;
      pendingCreation.current = null;
      saveWorkspacePreference(sessionPreference(), subject, created.id);
      window.history.replaceState(
        null,
        "",
        "/app?workspace=" + encodeURIComponent(created.id),
      );
      setView({
        kind: "ready",
        items: mergeOwnedWorkspaces(view.items, created),
        selected: created,
        notice: "Workspace created and verified through the workspace API.",
      });
      setName("");
      setCreation(emptyForm);
    } catch (error) {
      if (!generation.current.current(seq)) return;
      if (isUncertainCreateFailure(error)) {
        // The request may have committed despite a lost response. No automatic
        // retry is safe without a deployment-verified network delivery bound.
        setCreation({
          kind: "uncertain",
          name: attempt.name,
          inspected: false,
        });
      } else {
        pendingCreation.current = null;
        if (
          error instanceof WorkspaceApiError &&
          (error.status === 401 || error.status === 403)
        ) {
          reject(error);
        } else {
          setCreation({ kind: "error", message: errorText(error) });
        }
      }
    } finally {
      if (generation.current.current(seq)) createRequest.current = null;
    }
  };

  const busy = creation.kind === "submitting";

  return (
    <section className="workspace-section" aria-labelledby="workspace-heading">
      <div className="workspace-intro">
        <p className="eyebrow">YOUR PRODUCT WORKSPACES</p>
        <h1 id="workspace-heading">Work from the right context.</h1>
        <p className="introduction">
          Workspaces belong to your verified account. Every selection is
          authorized by FastAPI. Research, onboarding and CRM are not available
          in this milestone.
        </p>
      </div>

      {view.kind === "loading" && (
        <div className="workspace-card" aria-live="polite" aria-busy="true">
          <p role="status">{view.message}</p>
        </div>
      )}
      {view.kind === "blocked" && (
        <div className="workspace-card" role="alert">
          <h2>
            {view.reason === "disabled"
              ? "Account access unavailable"
              : "Workspace access unavailable"}
          </h2>
          <p>{view.message}</p>
          {view.reason !== "disabled" && view.reason !== "expired" && (
            <button
              type="button"
              className="workspace-secondary"
              onClick={() => void load()}
            >
              Try again
            </button>
          )}
          {view.reason === "expired" && <a href="/login">Return to sign in</a>}
        </div>
      )}
      {view.kind === "ready" && (
        <div className="workspace-grid">
          <div className="workspace-card">
            <div className="workspace-card-heading">
              <h2>
                {view.items.length === 0
                  ? "Create your first workspace"
                  : "Choose a workspace"}
              </h2>
              <span className="workspace-count">{view.items.length} owned</span>
            </div>
            {view.notice && (
              <p className="workspace-notice" role="status">
                {view.notice}
              </p>
            )}
            {view.items.length === 0 ? (
              <p>
                No workspaces yet. Give your first product or idea a name to
                begin.
              </p>
            ) : (
              <ul
                className="workspace-list"
                aria-label="Your authorized workspaces"
              >
                {view.items.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={
                        "workspace-choice" +
                        (view.selected?.id === item.id
                          ? " workspace-choice--active"
                          : "")
                      }
                      aria-pressed={view.selected?.id === item.id}
                      disabled={busy}
                      onClick={() => void select(item.id)}
                    >
                      <span>{item.name}</span>
                      <span>
                        {switching === item.id
                          ? "Checking…"
                          : view.selected?.id === item.id
                            ? "Active"
                            : "Select"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="workspace-active" aria-live="polite">
              <h3>Active workspace</h3>
              {switching && <p role="status">Authorizing your selection…</p>}
              {view.selected ? (
                <>
                  <strong>{view.selected.name}</strong>
                  <p>Verified owner access · Workspace ID {view.selected.id}</p>
                  <p className="workspace-limit">
                    Workspace context is ready. Product onboarding and
                    opportunities follow in later milestones.
                  </p>
                </>
              ) : (
                <p>
                  Nothing selected. Choose a workspace to establish an
                  authorized context.
                </p>
              )}
            </div>
            <button
              className="workspace-secondary"
              type="button"
              disabled={busy}
              onClick={() => void load()}
            >
              Refresh authorized list
            </button>
          </div>

          <div className="workspace-card">
            <h2>
              {view.items.length === 0
                ? "New workspace"
                : "Add another workspace"}
            </h2>
            <p>Each workspace is independent and private to your account.</p>
            <form
              className="workspace-form"
              onSubmit={(event) => void create(event)}
            >
              <label htmlFor="workspace-name">Product or idea name</label>
              <input
                id="workspace-name"
                name="workspace-name"
                autoComplete="off"
                maxLength={240}
                required
                value={name}
                disabled={
                  busy || switching !== null || creation.kind === "uncertain"
                }
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Research notes"
              />
              {creation.kind === "error" && (
                <p className="workspace-error" role="alert">
                  {creation.message}
                </p>
              )}
              {creation.kind === "submitting" && (
                <p role="status" aria-live="polite">
                  Creating your workspace…
                </p>
              )}
              {creation.kind === "uncertain" && (
                <div className="workspace-warning" role="alert">
                  <h3>Creation outcome is uncertain</h3>
                  <p>
                    The request for “{creation.name}” may have succeeded. Do not
                    submit a new request until you inspect your workspaces.
                  </p>
                  <button
                    type="button"
                    className="workspace-secondary"
                    onClick={() => void load()}
                  >
                    Inspect owned workspaces
                  </button>
                  {creation.inspected && (
                    <button
                      type="button"
                      className="workspace-secondary"
                      onClick={() => {
                        pendingCreation.current = null;
                        setCreation(emptyForm);
                      }}
                    >
                      I have inspected; allow a separate new attempt
                    </button>
                  )}
                </div>
              )}
              <button
                className="workspace-primary"
                type="submit"
                disabled={
                  busy || switching !== null || creation.kind === "uncertain"
                }
              >
                {busy ? "Creating…" : "Create workspace"}
              </button>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
