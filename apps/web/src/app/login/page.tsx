import Link from "next/link";
import { publicAuthConfig } from "../../lib/auth-config";
import { LoginForm } from "./login-form";

export const dynamic = "force-dynamic";

type LoginPageProps = {
  searchParams: Promise<{ notice?: string | string[]; returnTo?: string | string[] }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  const configured = Boolean(publicAuthConfig());
  const notices: Record<string, string> = {
    "session-required": "Please sign in to open your private workspace.",
    "session-expired": "Your session is no longer valid. Please sign in again.",
    "auth-unavailable": "Session verification is temporarily unavailable.",
    "signed-out": "You have signed out of this browser.",
    "signed-out-local":
      "This browser is signed out. Remote session revocation could not be confirmed.",
  };
  const notice = typeof params.notice === "string" ? notices[params.notice] : undefined;
  // Do not mirror untrusted returnTo input into the page, form or redirect.
  void params.returnTo;

  return (
    <>
      <a className="skip-link" href="#login-main">
        Skip to sign in
      </a>
      <div className="page-shell">
        <header className="site-header">
          <Link className="wordmark wordmark-link" href="/">
            AXIOM
          </Link>
          <span className="version-label">Secure account access</span>
        </header>
        <main id="login-main" className="auth-main" tabIndex={-1}>
          <div className="auth-card">
            <div className="eyebrow">PRIVATE WORKSPACE</div>
            <h1>Welcome back.</h1>
            <p className="introduction">
              Sign in using your provisioned Supabase account. No guest or evaluator bypass.
            </p>
            {notice && <p className="auth-notice" role="status">{notice}</p>}
            {!configured && (
              <p className="auth-error" role="alert">
                Sign-in is not configured in this environment. Ask the operator to configure
                the public Supabase URL and publishable key.
              </p>
            )}
            <LoginForm configured={configured} />
            <p className="auth-help">
              Account creation and password recovery are not available in this release.
              Contact your account administrator if you need access.
            </p>
          </div>
        </main>
        <footer className="site-footer">Axiom · Supabase identity · No guest mode</footer>
      </div>
    </>
  );
}
