---
title: XIFT 1.0 — Error Taxonomy and Category Registry (Steering Document)
status: draft (v0.10)
date: 2026-05-31
visibility: public
authors:
  - Memgator architecture working group
purpose: |
  Authoritative, versioned category registry for XIFT error and warning
  conditions. One row per condition: numeric routing code (core §12.1),
  `layer:domain:sub_category` namespaced category, layer, severity,
  channel scope, trigger, retryability, emitter, observer, recommended
  remedy, normative source. The numeric code is the deterministic
  routing axis; the category is the source of domain truth and may grow
  without a wire change. Unwanted-behaviour EARS resolve their code and
  category here. Re-engineered per ADR-XIFT-ERROR-MODEL-001,
  ADR-XIFT-ERROR-SIGNING-001 and ADR-XIFT-ERROR-MIGRATION-001.
related:
  - ADR-XIFT-ERROR-MODEL-001.md
  - ADR-XIFT-ERROR-SIGNING-001.md
  - ADR-XIFT-ERROR-MIGRATION-001.md
  - xift-domain-vocabulary.md
  - xift-actor-catalogue.md
  - xift-event-vocabulary.md
  - xift-state-vocabulary.md
  - xift-non-goals.md
  - xift-1.0-spec-core.md
  - xift-1.0-spec-channels-general.md
  - xift-1.0-spec-channel-1.md
  - xift-1.0-spec-channel-2.md
  - xift-1.0-spec-channel-3.md
  - xift-1.0-spec-channel-4.md
  - xift-1.0-spec-channel-5.md
  - xift-1.0-spec-channel-6.md
  - xift-1.0-spec-channel-7.md
  - xift-reference-implementation-architecture.md
---

# XIFT 1.0 — Error Taxonomy

## 0. How to Use This Document

An unwanted-behaviour EARS has the form:

> **if** `<unwanted condition>`, **then the** `<Subject>` **MUST/SHALL** reject with error `<code>` `<category>`.

`<code>` (numeric routing) and `<category>` (namespaced) resolve here. `<Subject>` resolves in
`xift-actor-catalogue.md`. The trigger condition aligns with an
event from `xift-event-vocabulary.md` and a state from
`xift-state-vocabulary.md`.

**Conventions used below**:

- **Code** is the numeric routing code from the canonical per-layer set
  (`xift-1.0-spec-core.md` §12.1): `protocol` 100–199, `policy`
  200–299, `model` 300–399, `custom` 900–999. It is the deterministic
  routing axis and carries no domain meaning.
- **Category** is the `layer:domain:sub_category` namespaced string
  (core §12.5) and is the source of domain truth. The `sub_category`
  preserves the snake_case mnemonic verbatim. This is the
  `category` field on the error wire object (channels-general §10).
- **Layer** is `protocol` or `policy`. `model` and `custom` layers
  exist but carry no normative codes in v1.0.
- **Severity** is `error` or `warning`, **orthogonal** to the code: the
  same code may appear with either severity (core §12.1).
- **Scope** indicates which channel emits the code; `cross` means it
  may originate from any channel. Scope is also reflected in the
  `domain` segment of the category (`channelN` or a cross-channel
  topic).
- **Trigger** is the canonical condition that produces the code,
  expressed close to its "if X" form for direct EARS use.
- **Retryable** indicates whether the sender may retry the same
  envelope as-is. `no` means the envelope is permanently rejected;
  retry requires a different envelope.
- **Emitter / Observer** name actors from `xift-actor-catalogue.md`.
- **Remedy** is a short recommended action for the receiver of the
  error.
- **Source** is the normative document and section.
- **Status** is **(spec)** for entries explicitly defined in a spec.
  Implementation-implied warnings would be marked **(impl-implied)**;
  none exist in v1.0 — every code below is from a spec table.

**Code / namespace conventions** (per `xift-1.0-spec-core.md` §12.1,
§12.5 and `xift-1.0-spec-channels-general.md` §1.7, §11):

Numeric codes come from a small immutable per-layer set; the channel or
topic is carried by the `domain` segment of the category, not by the
code. The canonical codes are:

| Layer    | Codes   | Canonical operational names                                                                                                                  |
|----------|---------|----------------------------------------------------------------------------------------------------------------------------------------------|
| protocol | 100–199 | 101 auth_failed, 102 invalid_argument, 103 rate_limit_exceeded, 104 not_found, 105 failed_precondition, 106 unavailable, 107 deadline_exceeded, 108 resource_exhausted, 109 aborted, 110 internal, 111 unimplemented, 112 version_unsupported |
| policy   | 200–299 | 201 unauthorized, 202 limit_exhausted, 203 precondition_failed, 204 data_protection_violation, 205 scope_not_accepted, 206 trust_below_threshold, 207 consent_invalid |
| model    | 300–399 | 301 ambiguous_context, 302 unmapped_ontology, 303 confidence_low (first catalogued by the `ontology` extension — §10quater)                    |
| custom   | 900–999 | per-deployment; `domain` = reverse-DNS deployment id                                                                                          |

Category `domain` segments: `channel1`…`channel7` for channel-specific
conditions; cross-channel topics include `crypto`, `schema`, `rate`,
`size`, `transport`, `version`, `identity`, `lineage`, `revocation`,
`replay`, `egress`, `extension`, `encryption`, `integrity`, `trust`,
`financial`, `scope`, `gdpr`, `memory`, `governance`, `provenance`,
`quality`, `ontology`, `consent`. The extension `domain` segments
(`governance`, `provenance`, `quality`, `ontology`) reuse the extension
name as the category domain, as `encryption` and `revocation` already do. `consent` is the
cross-channel topic for step-up / additional-assurance conditions
(core §8.6), distinct from the channel-1 handshake-assurance warning.

The numeric codes are NOT renumbered between releases. New conditions
reuse an existing operational code and add a new `category`; the
category registry grows without a wire change. A new numeric layer
requires a superseding ADR.

---

## 1. Core Protocol Errors (code 100–199) — Cross-Channel

These codes may be emitted by any channel handler when a fundamental
wire-protocol invariant is violated.

| Code | Category                            | Layer    | Severity | Scope | Trigger                                                                                                  | Retryable | Emitter                             | Observer       | Remedy                                                                                        | Source                                | Status |
|------|-------------------------------------|----------|----------|-------|----------------------------------------------------------------------------------------------------------|-----------|-------------------------------------|----------------|-----------------------------------------------------------------------------------------------|---------------------------------------|--------|
| 101 | `protocol:crypto:signature_verification_failed`     | protocol | error    | cross | Ed25519 verification over the JCS canonical form failed.                                                  | no        | `Crypto` / `Channel2Handler`        | `Sender`       | Investigate sender's key material; do not retry the same envelope.                            | core §12.5; channel-2 §9              | (spec) |
| 102 | `protocol:crypto:canonicalization_failed`           | protocol | error    | cross | JCS canonicalisation rejected the envelope (NaN, ±Infinity, -0.0, malformed JSON, depth limit).            | no        | `CryptoJCS` / `Channel2Handler`     | `Sender`       | Fix the envelope to conform to RFC 8785; resign; resend.                                       | core §12.5; impl §4.5                 | (spec) |
| 105 | `protocol:extension:unknown_extension`                 | protocol | error    | cross | Envelope declares an extension this receiver does not implement.                                          | no        | any channel handler                 | `Sender`       | Negotiate via Channel 1 capabilities or drop the extension.                                    | core §12.5                            | (spec) |
| 105 | `protocol:encryption:mandatory_encryption_missing`      | protocol | error    | cross | Classification ≥ `Sensitive` but the envelope carries no `encryption` extension.                          | no        | `Channel2Handler`                   | `Sender`       | Add the `encryption` extension; resend.                                                        | core §12.5; channel-2 §9              | (spec) |
| 102 | `protocol:integrity:payload_hash_mismatch`             | protocol | error    | cross | SHA-256 of received payload differs from declared `payload_hash`.                                         | no        | `Channel2Handler`                   | `Sender`       | Verify payload integrity at source; re-issue with corrected hash.                              | core §12.5; channel-2 §9              | (spec) |
| 106 | `protocol:channel3:status_list_unavailable`           | protocol | error    | cross | BSL fetch failed AND cache age exceeded `bsl_max_staleness_seconds`. Fail-closed.                          | yes       | `Channel3Handler`                   | `Sender`       | Wait for BSL host recovery; retry after `Retry-After` seconds.                                  | core §12.5; channel-3 §6              | (spec) |
| 112 | `protocol:version:unsupported_protocol_version`      | protocol | error    | cross | Envelope's `protocol_version` not in receiver's supported list.                                            | no        | any channel handler                 | `Sender`       | Downgrade or upgrade to a mutually-supported version; consult Channel 1 capabilities.          | core §12.5                            | (spec) |
| 106 | `protocol:identity:did_resolution_failed`             | protocol | error    | cross | `DIDResolver::resolve(agent_did)` returned an error.                                                       | yes       | `DIDResolver` (host trait)          | `Sender`       | Verify DID document availability; retry after a delay.                                          | core §12.5                            | (spec) |
| 105 | `protocol:lineage:lineage_policy_inconsistent`       | protocol | error    | cross | `lineage_policy = lax` declared on an envelope with PII (downgrade attempt).                              | no        | any channel handler                 | `Sender`       | Set `lineage_policy = strict` or remove PII before re-issuing.                                 | core §12.5                            | (spec) |
| 108 | `protocol:lineage:lineage_chain_too_deep`           | protocol | error    | cross | `parent_ids` chain length exceeds `lineage_chain_max`.                                                    | no        | any channel handler                 | `Sender`       | Distil or compact the lineage chain; re-issue.                                                | provenance §7                         | (spec) |
| 105 | `protocol:revocation:grant_revoked`                     | protocol | error    | cross | BSL bit at `status_list_index` is 1 (active revocation).                                                   | no        | `Channel3Handler` / any channel     | `Sender`       | Obtain a fresh grant; resend the envelope under the new grant.                                  | core §12.5; channel-3 §3, §9.1        | (spec) |
| 108 | `protocol:channel2:inline_size_exceeded`              | protocol | error    | cross | `payload_inline` size > receiver's `payload_inline_size_max` (default 64 KB).                              | no        | `Channel2Handler`                   | `Sender`       | Switch to `content_ref` with dial-back, or split the artifact.                                  | core §12.5; channel-2 §9              | (spec) |
| 103 | `protocol:rate:rate_limit_exceeded`               | protocol | error    | cross | Per-DID per-endpoint window exceeded `rate_limit_envelopes_per_minute_per_did`.                            | yes       | `RateLimitLayer`                    | `Sender`       | Wait `retry_after_seconds` and resend; reduce concurrency.                                       | core §12.5; channels-general §1.6     | (spec) |
| 105 | `protocol:replay:correlation_id_replay`             | protocol | error    | cross | `correlation_id` reuse or age exceeded `correlation_id_max_age_seconds`.                                   | no        | any channel handler                 | `Sender`       | Generate a fresh ULID `correlation_id`; resend.                                                  | core §12.5                            | (spec) |
| 108 | `protocol:size:envelope_size_exceeded`            | protocol | error    | cross | Total envelope exceeds `envelope_total_size_max`.                                                          | no        | any channel handler                 | `Sender`       | Shrink the envelope (smaller payload, fewer extensions); split into multiple envelopes.          | core §12.5                            | (spec) |
| 107 | `protocol:transport:transport_timeout`                 | protocol | error    | cross | Transport-level timeout (HTTP request did not complete within budget).                                     | yes       | transport layers                    | `Sender`       | Retry after `retry_after_seconds`; consider HTTP/2 if not already.                                | core §12.5                            | (spec) |
| 101 | `protocol:channel1:identity_handshake_failed`         | protocol | error    | cross | Mutual handshake (`HandshakeMethod`) failed within the operational budget.                                 | yes       | `HandshakeMethod` (host trait)      | `Initiator`    | Verify peer's capability advertisement; re-handshake.                                            | core §12.5; channel-1 §10.1            | (spec) |
| 101 | `protocol:channel2:dial_back_unauthorized`            | protocol | error    | cross | A dial-back challenge arrived from a DID that is not the envelope's `recipient_did`.                       | no        | `Channel2Handler`                   | `Sender` (dialled-back) | Investigate forged dial-back; do not serve the artifact.                                | core §12.5                            | (spec) |
| 105 | `protocol:channel2:recipient_mismatch`                | protocol | error    | cross | `recipient_did` does not match this agent's DID.                                                            | no        | any channel handler                 | `Sender`       | Re-issue with the correct `recipient_did`.                                                        | core §12.5; channel-2 §9              | (spec) |
| 105 | `protocol:revocation:grant_expired`                     | protocol | error    | cross | Grant's `consent_until` (or `expires_at`) has passed.                                                       | no        | any channel handler                 | `Sender`       | Obtain a renewed grant; resend.                                                                    | core §12.5                            | (spec) |
| 105 | `protocol:egress:egress_validation_failed`          | protocol | error    | cross | Sender-side egress check (per core §8.4) failed pre-emission.                                              | no        | `EgressGuardLayer` (sender's stack) | (sender-internal) | Fix the failing constraint (`accepts_classifications`, `accepts_memory_scopes`, etc.); resend.  | core §12.5; channel-2 §4.6             | (spec) |

---

## 2. Core Protocol Warnings (code 100–199, severity=warning) — Cross-Channel

| Code | Category                       | Layer    | Severity | Scope | Trigger                                                                  | Retryable | Emitter             | Observer       | Remedy                                                                  | Source        | Status |
|------|--------------------------------|----------|----------|-------|--------------------------------------------------------------------------|-----------|---------------------|----------------|-------------------------------------------------------------------------|---------------|--------|
| 105 | `protocol:revocation:nearing_consent_expiry`       | protocol | warning  | cross | `consent_until` is within 10% of remaining TTL.                          | n/a       | any channel handler | `Sender`       | Renew the grant before expiry to avoid `grant_expired`.                            | core §12.5     | (spec) |
| 206 | `policy:trust:trust_score_marginal`         | policy | warning  | cross | Sender's trust score is within 5% above the configured threshold.        | n/a       | `PolicyCedar`       | `Sender`       | Improve trust posture; expect `trust_score_below_threshold` / `discovery_visibility_denied` if score drops further.         | core §12.5     | (spec) |
| 207 | `policy:consent:additional_assurance_required` | policy | warning  | cross | Step-up: access to `restricted` knowledge requires re-authentication at a higher assurance level (core §8.6). Distinct from the channel-1 handshake warning `policy:channel1:assurance_level_below_target`. | n/a       | `PolicyCedar`       | `Sender`       | Re-run the handshake with a higher-assurance `HandshakeMethod`; retry. | core §8.6; channels-general §2.4 | (spec) |
| 108 | `protocol:lineage:large_lineage_chain`          | protocol | warning  | cross | `parent_ids` chain length > 80% of `lineage_chain_max`.                   | n/a       | any channel handler | `Sender`       | Consider distillation or chain compaction.                                | core §12.5     | (spec) |
| 105 | `protocol:extension:deprecated_extension`         | protocol | warning  | cross | Envelope declares an extension scheduled for deprecation.                 | n/a       | any channel handler | `Sender`       | Migrate to the replacement extension before deprecation date.            | core §12.5     | (spec) |

---

## 2bis. Core Policy Errors — Cross-Channel

These are deterministic, cross-channel policy decisions evaluated by
the host policy engine (not the auxiliary LLM). The canonical example,
used by `xift-1.0-spec-core.md` §12.2, is the rejection of an
unaccepted `memory_scope`; its name is preserved verbatim per the
stable-vocabulary rule.

| Code | Category                                 | Layer  | Severity | Scope | Trigger                                                              | Retryable | Emitter       | Observer | Remedy                                                        | Source     | Status |
|------|------------------------------------------|--------|----------|-------|----------------------------------------------------------------------|-----------|---------------|----------|---------------------------------------------------------------|------------|--------|
| 205  | `policy:scope:memory_scope_not_accepted` | policy | error    | cross | Envelope's `memory_scope` is not in the receiver's accepted set.     | no        | `PolicyCedar` | `Sender` | Re-issue under an accepted `memory_scope`, or negotiate scope. | core §12.2 | (spec) |
| 206  | `policy:trust:trust_score_below_threshold` | policy | error    | cross | Sender's trust score is below the receiver's configured threshold.   | no        | `PolicyCedar` | `Sender` | Improve trust posture; resubmit when above threshold.         | core §12.5; governance §7 | (spec) |

> **Note on vague, model-layer conditions.** Conditions that are
> inherently ambiguous and require LLM adjudication (ambiguous
> classification, novel scenario, ontology mismatch) are **not** policy
> errors; they belong to the `model` layer (codes 300–399) and are
> handled per core §12.3. They are deliberately left thinly enumerated
> here because, by nature, they resist precise cataloguing; the host's
> auxiliary LLM resolves them from the `category` and `context` at
> runtime rather than from a fixed code table.

---

## 3. Cross-Channel Billing Errors and Warnings — `policy:financial:*`

Billing conditions are **policy-layer** decisions in the
`policy:financial:*` namespace (per ADR-XIFT-ERROR-MODEL-001); there is
no numeric financial layer. Reference implementations of XIFT 1.0 do
NOT emit these codes (see `xift-non-goals.md` §9); listed here for
vocabulary completeness.

| Code | Category                                          | Layer  | Severity | Scope | Trigger (phase 3)                                                  | Source                 | Status     |
|------|---------------------------------------------------|--------|----------|-------|--------------------------------------------------------------------|------------------------|------------|
| 202  | `policy:financial:payment_required`               | policy | error    | cross | Provider requires payment before delivery; carries offer in `context`. | channels-general §11 | (reserved) |
| 201  | `policy:financial:payment_proof_invalid`          | policy | error    | cross | `payment_proof` signature or hash verification failed.             | channels-general §11   | (reserved) |
| 203  | `policy:financial:payment_rail_unsupported`       | policy | error    | cross | Provider does not support the buyer's chosen rail.                 | channels-general §11   | (reserved) |
| 203  | `policy:financial:payment_expired`                | policy | error    | cross | `price_declaration.valid_until` has passed.                        | channels-general §11   | (reserved) |
| 202  | `policy:financial:payment_nearing_exhaustion`     | policy | warning  | cross | Prepaid balance nearly depleted.                                   | channels-general §11   | (reserved) |
| 202  | `policy:financial:payment_price_changed`          | policy | warning  | cross | Provider changed price since last interaction.                     | channels-general §11   | (reserved) |
| 201  | `policy:financial:billing_model_rejected`         | policy | error    | cross | Receiver's policy does not accept the declared billing model.      | channels-general §11   | (reserved) |
| 201  | `policy:financial:billing_did_unauthorized`       | policy | error    | cross | `billing_did` is not authorized to pay for this agent's transactions. | channels-general §11 | (reserved) |
| 203  | `policy:financial:settlement_verification_failed` | policy | error    | cross | Payment layer could not verify settlement.                         | channels-general §11   | (reserved) |
| 203  | `policy:financial:dispute_pending_blocks_delivery` | policy | error    | cross | An active dispute blocks further deliveries between these parties. | channels-general §11   | (reserved) |
| 202  | `policy:financial:settlement_pending`             | policy | warning  | cross | Envelope accepted but settlement not yet confirmed.                | channels-general §11   | (reserved) |
| 202  | `policy:financial:free_tier_nearing_limit`        | policy | warning  | cross | Free tier usage approaching limit.                                 | channels-general §11   | (reserved) |
| 206  | `policy:financial:billing_did_trust_low`          | policy | warning  | cross | Payer's trust score warrants prepayment.                           | channels-general §11   | (reserved) |

---

## 4. Channel 1 Errors and Warnings (`domain=channel1`)

Capabilities and handshake.

| Code | Category                              | Layer    | Severity | Scope     | Trigger                                                                                    | Retryable | Emitter            | Observer       | Remedy                                                                  | Source         | Status |
|------|---------------------------------------|----------|----------|-----------|--------------------------------------------------------------------------------------------|-----------|---------------------|----------------|-------------------------------------------------------------------------|----------------|--------|
| 101 | `protocol:channel1:capability_signature_invalid`        | protocol | error    | channel-1 | `capability_signature` failed verification.                                                 | no        | `Channel1Handler`   | `Sender`       | Verify issuer's key; re-fetch advertisement.                            | channel-1 §10.1 | (spec) |
| 101 | `protocol:channel1:capability_did_mismatch`             | protocol | error    | channel-1 | `did` field does not match the resolved DID document.                                       | no        | `Channel1Handler`   | `Sender`       | Investigate issuer's DID document; re-fetch advertisement.              | channel-1 §10.1 | (spec) |
| 102 | `protocol:channel1:capability_schema_invalid`           | protocol | error    | channel-1 | Advertisement fails schema validation.                                                       | no        | `Channel1Handler`   | `Sender`       | Fix advertisement to conform to schema; republish.                       | channel-1 §10.1 | (spec) |
| 105 | `protocol:channel1:capability_advertisement_expired`    | protocol | error    | channel-1 | `expires_at` passed; refresh required.                                                       | yes       | `Channel1Handler`   | `Sender`       | Re-fetch a fresh advertisement.                                          | channel-1 §10.1 | (spec) |
| 105 | `protocol:channel1:handshake_method_unsupported`        | protocol | error    | channel-1 | None of `supported_methods` overlap with responder's.                                        | no        | `HandshakeMethod`   | `Initiator`    | Negotiate a different `HandshakeMethod`.                                  | channel-1 §10.1 | (spec) |
| 107 | `protocol:channel1:handshake_timeout`                   | protocol | error    | channel-1 | Handshake exceeded the 500 ms hard cap.                                                       | yes       | `HandshakeMethod`   | `Initiator`    | Investigate latency between agents; retry.                                | channel-1 §10.1 | (spec) |
| 101 | `protocol:channel1:session_token_invalid`               | protocol | error    | channel-1 | Token verification failed (forged, tampered).                                                  | no        | any channel handler | calling agent  | Re-handshake to obtain a new token.                                       | channel-1 §10.1 | (spec) |
| 105 | `protocol:channel1:session_token_expired`               | protocol | error    | channel-1 | Token past `session_expires_at`.                                                                | yes       | any channel handler | calling agent  | Re-handshake.                                                              | channel-1 §10.1 | (spec) |
| 105 | `protocol:channel1:advertisement_nearing_expiry`        | protocol | warning  | channel-1 | Advertisement within 10% of TTL.                                                                | n/a       | `Channel1Handler`   | (internal)     | Schedule republication.                                                    | channel-1 §10.2 | (spec) |
| 107 | `protocol:channel1:handshake_latency_high`              | protocol | warning  | channel-1 | Handshake completed but exceeded the 200 ms operational target.                                  | n/a       | `HandshakeMethod`   | (internal)     | Investigate latency; consider HTTP/2 connection reuse.                      | channel-1 §10.2 | (spec) |
| 105 | `protocol:channel1:session_token_nearing_expiry`        | protocol | warning  | channel-1 | Token within 10% of TTL; renewal recommended.                                                    | n/a       | any channel handler | calling agent  | Re-handshake proactively before `session_token_expired`.                                       | channel-1 §10.2 | (spec) |
| 206 | `policy:channel1:capability_trust_too_low_to_publish` | policy | error    | channel-1 | Publisher's trust score below indexing threshold (default 600).                                  | no        | `PolicyCedar`       | `Publisher`    | Improve trust posture; resubmit when above threshold.                       | channel-1 §10.3 | (spec) |
| 201 | `policy:channel1:discovery_visibility_denied`         | policy | error    | channel-1 | Querier's trust score below publisher's `min_trust_score_accepted`.                              | no        | `PolicyCedar`       | querier        | Improve trust posture or accept reduced visibility.                          | channel-1 §10.3 | (spec) |
| 105 | `protocol:channel1:did_method_not_accepted`             | protocol | error    | channel-1 | Querier's DID method not in `supported_did_methods`.                                            | no        | `DIDResolver`       | querier        | Use a supported DID method.                                                   | channel-1 §10.3 | (spec) |
| 207 | `policy:channel1:assurance_level_below_target`          | policy   | warning  | channel-1 | Handshake succeeded with lower-than-desired assurance; receiver may step up.                     | n/a       | `HandshakeMethod` / `PolicyCedar` | `Initiator` | Re-authenticate with a higher-assurance method (step-up).                | channel-1 §10.3 | (spec) |
| 204 | `policy:channel1:partial_advertisement_returned`        | policy   | warning  | channel-1 | Some advertisement fields elided due to the querier's trust level.                              | n/a       | `Channel1Handler`   | querier        | Improve trust posture for fuller disclosure; the partial result is usable. | channel-1 §10.2 | (spec) |

---

## 5. Channel 2 Errors and Warnings (`domain=channel2`)

Envelope handoff (signed delivery).

| Code | Category                              | Layer    | Severity | Scope     | Trigger                                                                                       | Retryable | Emitter            | Observer       | Remedy                                                                  | Source        | Status |
|------|---------------------------------------|----------|----------|-----------|-----------------------------------------------------------------------------------------------|-----------|---------------------|----------------|-------------------------------------------------------------------------|---------------|--------|
| 102 | `protocol:channel2:handoff_body_malformed`              | protocol | error    | channel-2 | Request body is not a valid JSON `KnowledgeObject`.                                            | no        | `Channel2Handler`   | `Sender`       | Fix the JSON; resign; resend.                                            | channel-2 §9.1 | (spec) |
| 106 | `protocol:channel2:content_ref_unreachable`             | protocol | error    | channel-2 | Receiver could not fetch the `content_ref` URL.                                                | yes       | `Channel2Handler`   | `Sender`       | Ensure dial-back URL is reachable; re-issue with valid URL.                | channel-2 §9.1 | (spec) |
| 101 | `protocol:channel2:dial_back_challenge_invalid`         | protocol | error    | channel-2 | Challenge signature failed or timestamp expired.                                                | yes       | `Sender`            | `Receiver`     | Issue a fresh challenge; retry dial-back.                                  | channel-2 §9.1 | (spec) |
| 105 | `protocol:channel2:crypto_recipient_kid_mismatch`       | protocol | error    | channel-2 | `encryption.recipient_kid` does not resolve to one of the receiver's own encryption keys (key-resolution failure, distinct from the `recipient_did` check `protocol:channel2:recipient_mismatch`). | no        | `Channel2Handler`   | `Sender`       | Re-encrypt to a held `recipient_kid`; verify the recipient's key from its capability advertisement. | channel-2 §9.1; encryption §7 | (spec) |
| 105 | `protocol:channel2:dial_back_url_expired`               | protocol | error    | channel-2 | `content_ref` URL TTL exceeded (5 minutes for HTTPS).                                            | no        | `Sender`            | `Receiver`     | Sender re-issues envelope with fresh `content_ref`.                         | channel-2 §9.1 | (spec) |
| 105 | `protocol:channel2:storage_uri_unsupported`             | protocol | error    | channel-2 | `content_ref` uses a storage scheme (e.g. `s3://`) not supported by receiver.                  | no        | `Channel2Handler`   | `Sender`       | Use a supported scheme (HTTPS dial-back) or negotiate storage credentials.   | channel-2 §9.1 | (spec) |
| 108 | `protocol:channel2:payload_size_exceeded`               | protocol | error    | channel-2 | Payload fetched via `content_ref` exceeds receiver's `payload_max_size_mb`.                     | no        | `Channel2Handler`   | `Sender`       | Reduce payload or split the artifact.                                       | channel-2 §9.1 | (spec) |
| 107 | `protocol:channel2:storage_access_slow`                 | protocol | warning  | channel-2 | Storage-mediated fetch exceeded latency target (default 2 s).                                    | n/a       | `Channel2Handler`   | (internal)     | Investigate storage backend performance.                                     | channel-2 §9.2 | (spec) |
| 102 | `protocol:channel2:payload_hash_omitted_inline`         | protocol | warning  | channel-2 | Inline payload arrived without `payload_hash`; accepted because `payload_hash` is OPTIONAL inline. | n/a    | `Channel2Handler`   | `Sender`       | Include `payload_hash` for integrity defense-in-depth.                       | channel-2 §9.2 | (spec) |
| 201 | `policy:channel2:receipt_signing_refused`             | policy | error    | channel-2 | Receiver refuses to provide a signed receipt under its policy.                                   | no        | `PolicyCedar`       | `Sender`       | Operate without receipts or negotiate a receipt-bearing relationship.        | channel-2 §9.3 | (spec) |
| 203 | `policy:channel2:inline_recommended_over_reference`   | policy | warning  | channel-2 | Receiver suggests inline delivery next time (small payload sent via `content_ref`).             | n/a       | `Channel2Handler`   | `Sender`       | Send small payloads as `payload_inline` next time.                          | channel-2 §9.4 | (spec) |
| 203 | `policy:channel2:reference_recommended_over_inline`   | policy | warning  | channel-2 | Receiver suggests `content_ref` next time (large payload sent inline).                          | n/a       | `Channel2Handler`   | `Sender`       | Use `content_ref` with dial-back for large payloads next time.              | channel-2 §9.4 | (spec) |

---

## 6. Channel 3 Errors and Warnings (`domain=channel3`)

BSL revocation status.

| Code | Category                       | Layer    | Severity | Scope     | Trigger                                                                                       | Retryable | Emitter            | Observer       | Remedy                                                                  | Source        | Status |
|------|--------------------------------|----------|----------|-----------|-----------------------------------------------------------------------------------------------|-----------|---------------------|----------------|-------------------------------------------------------------------------|---------------|--------|
| 101 | `protocol:channel3:bsl_signature_invalid`        | protocol | error    | channel-3 | BSL credential failed signature verification.                                                  | no        | `Channel3Handler`   | `BSLHost`      | Investigate BSL issuer's key material; refuse to use the BSL.            | channel-3 §9.1 | (spec) |
| 101 | `protocol:channel3:bsl_issuer_unexpected`        | protocol | error    | channel-3 | BSL issuer differs from the envelope's expected issuer.                                         | no        | `Channel3Handler`   | `Sender`       | Re-issue envelope referencing a BSL signed by the expected issuer.        | channel-3 §9.1 | (spec) |
| 102 | `protocol:channel3:bsl_format_invalid`           | protocol | error    | channel-3 | BSL does not conform to W3C v1.0 format.                                                         | no        | `Channel3Handler`   | `BSLHost`      | BSL issuer must publish a conformant BSL.                                  | channel-3 §9.1 | (spec) |
| 105 | `protocol:channel3:bsl_too_short`                | protocol | error    | channel-3 | BSL length below `bsl_min_length_bits` (default 131,072); herd privacy broken.                  | no        | `Channel3Handler`   | `BSLHost`      | Pad BSL to the minimum length; republish.                                  | channel-3 §9.1 | (spec) |
| 102 | `protocol:channel3:bsl_hash_mismatch`            | protocol | error    | channel-3 | BSL hash does not match envelope's `status_list_hash`.                                          | no        | `Channel3Handler`   | `Sender`       | Re-fetch the BSL; re-issue envelope with current hash.                     | channel-3 §9.1 | (spec) |
| 102 | `protocol:channel3:bsl_index_out_of_range`       | protocol | error    | channel-3 | Envelope's `status_list_index` exceeds BSL length.                                              | no        | `Channel3Handler`   | `Sender`       | Re-issue envelope with valid `status_list_index`.                          | channel-3 §9.1 | (spec) |
| 106 | `protocol:channel3:bsl_cache_near_expiry`        | protocol | warning  | channel-3 | Cached BSL within 80% of staleness window.                                                       | n/a       | `Channel3Handler`   | (internal)     | Schedule proactive refresh.                                                 | channel-3 §9.2 | (spec) |
| 106 | `protocol:channel3:bsl_freshness_below_target`   | protocol | warning  | channel-3 | BSL fetch succeeded but is older than ideal (per implementation policy).                          | n/a       | `Channel3Handler`   | (internal)     | Increase refresh cadence or relax `max_staleness_seconds` budget.            | channel-3 §9.2 | (spec) |
| 106 | `protocol:channel3:direct_fetch_recommended`   | protocol | warning  | channel-3 | Custodian-aggregated BSL appears stale; a direct fetch from the issuer is suggested.            | n/a       | `Channel3Handler`   | (internal)     | Fetch the BSL directly from the issuer for freshness-critical checks.        | channel-3 §9.3 | (spec) |
| 206 | `policy:channel3:bsl_host_trust_too_low`       | policy | error    | channel-3 | BSL host's trust score below receiver's threshold.                                              | no        | `PolicyCedar`       | (internal)     | Use a different BSL host or negotiate trust uplift.                          | channel-3 §9.3 | (spec) |

---

## 7. Channel 4 Errors and Warnings (`domain=channel4`)

Change notifications via SSE.

| Code | Category                              | Layer    | Severity | Scope     | Trigger                                                                                       | Retryable | Emitter            | Observer       | Remedy                                                                  | Source         | Status |
|------|---------------------------------------|----------|----------|-----------|-----------------------------------------------------------------------------------------------|-----------|---------------------|----------------|-------------------------------------------------------------------------|----------------|--------|
| 101 | `protocol:channel4:notification_session_required`       | protocol | error    | channel-4 | Channel 4 request without valid session token.                                                 | yes       | `Channel4Handler`   | `Subscriber`   | Handshake to obtain a session token; reconnect.                          | channel-4 §11.1 | (spec) |
| 111 | `protocol:channel4:notification_stream_unsupported`     | protocol | error    | channel-4 | Publisher does not implement Channel 4.                                                          | no        | `Channel4Handler`   | `Subscriber`   | Poll Channel 3 BSL instead, or pick a different publisher.                | channel-4 §11.1 | (spec) |
| 106 | `protocol:channel4:notification_stream_terminated`      | protocol | error    | channel-4 | Publisher closed the stream (graceful shutdown, restart).                                       | yes       | `Publisher`         | `Subscriber`   | Reconnect with `Last-Event-ID` after `retry_after_seconds`.               | channel-4 §11.1 | (spec) |
| 101 | `protocol:channel4:event_signature_invalid`             | protocol | error    | channel-4 | An incoming event's signature failed verification.                                              | no        | `Subscriber`        | (internal)     | Discard the event; do not act on it.                                       | channel-4 §11.1 | (spec) |
| 101 | `protocol:channel4:event_publisher_unexpected`          | protocol | error    | channel-4 | Event `publisher_did` does not match expected publisher.                                        | no        | `Subscriber`        | (internal)     | Discard the event; investigate channel hijacking.                          | channel-4 §11.1 | (spec) |
| 108 | `protocol:channel4:event_replay_buffer_exceeded`        | protocol | error    | channel-4 | `Last-Event-ID` is older than replay buffer; full resync needed.                                 | yes       | `Publisher`         | `Subscriber`   | Full re-sync via Channel 3 BSL pull, then reopen SSE without `Last-Event-ID`. | channel-4 §11.1 | (spec) |
| 102 | `protocol:channel4:event_schema_invalid`                | protocol | error    | channel-4 | Event payload fails schema validation.                                                            | no        | `Subscriber`        | (internal)     | Discard the event; raise an issue against the publisher.                    | channel-4 §11.1 | (spec) |
| 106 | `protocol:channel4:notification_keepalive_lost`         | protocol | error    | channel-4 | Subscriber detected absence of keepalives (90 s silence); reconnecting.                          | yes       | `Subscriber`        | (internal)     | Reconnect with `Last-Event-ID`.                                              | channel-4 §11.1 | (spec) |
| 108 | `protocol:channel4:notification_connection_refused`     | protocol | error    | channel-4 | Publisher refused the SSE or WebSocket connection due to subscriber capacity exhaustion (§7.6 of channels-general) or other publisher-side constraint. The response MUST include a `Retry-After` header. | yes       | `Publisher`         | `Subscriber`   | Retry after `retry_after_seconds`; fall back to Channel 3 polling; reduce subscription concurrency. | channel-4 §11.1; channels-general §7.6 | (spec) |
| 101 | `protocol:channel4:notification_reauth_required`        | protocol | error    | channel-4 | Session token expired mid-stream; re-handshake needed.                                            | yes       | `Publisher`         | `Subscriber`   | Re-handshake; reconnect with fresh token and `Last-Event-ID`.                  | channel-4 §11.1 | (spec) |
| 103 | `protocol:channel4:notification_high_event_rate`        | protocol | warning  | channel-4 | Subscriber receiving events faster than recommended rate.                                          | n/a       | `Subscriber`        | (internal)     | Throttle downstream consumers or filter at subscription.                       | channel-4 §11.2 | (spec) |
| 108 | `protocol:channel4:notification_buffer_nearing_full`    | protocol | warning  | channel-4 | Publisher's replay buffer 80% full; resync recommended.                                            | n/a       | `Publisher`         | `Subscriber`   | Consider resyncing via Channel 3 to release buffer pressure.                    | channel-4 §11.2 | (spec) |
| 107 | `protocol:channel4:keepalive_delayed`                   | protocol | warning  | channel-4 | Keepalive emission delayed beyond 30 s but within 90 s.                                             | n/a       | `Publisher`         | (internal)     | Investigate publisher load; no action by subscriber.                            | channel-4 §11.2 | (spec) |
| 201 | `policy:channel4:notification_visibility_denied`      | policy | error    | channel-4 | Subscriber not authorized for events about this scope.                                              | no        | `PolicyCedar`       | `Subscriber`   | Negotiate grant or accept reduced visibility.                                    | channel-4 §11.3 | (spec) |
| 206 | `policy:channel4:subscriber_trust_too_low`            | policy | error    | channel-4 | Subscriber trust score below publisher's threshold.                                                 | no        | `PolicyCedar`       | `Subscriber`   | Improve trust posture; reapply when above threshold.                              | channel-4 §11.3 | (spec) |
| 108 | `protocol:channel4:subscriber_capacity_nearing`       | protocol | warning  | channel-4 | Subscriber count reached 80% of `channel_4_subscriber_capacity`; new connections may soon be refused. | n/a       | `Custodian`         | `Subscriber`   | Prepare a Channel 3 polling fallback before capacity is exhausted.               | channels-general §7.6 | (spec) |
| 204 | `policy:channel4:event_payload_redacted`             | policy | warning  | channel-4 | Some event fields were elided for the subscriber's trust level.                                     | n/a       | `Publisher`         | `Subscriber`   | Improve trust posture for fuller event payloads; the redacted event is usable.   | channel-4 §11.3 | (spec) |

---

## 8. Channel 5 Errors and Warnings (`domain=channel5`)

Semantic Discovery Request.

| Code | Category                          | Layer    | Severity | Scope     | Trigger                                                              | Retryable | Emitter            | Observer       | Remedy                                                                  | Source        | Status |
|------|-----------------------------------|----------|----------|-----------|----------------------------------------------------------------------|-----------|---------------------|----------------|-------------------------------------------------------------------------|---------------|--------|
| 101 | `protocol:channel5:query_signature_invalid`         | protocol | error    | channel-5 | `query_signature` did not verify.                                     | no        | `Channel5Handler`   | querier        | Resign with valid key; resend.                                          | channel-5     | (spec) |
| 105 | `protocol:channel5:embedding_model_unsupported`     | protocol | error    | channel-5 | Responder does not support `embedding_model`.                          | no        | `Channel5Handler`   | querier        | Use a supported model declared in responder's capability advertisement.  | channel-5     | (spec) |
| 108 | `protocol:channel5:query_size_exceeded`             | protocol | error    | channel-5 | Query exceeds size limit (`sdr_query_size_max`).                       | no        | `Channel5Handler`   | querier        | Shrink query; resend.                                                    | channel-5     | (spec) |
| 104 | `protocol:channel5:partial_results_only`            | protocol | warning  | channel-5 | Returned fewer matches than `max_results`.                              | n/a       | `Channel5Handler`   | querier        | Accept partial results or refine query.                                   | channel-5     | (spec) |
| 201 | `policy:channel5:query_outside_governance`        | policy | error    | channel-5 | Query's `max_classification` exceeds responder's policy.                | no        | `PolicyCedar`       | querier        | Lower `max_classification`; resend.                                       | channel-5     | (spec) |
| 202 | `policy:channel5:cost_budget_insufficient`        | policy | error    | channel-5 | Responder's cost exceeds `cost_budget_tokens`.                          | no        | `PolicyZen`         | querier        | Raise budget or accept fewer results.                                      | channel-5     | (spec) |
| 204 | `policy:channel5:preview_redaction_insufficient`  | policy | warning  | channel-5 | Responder suspects preview may contain residual PII.                    | n/a       | `PolicyCedar`       | querier        | Re-redact at consumer side before further use.                              | channel-5     | (spec) |

---

## 9. Channel 6 Errors and Warnings (`domain=channel6`)

Semantic Interest & Experience Announce.

| Code | Category                          | Layer    | Severity | Scope     | Trigger                                                                  | Retryable | Emitter            | Observer       | Remedy                                                                  | Source        | Status |
|------|-----------------------------------|----------|----------|-----------|--------------------------------------------------------------------------|-----------|---------------------|----------------|-------------------------------------------------------------------------|---------------|--------|
| 101 | `protocol:channel6:subscription_signature_invalid`  | protocol | error    | channel-6 | Subscription signature did not verify.                                    | no        | `Channel6Handler`   | `Subscriber`   | Resign and resubscribe.                                                  | channel-6     | (spec) |
| 101 | `protocol:channel6:announcement_signature_invalid`  | protocol | error    | channel-6 | Announcement signature did not verify.                                    | no        | `Channel6Handler`   | `Announcer`    | Resign and republish.                                                     | channel-6     | (spec) |
| 105 | `protocol:channel6:subscription_expired`            | protocol | error    | channel-6 | Subscription has expired (`expires_at` past).                              | no        | `Channel6Handler`   | `Subscriber`   | Renew subscription.                                                       | channel-6     | (spec) |
| 108 | `protocol:channel6:subscription_quota_exceeded`     | protocol | error    | channel-6 | Subscriber exceeded `max_active_subscriptions`.                            | no        | `Channel6Handler`   | `Subscriber`   | Cancel an existing subscription or negotiate higher quota.                  | channel-6     | (spec) |
| 105 | `protocol:channel6:subscription_nearing_expiry`     | protocol | warning  | channel-6 | Subscription within 10% of TTL.                                            | n/a       | `Channel6Handler`   | `Subscriber`   | Renew proactively to avoid `subscription_expired`.                                           | channel-6     | (spec) |
| 108 | `protocol:channel6:notification_deprioritized`      | protocol | warning  | channel-6 | Subscriber deprioritized due to fanout cap (`siea_global_fanout_per_announcement_max`). | n/a | `Custodian`         | `Subscriber`   | Tighten subscription constraints; expect partial notification delivery.       | channel-6     | (spec) |
| 201 | `policy:channel6:announcement_outside_governance` | policy | error    | channel-6 | Announcement governance fails subscriber's constraints.                     | no        | `PolicyCedar`       | `Announcer`    | Adjust announcement governance or revise subscriber constraints.             | channel-6     | (spec) |
| 204 | `policy:channel6:abstract_redaction_suspect`      | policy | warning  | channel-6 | Custodian flags potential PII in abstract.                                  | n/a       | `Custodian`         | `Announcer`    | Re-emit announcement with stricter redaction.                                 | channel-6     | (spec) |

---

## 10. Channel 7 Errors and Warnings (`domain=channel7`)

Sequential Conversation Session.

| Code | Category                              | Layer    | Severity | Scope     | Trigger                                                                  | Retryable | Emitter            | Observer       | Remedy                                                                  | Source        | Status |
|------|---------------------------------------|----------|----------|-----------|--------------------------------------------------------------------------|-----------|---------------------|----------------|-------------------------------------------------------------------------|---------------|--------|
| 102 | `protocol:channel7:session_request_invalid`             | protocol | error    | channel-7 | Session request signature or structure invalid.                            | no        | `Channel7Handler`   | `Initiator`    | Fix request; resign; retry.                                              | channel-7     | (spec) |
| 101 | `protocol:channel7:session_token_invalid`               | protocol | error    | channel-7 | Token verification failed.                                                  | no        | `Channel7Handler`   | participant    | Re-handshake; reconnect.                                                  | channel-7     | (spec) |
| 105 | `protocol:channel7:message_seq_out_of_order`            | protocol | error    | channel-7 | Sequence number violation (`message_seq` not monotonic).                    | no        | `Channel7Handler`   | sender         | Reset sequence at next message; do not reuse `message_seq`.                  | channel-7     | (spec) |
| 105 | `protocol:channel7:session_expired`                     | protocol | error    | channel-7 | Session past `session_expires_at`.                                          | no        | `Channel7Handler`   | participant    | Open a new session.                                                          | channel-7     | (spec) |
| 108 | `protocol:channel7:session_quota_exceeded`              | protocol | error    | channel-7 | Participant exceeded `max_concurrent_sessions`.                              | no        | `Channel7Handler`   | participant    | Close an existing session or negotiate higher quota.                          | channel-7     | (spec) |
| 105 | `protocol:channel7:session_nearing_expiry`              | protocol | warning  | channel-7 | Session within 10% of duration.                                              | n/a       | `Channel7Handler`   | participant    | Conclude or migrate to a fresh session.                                       | channel-7     | (spec) |
| 108 | `protocol:channel7:round_limit_approaching`             | protocol | warning  | channel-7 | Within 1 round of `max_rounds`.                                              | n/a       | `Channel7Handler`   | participant    | Move toward synopsis or task_complete.                                         | channel-7     | (spec) |
| 201 | `policy:channel7:multi_agent_classification_too_high` | policy | error    | channel-7 | Multi-agent session refused for `Sensitive` classification (3+ participants). | no       | `PolicyCedar`       | `Initiator`    | Drop to 2 participants or lower classification.                                 | channel-7     | (spec) |
| 206 | `policy:channel7:participant_below_trust_threshold`   | policy | error    | channel-7 | An invitee's trust score is too low.                                          | no        | `PolicyCedar`       | `Initiator`    | Replace participant or wait for trust uplift.                                    | channel-7     | (spec) |
| 203 | `policy:channel7:consensus_unreachable`               | policy | warning  | channel-7 | Round closing without consensus; flagging.                                     | n/a       | `Channel7Handler`   | participant    | Reframe motion or end session without consensus.                                  | channel-7     | (spec) |

---

## 10bis. Trust Custodian Errors and Warnings (`domain=custodian`)

Conditions emitted by the Trust Custodian (`xift-custodian-1.0.md` §10).
The Custodian is identified by the `custodian` `domain` segment, not by
a numeric sub-range.

| Code | Category                                              | Layer    | Severity | Scope     | Trigger                                                            | Retryable | Emitter      | Observer     | Remedy                                                       | Source         | Status |
|------|-------------------------------------------------------|----------|----------|-----------|--------------------------------------------------------------------|-----------|--------------|--------------|--------------------------------------------------------------|----------------|--------|
| 101  | `protocol:custodian:registration_signature_invalid`   | protocol | error    | custodian | Capability registration signature did not verify.                 | no        | `Custodian`  | `Agent`      | Resign the registration; resubmit.                           | custodian §10  | (spec) |
| 105  | `protocol:custodian:delta_base_version_unknown`       | protocol | error    | custodian | Δ-gossip delta references an unknown base version.                | yes       | `Custodian`  | `Custodian`  | Request a full snapshot; replay deltas.                      | custodian §10  | (spec) |
| 101  | `protocol:custodian:delegation_signature_invalid`     | protocol | error    | custodian | BSL delegation signature did not verify.                          | no        | `Custodian`  | `Issuer`     | Resign the delegation; resubmit.                             | custodian §10  | (spec) |
| 101  | `protocol:custodian:identity_cache_attestation_invalid`| protocol | error    | custodian | Cached handshake attestation did not verify.                      | no        | `Custodian`  | `Agent`      | Re-handshake to refresh the attestation.                     | custodian §10  | (spec) |
| 106  | `protocol:custodian:custodian_deactivating`           | protocol | error    | custodian | Custodian is in `deactivating` state; request redirected.         | yes       | `Custodian`  | requester    | Follow the 307 redirect to the successor Custodian.          | custodian §10  | (spec) |
| 106  | `protocol:custodian:custodian_unavailable`            | protocol | error    | custodian | All Custodians of this type are unreachable.                      | yes       | requester    | requester    | Fall back to degraded P2P mode; retry later.                 | custodian §10  | (spec) |
| 105  | `protocol:custodian:registration_expired`             | protocol | error    | custodian | Capability registration TTL elapsed.                              | no        | `Custodian`  | `Agent`      | Re-register the capability.                                  | custodian §10  | (spec) |
| 105  | `protocol:custodian:bsl_delegation_expired`           | protocol | error    | custodian | BSL delegation TTL elapsed.                                       | no        | `Custodian`  | `Issuer`     | Renew the delegation.                                        | custodian §10  | (spec) |
| 108  | `protocol:custodian:index_quota_exceeded`             | protocol | error    | custodian | Custodian at capacity limit for indexed capabilities.             | no        | `Custodian`  | `Agent`      | Wait for capacity or use another Custodian.                  | custodian §10  | (spec) |
| 105  | `protocol:custodian:registration_nearing_expiry`      | protocol | warning  | custodian | Capability registration within 10% of TTL.                        | n/a       | `Custodian`  | `Agent`      | Re-register proactively.                                     | custodian §10  | (spec) |
| 105  | `protocol:custodian:bsl_delegation_nearing_expiry`    | protocol | warning  | custodian | BSL delegation within 10% of TTL.                                 | n/a       | `Custodian`  | `Issuer`     | Renew proactively.                                           | custodian §10  | (spec) |
| 108  | `protocol:custodian:custodian_load_high`              | protocol | warning  | custodian | Custodian observing > 80% of its capacity limits.                 | n/a       | `Custodian`  | mesh         | Spawn an additional Custodian or shed load.                  | custodian §10  | (spec) |
| 106  | `protocol:custodian:degraded_p2p_mode`               | protocol | warning  | custodian | No active Custodian; mesh in degraded P2P mode.                   | n/a       | mesh         | agents       | Promote a custodian-eligible agent.                          | custodian §10  | (spec) |
| 106  | `protocol:custodian:no_custodian_available`          | protocol | warning  | custodian | No Custodian active for this service; degraded mode.              | n/a       | mesh         | requester    | Operate in degraded P2P mode.                                | custodian §10  | (spec) |
| 106  | `protocol:custodian:siea_unavailable_degraded_mode`  | protocol | warning  | custodian | SIEA cannot operate in the current degraded mode.                 | n/a       | mesh         | `Subscriber` | Await Custodian recovery; poll Channel 3.                    | custodian §10  | (spec) |
| 103  | `protocol:custodian:subscriber_rate_limit_reached`   | protocol | warning  | custodian | Per-subscriber notification rate limit reached.                   | n/a       | `Custodian`  | `Subscriber` | Reduce subscription breadth.                                 | custodian §10  | (spec) |
| 106  | `protocol:custodian:index_lag_observed`              | protocol | warning  | custodian | Custodian index lag exceeds `capability_index_freshness_seconds`. | n/a       | `Custodian`  | querier      | Expect slightly stale discovery; direct-fetch if critical.   | custodian §10  | (spec) |
| 206  | `policy:custodian:trust_score_insufficient_for_indexing` | policy | error  | custodian | Agent's trust score below `min_trust_score_for_indexing`.         | no        | `Custodian`  | `Agent`      | Improve trust posture; re-register when above threshold.     | custodian §10  | (spec) |
| 206  | `policy:custodian:trust_score_insufficient_for_delegation` | policy | error | custodian | Issuer's trust score below `min_trust_score_for_bsl_hosting`.     | no        | `Custodian`  | `Issuer`     | Improve trust posture; re-delegate when above threshold.     | custodian §10  | (spec) |

---

## 10ter. Extension Policy Errors (`domain=governance|provenance`)

Policy decisions driven by the core extensions. The extension name is
the category `domain` segment. The `governance` extension is the primary
input to policy evaluation, so several of its conditions share the
generic `201 unauthorized` routing code and disambiguate by `category`
(per ADR-XIFT-ERROR-MODEL-001). The `quality` extension is silently
ignorable and registers no codes; a receiver that gates on `quality`
values surfaces a generic `policy:governance:policy_rejection`.

| Code | Category                                                | Layer  | Severity | Scope      | Trigger                                                            | Retryable | Emitter       | Observer | Remedy                                                          | Source         | Status |
|------|---------------------------------------------------------|--------|----------|------------|--------------------------------------------------------------------|-----------|---------------|----------|-----------------------------------------------------------------|----------------|--------|
| 201  | `policy:governance:policy_rejection`                    | policy | error    | governance | Policy engine explicitly rejected the envelope.                    | no        | `PolicyCedar` | `Sender` | Inspect `policy_ref`; satisfy the policy or renegotiate.         | governance §7  | (spec) |
| 201  | `policy:governance:purpose_of_use_mismatch`             | policy | error    | governance | Declared `purpose_of_use` not authorized for this recipient.       | no        | `PolicyCedar` | `Sender` | Re-issue under an authorized `purpose_of_use`.                  | governance §7  | (spec) |
| 201  | `policy:governance:classification_too_high`             | policy | error    | governance | Receiver policy rejects this `classification` sensitivity level.   | no        | `PolicyCedar` | `Sender` | Lower the classification (if legitimate) or use another receiver.| governance §7  | (spec) |
| 201  | `policy:governance:agent_role_not_recognized`           | policy | error    | governance | Declared `agent_role` not in the receiver's role taxonomy.        | no        | `PolicyCedar` | `Sender` | Use a recognized role or rely on fine-grained ABAC attributes.  | governance §7  | (spec) |
| 203  | `policy:governance:consent_unsupportable`               | policy | error    | governance | Receiver cannot honor the declared `consent_until`.               | no        | `PolicyCedar` | `Sender` | Shorten `consent_until` or negotiate the receiver's capability. | governance §7  | (spec) |
| 207  | `policy:governance:consent_vc_invalid`                  | policy | error    | governance | VC at `consent_vc_ref` does not validate.                         | no        | `PolicyCedar` | `Sender` | Provide a valid consent VC; re-issue.                           | governance §7  | (spec) |
| 207  | `policy:governance:consent_vc_hash_mismatch`            | policy | error    | governance | `consent_vc_hash` does not match the fetched VC.                  | no        | `PolicyCedar` | `Sender` | Recompute `consent_vc_hash` over the canonical VC; re-issue.    | governance §7  | (spec) |
| 204  | `policy:provenance:anonymization_evidence_insufficient` | policy | error    | provenance | `anonymization_evidence` does not satisfy the receiver's policy.  | no        | `PolicyCedar` | `Sender` | Strengthen the anonymization method/parameters; re-attest.      | provenance §7  | (spec) |

---

## 10quater. Extension `ontology` Errors and Warnings (`domain=ontology`)

The silently-ignorable `ontology` extension is the **first concrete
consumer of the `model` layer (300–399)** — the layer deliberately left
thinly enumerated (§2 note) for conditions an auxiliary LLM resolves at
runtime. These categories reuse the existing per-layer codes and add only
`category` strings (no wire change, per ADR-XIFT-ERROR-MODEL-001). Unlike
`quality`, `ontology` registers codes because the consuming party verifies
a hash-pin (`102`) and the alignment loop surfaces model-tier outcomes.
The `@context` hash-pin failure routes on **`102`** for registry
consistency — every hash-mismatch (`payload_hash_mismatch`,
`bsl_hash_mismatch`) routes there.

| Code | Category                                  | Layer    | Severity | Scope    | Trigger                                                                                  | Retryable | Emitter             | Observer       | Remedy                                                                       | Source       | Status |
|------|-------------------------------------------|----------|----------|----------|------------------------------------------------------------------------------------------|-----------|---------------------|----------------|------------------------------------------------------------------------------|--------------|--------|
| 102  | `protocol:ontology:context_hash_mismatch` | protocol | error    | ontology | Fetched `@context` body does not match the declared `sha256:` hash-pin (integrity).      | no        | any channel handler | `Sender`       | Re-fetch the `@context`; re-issue the descriptor with the current hash-pin.  | ontology §7  | (spec) |
| 302  | `model:ontology:unmapped_concept`         | model    | error    | ontology | A required concept has no acceptable correspondence in the counterparty's vocabulary.    | no        | `Channel7Handler`   | counterparty   | Negotiate a broader/narrower correspondence, or treat the concept as opaque. | ontology §7  | (spec) |
| 301  | `model:ontology:context_unresolvable`     | model    | error    | ontology | The auxiliary model cannot resolve the asserted correspondence (ambiguous context).      | no        | `Channel7Handler`   | counterparty   | Supply a scoped SKOS projection / SHACL shapes; re-run the alignment probe.  | ontology §7  | (spec) |
| 303  | `model:ontology:alignment_score_low`      | model    | warning  | ontology | A cell's `alignment_score` is below confidence (advisory default; no hard gate).         | n/a       | `Channel7Handler`   | counterparty   | Treat as advisory; gate promotion via `ontology_alignment_min_score` if set. | ontology §7  | (spec) |

> **Advisory by default.** `model:ontology:alignment_score_low` (303) is a
> **warning**; a low or borderline alignment never rejects on its own. A
> **hard reject** at the model layer occurs only when a deployment configures
> `ontology_alignment_min_score` and a required cell falls below it (then a
> `302`/`301` `error`-severity condition is raised), mirroring the `quality`
> soft-acceptance model.

---

## 11. Error Object Shape

Every error and warning travels as a JSON object on the wire with
the shape defined in `xift-1.0-spec-channels-general.md` §10.2:

| Field                  | Type         | Required | Meaning                                                                                                          |
|------------------------|--------------|----------|------------------------------------------------------------------------------------------------------------------|
| `code`                 | integer      | yes      | The numeric routing code (core §12.1); never carries domain meaning.                                            |
| `layer`                | string       | yes      | `protocol` or `policy`.                                                                                          |
| `severity`             | string       | yes      | `error` or `warning`.                                                                                            |
| `category`             | string       | yes      | The `layer:domain:sub_category` namespaced string; source of domain truth.                                      |
| `machine_message`      | string       | yes      | Short machine-parseable summary.                                                                                 |
| `human_message`        | string       | no       | Optional human-readable detail.                                                                                  |
| `envelope_id`          | string       | no       | The envelope this error refers to, if any.                                                                       |
| `correlation_id`       | string       | no       | Echoed from the originating request when present.                                                                |
| `timestamp`            | string       | yes      | RFC3339 of error generation.                                                                                     |
| `retryable`            | boolean      | yes      | Mirrors the "Retryable" column of this catalogue.                                                                |
| `retry_after_seconds`  | integer      | no       | Required when `retryable=true` AND the receiver wants the sender to back off; always set on 429s and on `status_list_unavailable` / `rate_limit_exceeded` / `transport_timeout`. |
| `context`              | object       | no       | Flat map of key → scalar (one level). State snapshot for remediation; keys fold units (e.g. `limitPerMinute`). |
| `remediation_paths`    | array        | no       | Array of `{type, label, uri, action}` objects (one nesting level).                                              |

The whole object is **flat** (one nesting level) and signed in full via
JCS / Ed25519 per **ADR-XIFT-ERROR-SIGNING-001**: the signature covers
`category`, `machine_message`, `human_message`, `context`, and
`remediation_paths`. `human_message` is a single-language string;
localisation is an application-layer concern (a consuming LLM
translates on demand), so there is no per-locale array on the wire.

XIFT 1.0 does NOT define `model` or `custom` codes; both layers
exist in the routing convention (channels-general §10.3) but carry
no normative codes in this release.

---

## 12. Retryability Discipline

Codes marked **retryable = no** are permanent under the *current
envelope*: the same envelope sent again will fail again. The sender
MUST modify something (renew the grant, change the recipient, fix
the JCS form, lower the classification, etc.) before retrying.

Codes marked **retryable = yes** are transient: the same envelope
sent again later may succeed. When the receiver wants the sender to
wait, it MUST include `retry_after_seconds`. Senders MUST honour
`retry_after_seconds` if present and MAY apply exponential backoff
otherwise. Specifically:

- `status_list_unavailable`, `rate_limit_exceeded`, `transport_timeout`,
  `dial_back_challenge_invalid`, `notification_stream_terminated`,
  `notification_connection_refused`, `notification_reauth_required` MUST
  set `retry_after_seconds`.
- `transport_timeout`, `identity_handshake_failed`,
  `content_ref_unreachable` SHOULD set `retry_after_seconds`.
- `did_resolution_failed` MAY set `retry_after_seconds` based on the DID
  method's expected propagation time.

**Warnings (`severity=warning`)** are informational; `retryable` is
`n/a`. A warning does not change the outcome of the request; it
accompanies either a successful response or a stronger error.

---

## 13. Layer Routing Reminder

Per `xift-1.0-spec-channels-general.md` §10.3:

- **`protocol`** errors and warnings are handled internally by the
  XIFT SDK; they surface to the host only on terminal failure of an
  operation.
- **`policy`** errors and warnings are returned to the host SDK,
  which applies deterministic resolution (typically refuse + audit).
- **`model`** and **`custom`** layers are not used by XIFT 1.0 wire
  codes; deployments MAY introduce their own per-deployment codes
  in those layers.

This routing convention is the reason codes are partitioned into
`protocol` and `policy` layers (by numeric range), while the
channel/topic distinction lives in the category `domain` segment, not
in the number.

**Layer-placement principle.** The **availability, capacity,
reachability or freshness** of a protocol component — a channel, an
extension, a wire field, the Custodian — is always a `protocol`-layer
condition (unreachable, unavailable, degraded, capacity/quota
exhausted, stale). The `policy` layer is reserved for **deliberate
governance decisions**: authorization, trust thresholds, consent,
classification, redaction/data-protection, and billing budgets. When a
condition reports that a component cannot serve a request (as opposed
to a policy refusing to), it is `protocol`, and its numeric code must
fall in the `protocol` band (100–199), never `policy` (200–299).

---

## 14. Cross-References

| When writing an unwanted-behaviour EARS …                                              | Resolve …                                                                                       |
|----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| The subject (who emits the error)                                                      | `xift-actor-catalogue.md`                                                                        |
| The data the error mentions (`AgentDid`, `KnowledgeObject`, `Grant`, `BitstringStatusList`, …) | `xift-domain-vocabulary.md`                                                              |
| The event that triggers the error (`SignatureFailed`, `BSLHashMismatch`, …)            | `xift-event-vocabulary.md`                                                                       |
| The state from which the error becomes possible (`Stale`, `BackPressure`, …)           | `xift-state-vocabulary.md`                                                                       |
| Whether the error is in scope at all (or belongs to a non-goal)                        | `xift-non-goals.md`                                                                              |

---

## 15. Change Log

> **Change history:** consolidated in [`spec/CHANGELOG.md`](./CHANGELOG.md) (newest first).

