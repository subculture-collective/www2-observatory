# Relay measurement upgrade

Requested 2026-09-22: correct attribution and operator labeling, measure discovery-to-return behavior, separate scanning from engagement, publish useful ordinary resources, and record interventions.

1. Verify Caddy runtime trusts only the tunnel peer. Prefer its validated `client_ip` only when explicitly enabled. Reconcile retained raw-log hashes into existing records, retain original pseudonyms, and rebuild sessions chronologically. Back up database/key before migration; never infer missing visitor identities.
2. Mark future operator requests with `Deadweb-Operator/1.0` and `obs_probe` query tags. These are self-declared markers, not authentication. Unmarked historical traffic remains unknown. Keep it visible and avoid calling the remainder organic.
3. Add classification and an ordered discovery/capability/representation/write/return funnel. Exclude declared operator probes and obvious credential scans. Require success and explicit durable-object matching for return milestones; distinguish client fingerprints from independent participants.
4. Preserve candidate 4 and add research metrics, definitions, and evidence trails using real records. Verify scanner/engagement boundaries, ordered stages, successful redirects, and delayed reads in isolated fixtures.
5. Publish a small webmaster-authored reference shelf on the relay, link it from the current homepage, retain text versions, and publish a dated intervention ledger. Keep forms, feeds, storage, and the public design intact. No invented participants or messages.

Verification: focused Go tests, race tests, container builds, snapshot reconciliation/idempotency, labeled live read probes, private browser journeys, public resource readback, backup and image identity. Production data writes are limited to deploying authored reference resources; test communication writes use disposable state.

## Completion — 2026-09-22 22:53 CDT

All five units are deployed and verified. The Caddy policy already had the required trust restriction; only the observatory needed its computed-client option enabled. Reconciled all 424 pre-cutover records with original identities retained. Snapshot replay was idempotent, live probes were classified as operator activity, reference files matched published bytes, and both services are healthy. Candidate 4 and the relay's existing Go/HTML interface remain in use. See the parent `docs/MEASUREMENT-DEPLOYMENT-2026-09-22.md` for checks, measured counts, image identities, and rollback. Organic write/return activity remains unobserved.
