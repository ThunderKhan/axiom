import Link from "next/link";
import { redirect } from "next/navigation";
import { publicAuthConfig } from "../../lib/auth-config";
import { loginDestination } from "../../lib/redirects";
import { createServerAuthClient } from "../../lib/supabase/server";
import { AuthObserver } from "./auth-observer";
import { SignOutButton } from "./sign-out-button";

export const dynamic = "force-dynamic";

export default async function AuthenticatedFoundationPage() {
  if (!publicAuthConfig()) redirect(loginDestination("auth-unavailable"));

  let verifiedSubject: string | null = null;
  let unavailable = false;
  try {
    const client = await createServerAuthClient();
    const result = await client.auth.getClaims();
    const claims = result.data?.claims;
    if (
      !result.error &&
      claims &&
      typeof claims.sub === "string" &&
      claims.role === "authenticated" &&
      claims.is_anonymous !== true
    ) {
      verifiedSubject = claims.sub;
    } else if (result.error?.status && result.error.status >= 500) {
      unavailable = true;
    }
  } catch {
    unavailable = true;
  }
  if (!verifiedSubject) {
    redirect(loginDestination(unavailable ? "auth-unavailable" : "session-expired"));
  }

  return (
    <>
      <a href="#app-main" className="skip-link">Skip to application</a>
      <div className="page-shell">
        <header className="site-header">
          <Link className="wordmark wordmark-link" href="/">AXIOM</Link>
          <SignOutButton />
        </header>
        <main id="app-main" className="private-main" tabIndex={-1}>
          <div className="eyebrow">VERIFIED SUPABASE SESSION</div>
          <h1>Your Axiom session is active.</h1>
          <p className="introduction">
            Your identity was verified by Supabase Auth. This is the Milestone 1
            protected application foundation, not an authorized product workspace.
          </p>
          <section className="status-panel private-status" aria-labelledby="private-heading">
            <div className="status-heading">
              <h2 id="private-heading">What is available?</h2>
              <p>Session verification is separate from application and workspace authorization.</p>
            </div>
            <ul className="capabilities">
              <li className="capability">
                <div>
                  <h3>Session</h3>
                  <p>Signed in using a verified provider identity.</p>
                </div>
                <span className="status status--available">Verified</span>
              </li>
              <li className="capability">
                <div>
                  <h3>Workspace access</h3>
                  <p>
                    Account bootstrap, workspace authorization and product screens depend on
                    later FastAPI and frontend implementation issues.
                  </p>
                </div>
                <span className="status status--unavailable">Not yet available</span>
              </li>
            </ul>
          </section>
        </main>
        <footer className="site-footer">Axiom · Private session · No fabricated workspace data</footer>
      </div>
      <AuthObserver verifiedSubject={verifiedSubject} />
    </>
  );
}
