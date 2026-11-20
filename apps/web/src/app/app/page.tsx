import Link from "next/link";
import { redirect } from "next/navigation";
import { publicAuthConfig } from "../../lib/auth-config";
import { loginDestination } from "../../lib/redirects";
import { createServerAuthClient } from "../../lib/supabase/server";
import { AuthObserver } from "./auth-observer";
import { SignOutButton } from "./sign-out-button";
import { WorkspaceManager } from "./workspace-manager";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{ workspace?: string | string[] }>;
};

export default async function AuthenticatedWorkspacePage({
  searchParams,
}: PageProps) {
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
    redirect(
      loginDestination(unavailable ? "auth-unavailable" : "session-expired"),
    );
  }

  const params = await searchParams;
  const requestedWorkspace =
    typeof params.workspace === "string" ? params.workspace : null;

  return (
    <>
      <a href="#app-main" className="skip-link">
        Skip to application
      </a>
      <div className="page-shell">
        <header className="site-header">
          <Link className="wordmark wordmark-link" href="/">
            AXIOM
          </Link>
          <SignOutButton />
        </header>
        <main id="app-main" className="private-main" tabIndex={-1}>
          <WorkspaceManager
            subject={verifiedSubject}
            requestedWorkspace={requestedWorkspace}
          />
        </main>
        <footer className="site-footer">
          Axiom · Authenticated workspace foundation · Provider verification
          pending
        </footer>
      </div>
      <AuthObserver verifiedSubject={verifiedSubject} />
    </>
  );
}
