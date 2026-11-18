# Security policy

Axiom handles founder product profiles, research evidence, CRM drafts, and externally sourced data. Security reports are treated as high priority.

## Private reporting

**Do not open public GitHub issues or PR comments with exploit details, credentials, private customer records, tokens, or sensitive security logs.**

**Current limitation:** GitHub Private Vulnerability Reporting has not been enabled for this repository, and no verified private security mailbox has been supplied. Consequently, this repository does **not currently provide a working confidential external intake route**. Do **not** submit sensitive reports, access tokens, exploit details, or personal data through public issues, discussions or PR comments. If you already have an established private contact with the maintainer, use it without publishing details.

**Tracking:** [Issue #3 — enable and verify private vulnerability reporting](https://github.com/ThunderKhan/axiom/issues/3). This is a confirmed outstanding repository-setting dependency, not an implemented feature.

**Required owner configuration before inviting external vulnerability reports:** enable *Private vulnerability reporting* under repository **Settings → Code security and analysis**, verify an external reporter can submit through **Security → Report a vulnerability**, then update this policy and the issue chooser with the tested private report URL. Do not claim that the private reporting feature is live until verified. No production security SLA is claimed.

Include the affected component, impact, reproduction conditions, and a minimal sanitized example. Do not conduct active scans or tests against production or other users' workspaces without explicit permission.

## Security-sensitive areas

- Supabase Auth identity and JWT verification; FastAPI workspace and object authorization.
- PostgreSQL isolation, RLS, migrations and privileged DB connections.
- Remote MCP OAuth 2.1 token audience, scopes, consent and write approval.
- Research source terms, SSRF-safe URL fetching, prompt injection and data provenance.
- Groq/Gemini data-routing privacy and third-party quotas.
- CI workflow permissions, dependency supply chain, secret leakage and production deployment.

Review [ENGINEERING.md](ENGINEERING.md) and [docs/17-SECURITY.md](docs/17-SECURITY.md) for controls and adversarial test expectations.

## Supported versions and response commitment

Axiom is pre-release. No production security support SLA or response-time guarantee is claimed. Fixes and release decisions require assessment and verified tests; never publicize a vulnerability before coordinating a safe remediation.
