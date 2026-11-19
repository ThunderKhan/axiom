"use client";

import { useEffect } from "react";
import { clearPrivateState } from "../../lib/private-state";
import { createBrowserAuthClient } from "../../lib/supabase/browser";

/** Guard against stale private client state after logout, tab signout or account swap. */
export function AuthObserver({ verifiedSubject }: { verifiedSubject: string }) {
  useEffect(() => {
    const client = createBrowserAuthClient();
    const reset = () => {
      clearPrivateState(window.localStorage);
      clearPrivateState(window.sessionStorage);
    };
    const { data: listener } = client.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT") {
        reset();
        window.location.replace("/login?notice=session-expired");
      } else if (
        (event === "SIGNED_IN" || event === "TOKEN_REFRESHED" || event === "INITIAL_SESSION") &&
        session?.user.id &&
        session.user.id !== verifiedSubject
      ) {
        reset();
        // A different principal must be freshly authorized by the server.
        window.location.replace("/app");
      }
    });
    const onPageShow = (event: PageTransitionEvent) => {
      if (event.persisted) window.location.reload();
    };
    window.addEventListener("pageshow", onPageShow);
    return () => {
      listener.subscription.unsubscribe();
      window.removeEventListener("pageshow", onPageShow);
    };
  }, [verifiedSubject]);

  return null;
}
