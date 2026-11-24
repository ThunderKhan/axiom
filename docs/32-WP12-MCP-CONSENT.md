# WP-12 — Durable MCP consent boundary

**Status: implementation candidate; not an enabled MCP server.**

The resource-bound delegated verifier distinguishes signed OAuth access
tokens from browser JWTs and checks token scopes. The domain access policy
intersects signed scopes with the current database consent record for the
same authenticated user, client, workspace and resource. The MCP read
operation uses the ordinary CRM store, including its owner checks.

M5 adds one RLS-protected table, `axiom.mcp_client_grants`, and three
policies. Only the owning active founder can access these records through
the runtime identity. Scopes, client, user, workspace, resource and expiry
cannot be updated; revocation is a one-way timestamp, with no reactivation
or deletion. Consent expires within 30 days of its recording. For this
bounded slice a revoked or expired client grant cannot be reissued under
the same tuple; proper reauthorization and session revocation must be
designed with the chosen broker.

The internal `record_reviewed_consent` method is not a public route. It
must be called only after an approved OAuth client registration and
verified founder consent flow. This implementation does not provide such
a flow or establish a provider's identity. No developer-created grant
or synthetic JWT is release evidence. Writes remain denied even if a
token claims a write scope.

Real PostgreSQL tests cover lookup by the verified delegated principal,
scope denial, fresh-instance resolution, foreign owner denial, RLS
visibility, revocation, duplicate grant denial and mutation prevention.
Unit tests cover the token and grant scope intersection. A qualified
security reviewer must examine these boundaries before remote enablement.

Outstanding: compatible authorization broker/PKCE and metadata, consent
UI, current token/session revocation checks, write consent and audit,
durable discovery/assessment data, pinned MCP SDK and external client
verification. No remote tool endpoint or hosted migration is claimed.
