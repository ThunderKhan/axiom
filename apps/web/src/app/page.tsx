import Link from "next/link";
import { capabilities, statusLabel } from "../lib/foundation";

export default function HomePage() {
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <div className="page-shell">
        <header className="site-header">
          <span className="wordmark">AXIOM</span>
          <Link className="header-login" href="/login">
            Sign in
          </Link>
        </header>
        <main id="main-content" tabIndex={-1}>
          <div className="eyebrow">BUILDING WITH EVIDENCE</div>
          <h1>Axiom is taking shape.</h1>
          <p className="introduction">
            An evidence-grounded intelligence workspace for founders is planned.
            This public page shows the implementation status; private research
            and live provider-backed workspaces are not yet verified.
          </p>
          <Link className="primary-cta" href="/login">
            Sign in to Axiom
          </Link>
          <section className="status-panel" aria-labelledby="status-heading">
            <div className="status-heading">
              <h2 id="status-heading">Implementation status</h2>
              <p>Only verified capabilities are marked available.</p>
            </div>
            <ul className="capabilities" aria-label="Current capabilities">
              {capabilities.map((item) => (
                <li className="capability" key={item.id}>
                  <div>
                    <h3>{item.title}</h3>
                    <p>{item.description}</p>
                  </div>
                  <span className={"status status--" + item.state}>
                    {statusLabel(item.state)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </main>
        <footer className="site-footer">
          Axiom · Public foundation · Provider verification pending
        </footer>
      </div>
    </>
  );
}
