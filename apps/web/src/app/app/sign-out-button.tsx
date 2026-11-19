"use client";

import { useFormStatus } from "react-dom";
import { clearPrivateState } from "../../lib/private-state";
import { signOut } from "../login/actions";

function Button() {
  const { pending } = useFormStatus();
  return (
    <button className="auth-signout" disabled={pending} type="submit">
      {pending ? "Signing out…" : "Sign out"}
    </button>
  );
}

export function SignOutButton() {
  return (
    <form
      action={signOut}
      onSubmit={() => {
        clearPrivateState(window.localStorage);
        clearPrivateState(window.sessionStorage);
      }}
    >
      <Button />
    </form>
  );
}
