"use client";

import { useEffect } from "react";
import { subscribeToSignOut } from "../../lib/auth-sync";
import { clearBrowserPrivateState } from "../../lib/private-state";
import { createBrowserAuthClient } from "../../lib/supabase/browser";

/** Prevent stale private UI after account changes, logout or missed tab events. */
export function AuthObserver({ verifiedSubject }: { verifiedSubject: string }) {
  useEffect(() => {
    const client = createBrowserAuthClient();
    const goToLogin = () => {
      clearBrowserPrivateState();
      window.location.replace("/login?notice=session-expired");
    };
    const unsubscribe = subscribeToSignOut(goToLogin);
    const { data: listener } = client.auth.onAuthStateChange(
      (event, session) => {
        if (
          event === "SIGNED_OUT" ||
          (event === "INITIAL_SESSION" && !session)
        ) {
          goToLogin();
        } else if (
          (event === "SIGNED_IN" ||
            event === "TOKEN_REFRESHED" ||
            event === "INITIAL_SESSION") &&
          session?.user.id &&
          session.user.id !== verifiedSubject
        ) {
          clearBrowserPrivateState();
          // A different principal needs a fresh server-side protected-route check.
          window.location.replace("/app");
        }
      },
    );
    const onPageShow = (event: PageTransitionEvent) => {
      if (event.persisted) window.location.reload();
    };
    const onVisibilityChange = () => {
      // Revalidate from the server if this tab missed cross-tab signout.
      if (document.visibilityState === "visible") window.location.reload();
    };
    window.addEventListener("pageshow", onPageShow);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      listener.subscription.unsubscribe();
      unsubscribe();
      window.removeEventListener("pageshow", onPageShow);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [verifiedSubject]);

  return null;
}
