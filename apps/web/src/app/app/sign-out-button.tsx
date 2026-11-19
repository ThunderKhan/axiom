"use client";

import { useFormStatus } from "react-dom";
import { clearBrowserPrivateState } from "../../lib/private-state";
import { broadcastSignOut } from "../../lib/auth-sync";
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
        clearBrowserPrivateState();
        broadcastSignOut();
      }}
    >
      <Button />
    </form>
  );
}
