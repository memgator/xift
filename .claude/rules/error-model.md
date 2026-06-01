---
paths:
  - "spec/**/*.md"
  - "**/xift-error-taxonomy.md"
  - "**/xift-1_0-spec-*.md"
  - "rust/**/*.rs"
---

# XIFT error model rule

Applies when editing any spec, the error taxonomy/registry, or Rust error types.
Established by ADR-XIFT-ERROR-MODEL-001, -SIGNING-001, -MIGRATION-001 (xift-internal).

## The three orthogonal axes

1. **`code`** — integer from a small immutable per-layer set. The deterministic
   routing axis (what routers/SDK/Custodian read for retry, back-pressure,
   fallback). Never carries domain meaning.
   - `protocol` 100–199, `policy` 200–299, `model` 300–399, `custom` 900–999.
   - `0` = OK. Ranges 400–899 and 1000+ are RESERVED (a new layer needs a
     superseding ADR).
   - Canonical protocol codes: 101 auth_failed, 102 invalid_argument,
     103 rate_limit_exceeded, 104 not_found, 105 failed_precondition,
     106 unavailable, 107 deadline_exceeded, 108 resource_exhausted,
     109 aborted, 110 internal, 111 unimplemented, 112 version_unsupported.
   - Canonical policy codes: 201 unauthorized, 202 limit_exhausted,
     203 precondition_failed, 204 data_protection_violation,
     205 scope_not_accepted, 206 trust_below_threshold, 207 consent_invalid.
   - Canonical model codes: 301 ambiguous_context, 302 unmapped_ontology,
     303 confidence_low.

2. **`category`** — `layer:domain:sub_category`, lower_snake, colon-delimited.
   The source of domain truth. Grammar: `segment := [a-z][a-z0-9_]*`.
   - `domain` is the channel (`channel1`…`channel7`), an extension
     (`governance`, `provenance`, `encryption`, `revocation`, `quality`), the
     Custodian (`custodian`), or a cross-channel topic (`crypto`, `rate`,
     `transport`, `version`, `scope`, `trust`, `financial`, `gdpr`, `memory`, …).
   - **Preserved verbatim** as `sub_category`: `memory_scope_not_accepted`;
     CoALA strata (`model:memory:working|episodic|semantic|procedural`); GDPR
     vocabulary.
   - **No numeric `financial` layer.** Billing is `policy:financial:*`.
   - `custom` uses a reverse-DNS deployment id as `domain`
     (`custom:com_acme_mesh:...`; render `.` as `_`).

3. **`severity`** — `error` (envelope REJECTED) or `warning` (ACCEPTED, flagged).
   Orthogonal to `code`: the same code may carry either severity. No warning
   sub-bands, no special "advisory" code.

## Error object shape (flat, signed)

- One nesting level. Top-level scalars: `code`, `layer`, `severity`, `category`,
  `retryable`, `retry_after_seconds`, `machine_message`, `human_message`,
  `envelope_id`, `correlation_id`, `timestamp`.
- `context`: optional flat map of key → scalar; fold the unit into the key
  (`limitPerMinute: 60`, not `limit: "60/min"`).
- `remediation_paths`: optional array of `{type, label, uri, action}`.
- The whole object is signed in full (Ed25519 over JCS / RFC 8785); only the
  outer `sig` member is unsigned. `human_message` is single-language (no
  per-locale array); translation is an application-layer concern.

## Routing vs domain (hybrid consumer)

- A router/SDK/Custodian decides retry/back-pressure/fallback from `code`,
  `layer`, `severity`, `retryable`, `retry_after_seconds` **only** — never by
  parsing `category`.
- An LLM reasons about remediation from `category`, `human_message`, `context`,
  `remediation_paths`.
- An unknown `category` MUST NOT cause a routing failure (forward-compatible).

## Editing discipline

- Greenfield: no four-digit legacy codes anywhere in normative docs; the
  migration to namespaced categories is complete.
- When adding a condition, reuse an existing operational `code` and add a new
  `category`; register it in `xift-error-taxonomy.md`. Do not widen the numeric
  set without an ADR.
