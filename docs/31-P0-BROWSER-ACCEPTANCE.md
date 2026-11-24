# P0 founder browser acceptance (24 November 2026)

**Status: test implementation only. NOT EXECUTED against a hosted database.**

The explicit nonproduction provider suite now accepts `E2E_P0_ACCEPTANCE=1`
in addition to the existing M1 authorization/environment requirements.
It uses actual browser sign-in and actual FastAPI/database requests. Never
run it with production accounts or traced CI; no screenshots, video or
bearer-token artifacts may be generated.

With the current migrated API and private nonproduction settings in place,
run from `apps/web`:

```powershell
$env:E2E_P0_ACCEPTANCE = '1'
npm run test:provider
Remove-Item Env:E2E_P0_ACCEPTANCE
```

Required existing variables and safety gate: see
[hosted parity runbook](22-M1-HOSTED-DATABASE-PARITY-RUNBOOK.md) and
`playwright.provider.config.ts`. The latest migration head is
`m4_0001_scenarios`; do not apply local disposable test role scripts to hosted.
The earlier M1 provider test alone does not prove this test passes.

This extension creates a workspace-scoped confirmed product profile through
the real authenticated API, saves a clearly **manual synthetic test citation**
in the browser, requests an assessment, opens an evidence edge, saves two
named alternatives, updates lead notes and follow-up, reloads and reopens the
frozen comparison. It then checks foreign-user denial against the same lead
and saved comparison routes. No request stubs, fake authentication or fake
live source labels are involved. Test records remain in the explicitly
authorized nonproduction environment.

Not covered: actual browser onboarding interview completion, real permitted
live provider and competitor acquisition, fresh login scenario replay,
hosted TLS/pooler parity, MCP consent/transport and evaluator deployment.
These remain independent acceptance gates. Record exact tested revision,
environment, pass/fail and remaining limitations in the submission evidence.
