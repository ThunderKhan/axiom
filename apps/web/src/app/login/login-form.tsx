"use client";

import { useActionState, useEffect, useRef, useState } from "react";
import { useFormStatus } from "react-dom";
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
  const messageRef = useRef<HTMLParagraphElement>(null);
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
