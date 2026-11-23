# WP-09 — Founder CRM screen and API integration

**Status:** PR implementation; verification and provider-backed acceptance pending.
**Authority:** `AGENTS.md`, `ENGINEERING.md`, `docs/03-MVP.md`, `docs/12-UI-UX-SPEC.md`, `docs/13-DESIGN.md`, approved scope cutline, and `docs/26-WP09-DURABLE-LEADS-CONTRACT.md`.

## Boundary

The authenticated `/app` workspace now renders a separate full-width CRM section **only when a workspace was reauthorized by FastAPI**. A second browser auth client is used strictly for Supabase Auth sessions; all domain access goes through the existing FastAPI bearer API.

The screen supports creating a manually supplied public HTTPS source citation and excerpt, saved lead list and reopen, stages, notes, one due/completed follow-up, editable **unsent** outreach draft, revision-guarded updates, archive, and recent activity. A user-supplied citation is **not** automatically fetched, a verified signal or a live research outcome. There is no send action.

All response DTOs are validated against the active workspace ID and expected provenance; unknown stages, malformed timestamps, forged live-origin labels and mismatched owner IDs are rejected before entering the UI. Requests have timeouts, AbortSignals, no browser credential cookies sent to the domain API, and no persistent token cache. Component state is cleared or unmounted on workspace switch and account sign-out. Conflicts and uncertain mutation responses do not silently retry with new idempotency keys. The UI requires a successful authorized list inspection before a new create attempt following a network-uncertain save.

The approved ten-token terracotta/plum palette is used across mobile, keyboard-readable list/detail and forms. No user data is displayed on the public home page, unconfigured auth, or a forged anonymous deep link.

## Honest limitations and remaining work

This is a **workspace-gated CRM screen, not the complete founder discovery journey**. The first 100 records are shown without cross-page pagination; search/filter are supported by the backend but are not yet exposed here. Profile confirmation does not synthesize live opportunities. Real source collection, competitor research, graph/report, saved scenarios, MCP, production hosting, evaluator session provision, hosted Supabase migration/authorization and live-provider E2E must be implemented and verified separately.

No real provider login, live backend screenshot or deployed browser success is claimed by this PR. Default CI tests operate with auth deliberately unconfigured; real-provider tests require separate approved nonproduction accounts in a trace-free setup. Release security review and operator acceptance issue #29 remain open regardless of merge.

## Required evidence

- Web Next.js lint, Prettier, TypeScript typecheck, unit tests, deterministic Playwright browser/keyboard/mobile/anonymous denial, build and integrated API smoke at the exact head.
- Explicit independent review of token handling, tenant-ID reconciliation, malformed response acceptance, owner context stale races, idempotent create uncertainty, and user-supplied URLs.
- Separate authorized test: login, A/B workspaces, manual lead save, refresh/reopen, stale revision conflict, draft persisted but not sent, foreign workspace/other account denied. No secret-bearing trace, screenshot or recording.
