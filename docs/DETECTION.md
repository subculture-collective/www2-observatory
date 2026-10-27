# What the dashboard can and cannot infer

The observatory reports **automation likelihood**, not "AI detected."

Useful behavioral signals include:

- `OPTIONS` capability probes
- `HEAD` probes
- PUT/PATCH/DELETE usage
- command-line or crawler user agents
- explicit preference for JSON or plain text without HTML
- direct requests for `.json`, `.txt`, `.ndjson`, feeds, sitemaps, robots, or `/.well-known/`
- sequences that enumerate multiple alternate representations

A human using curl may score highly. A model operating through a normal browser may score low. Treat the score as a way to prioritize interesting sessions for inspection, never as proof of model identity.

## Stronger observations

More meaningful evidence is longitudinal behavior:

1. a pseudonymous client discovers an unusual surface;
2. it returns later;
3. it writes using a stable convention;
4. a different pseudonymous client retrieves the same unusual resource;
5. that client begins using the convention independently.

The optional application-event log supports basic repeated-token/convention analysis when the public application already emits append-only write events. Access logs alone cannot see POST/PUT request bodies and should not be modified to do so solely for analytics.
