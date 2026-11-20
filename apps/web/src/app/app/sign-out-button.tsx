"use client";

import { useFormStatus } from "react-dom";
import { clearBrowserPrivateState } from "../../lib/private-state";
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
        // Do not broadcast before the server action completes: the initiating
        // tab subscribes too and would navigate to session-expired prematurely.
        clearBrowserPrivateState();
      }}
    >
      <Button />
    </form>
  );
}
