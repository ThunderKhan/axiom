"use client";

import { useFormStatus } from "react-dom";
import { clearBrowserPrivateState } from "../../lib/private-state";
import { broadcastSignOut, notifyLocalSignOutStarted } from "../../lib/auth-sync";
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
        // Abort same-tab workspace work now; leave the normal server-action
        // redirect alone. Only other tabs should navigate on the broadcast.
        notifyLocalSignOutStarted();
        clearBrowserPrivateState();
        broadcastSignOut();
      }}
    >
      <Button />
    </form>
  );
}
