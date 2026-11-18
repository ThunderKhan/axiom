# Security policy

Axiom handles founder product profiles, research evidence, CRM drafts, and externally sourced data. Security reports are treated as high priority.

## Private reporting

**Do not disclose exploit details, credentials, private customer records, tokens, or sensitive security logs in public GitHub issues, pull requests, or discussions.**

To report a vulnerability confidentially, use GitHub's [Report a vulnerability](https://github.com/ThunderKhan/axiom/security/advisories/new) workflow. Open the repository's **Security and quality → Advisories** page and select **Report a vulnerability** to submit a private report visible to the repository maintainers.

Include the affected component or version, potential impact, reproduction conditions, and a minimal, sanitized proof of concept. Share sensitive reproduction details **only inside the private report**; never publish secrets, third-party personal data, or access tokens.

**If GitHub does not offer the private reporting form**, do not fall back to a public issue or PR comment. Use a private contact already established with the maintainer and ask for a confidential reporting route. The owner has reported enabling private vulnerability reporting on 18 November 2026; availability to an external reporter has not been independently verified by repository CI or the connected GitHub integration.

Do not conduct active scans or tests against production or other users' workspaces without explicit permission.

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
