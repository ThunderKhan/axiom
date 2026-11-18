# Security policy

Axiom handles founder product profiles, research evidence, CRM drafts, and externally sourced data. Security reports are treated as high priority.

## Private reporting

**Do not open public GitHub issues or PR comments with exploit details, credentials, private customer records, tokens, or sensitive security logs.**

Use the repository's **Security** tab and **Report a vulnerability** / private vulnerability reporting when available. If private vulnerability reporting is not enabled, contact a repository maintainer **privately through an established trusted channel** before sharing exploit details; no public contact address is published here. Do not create public proofs of concept.

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
