"use client";

import { useActionState, useEffect, useRef, useState } from "react";
import { useFormStatus } from "react-dom";
import { resetLocalSignOutStarted } from "../../lib/auth-sync";
import { clearBrowserPrivateState } from "../../lib/private-state";
import { signIn, type LoginState } from "./actions";

function SubmitButton({ disabled }: { disabled: boolean }) {
  const { pending } = useFormStatus();
  return (
    <button
      className="auth-submit"
      disabled={disabled || pending}
      type="submit"
    >
      {pending ? "Verifying account…" : "Sign in"}
    </button>
  );
}

export function LoginForm({ configured }: { configured: boolean }) {
  const initial: LoginState = { message: "" };
  const [state, action] = useActionState(signIn, initial);
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const messageRef = useRef<HTMLParagraphElement>(null);
  // Public login is the safe landing for expired, revoked and missing sessions.
  // Remove only app-private keys, even when this tab missed a logout broadcast.
  useEffect(() => {
    // Next.js may navigate here without reloading the module after sign-out.
    // A subsequent login must accept legacy cross-tab logout messages again.
    resetLocalSignOutStarted();
    clearBrowserPrivateState();
  }, []);
  useEffect(() => {
    if (state.message) messageRef.current?.focus();
  }, [state.message]);

  return (
    <form action={action} className="auth-form" noValidate={false}>
      <input type="hidden" name="returnTo" value="/app" />
      <label htmlFor="account-email">Email address</label>
      <input
        autoComplete="username"
        id="account-email"
        name="email"
        type="email"
        inputMode="email"
        required
        maxLength={254}
        disabled={!configured}
        placeholder="you@example.com"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />
      <div className="auth-label-row">
        <label htmlFor="account-password">Password</label>
      </div>
      <div className="password-field">
        <input
          autoComplete="current-password"
          id="account-password"
          name="password"
          type={showPassword ? "text" : "password"}
          required
          disabled={!configured}
        />
        <button
          type="button"
          aria-label={showPassword ? "Hide password" : "Show password"}
          aria-pressed={showPassword}
          disabled={!configured}
          onClick={() => setShowPassword((value) => !value)}
        >
          {showPassword ? "Hide" : "Show"}
        </button>
      </div>
      {state.message && (
        <p className="auth-error" role="alert" tabIndex={-1} ref={messageRef}>
          {state.message}
        </p>
      )}
      <SubmitButton disabled={!configured} />
    </form>
  );
}
