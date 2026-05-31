---
title: "XIFT 1.0 — Channel 1: Discovery & Handshake"
status: draft (v1.0)
date: 2026-05-23
visibility: public
authors:
  - Memgator architecture working group
related:
  - xift-1.0-spec-core.md (core spec)
  - xift-1.0-spec-channels-general.md (general channel specifications)
  - xift-1.0-spec-channel-2.md
  - xift-1.0-spec-channel-3.md
  - xift-1.0-spec-channel-4.md
  - xift-1.0-spec-channel-5.md
  - xift-1.0-spec-channel-6.md
  - xift-1.0-spec-channel-7.md
  - xift-custodian-1.0.md
  - xift-interop-1.0.md
---
 
# XIFT 1.0 — Channel 1: Discovery & Handshake

Common conventions (transport, authentication, back-pressure,
identity handshake primitive, reserved error code ranges) are
specified in `xift-1.0-spec-channels-general.md`. This document
specifies Channel 1 normative content.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

Channel 1 enables an agent to:

- **Publish** its capability advertisement (identity, supported
  extensions, channel endpoints, governance constraints) so peers
  can find it.
- **Discover** other agents' capability advertisements.
- **Establish** an authenticated session via the identity handshake
  primitive (see `xift-1.0-spec-channels-general.md` §2).

Channel 1 is the entry point to all other channels: without
discovery there are no addresses, and without a handshake there is
no authenticated session token to use them.

---

## 2. Topology

Channel 1 supports three topologies:

- **Static configuration** (small meshes): peers are known by
  configuration; Channel 1 is used only for handshake.
- **P2P pull** (≤ 50 agents): an agent fetches another agent's
  capability advertisement directly via HTTPS GET on the publisher's
  Channel 1 endpoint.
- **Custodian-mediated** (> 50 agents, MANDATORY per core §10):
  agents register their capability advertisement with the Trust
  Custodian's Capability Index Service (per `xift-custodian-1.0.md`
  §4), and queriers consume the index instead of pulling from each
  peer.

---

## 3. Capability Advertisement Schema (Baseline)

The capability advertisement is the canonical document describing
an agent's XIFT participation. With the core baseline fields, the
schema is:

```json
{
  "did": "did:web:org.example.com:agent:alpha",
  "name": "Strategy Analyst",
  "version": 12,
  "protocol_version": "1.0",
  "endpoints": {
    "xift_discovery_v1": "https://api.example.com/xift/v1/discovery",
    "xift_handoff_v1":   "https://api.example.com/xift/v1/envelopes",
    "xift_status_v1":    "https://api.example.com/xift/v1/status",
    "xift_changes_v1":   "https://api.example.com/xift/v1/notifications",
    "xift_sdr_v1":       "https://api.example.com/xift/v1/sdr",
    "xift_siea_v1":      "https://api.example.com/xift/v1/siea",
    "xift_css_v1":       "https://api.example.com/xift/v1/css"
  },
  "supported_extensions": [
    "governance", "provenance", "encryption", "revocation"
  ],
  "supported_encryption_schemes": [
    "hpke-x25519-sha256-aes256gcm"
  ],
  "supported_did_methods": ["did:web", "did:key"],
  "max_inline_size_kb": 64,
  "transport_modes": ["inline", "dial-back"],
  "governance_constraints": {
    "min_trust_score_accepted": 600,
    "accepts_classifications": ["public", "internal", "confidential"],
    "accepts_pii_classifications": ["non-personal", "anonymized"]
  },
  "identity_handshake": {
    "supported_methods": ["iatp-v1"],
    "endpoint": "https://api.example.com/xift/v1/handshake",
    "session_token_ttl_seconds": 900
  },
  "advertised_at": "2026-05-21T10:00:00.000Z",
  "expires_at": "2026-05-22T10:00:00.000Z",
  "capability_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:agent:alpha#key-1"
}
```

Baseline Channel 1 fields:

| Field                          | Purpose                                                            |
|--------------------------------|--------------------------------------------------------------------|
| `protocol_version`             | XIFT version supported. v1: `"1.0"`.                               |
| `endpoints`                    | Per-channel endpoint URLs. Endpoints for semantic channels (5–7) are OPTIONAL. |
| `supported_extensions`         | Which envelope extensions this agent processes.                    |
| `supported_did_methods`        | DID methods this agent can resolve.                                |
| `governance_constraints`       | Pre-emission hints for senders (egress DLP support, per §8).      |
| `identity_handshake.endpoint`  | URL where peers initiate the handshake.                            |
| `identity_handshake.supported_methods` | Handshake protocols supported (identity-provider-specific).|
| `advertised_at` / `expires_at` | Lifecycle; agents MUST refresh before expiry.                      |
| `capability_signature`         | Ed25519 over JCS of all fields except this one.                    |

Additional fields (`channel_capabilities`, `capability_vector`,
`resource_costs`, `custodian_eligible`, `mcp_servers`) are specified
in §4 (Extended Capability Advertisement) and are added when the
agent participates in Channel 5–7 or in interop scenarios. They are
OPTIONAL from the baseline perspective.

---

## 4. Extended Capability Advertisement

The capability advertisement is extended with semantic fields needed
by Channels 5–7. The baseline `supported_extensions` array is
augmented; new fields are added to the capability document.

### 4.1 Extended Capability Document

The extended document is a **strict superset** of the baseline (§3):
every baseline field MUST be present, and the new fields listed in
§4.2 are added. The example below shows the complete document; the
baseline fields are preserved unchanged, with the new fields
interleaved for readability.

```json
{
  "did": "did:web:org.example.com:agent:alpha",
  "name": "Strategy Analyst",
  "version": 12,
  "protocol_version": "1.0",
  "endpoints": {
    "xift_discovery_v1": "https://api.example.com/xift/v1/discovery",
    "xift_handoff_v1":   "https://api.example.com/xift/v1/envelopes",
    "xift_status_v1":    "https://api.example.com/xift/v1/status",
    "xift_changes_v1":   "https://api.example.com/xift/v1/notifications",
    "xift_sdr_v1":       "https://api.example.com/xift/v1/sdr",
    "xift_siea_v1":      "https://api.example.com/xift/v1/siea",
    "xift_css_v1":       "https://api.example.com/xift/v1/css"
  },
  "supported_extensions": [
    "governance",
    "provenance",
    "encryption",
    "revocation",
    "quality"
  ],
  "supported_encryption_schemes": [
    "hpke-x25519-sha256-aes256gcm"
  ],
  "supported_did_methods": ["did:web", "did:key"],
  "max_inline_size_kb": 64,
  "transport_modes": ["inline", "dial-back"],
  "channel_capabilities": {
    "sdr": {
      "enabled": true,
      "embedding_models": ["nomic-embed-text-v1.5", "openai-3-small"],
      "max_concurrent_queries": 8
    },
    "siea": {
      "enabled": true,
      "max_active_subscriptions": 32,
      "broadcast_topology": "custodian-mediated"
    },
    "css": {
      "enabled": true,
      "max_concurrent_sessions": 16,
      "max_session_duration_seconds": 3600,
      "supports_smart_clustering": true,
      "supports_consensus_voting": true
    }
  },
  "capability_vector": {
    "embedding": "<base64-bytes>",
    "dimensions": 256,
    "model": "nomic-embed-text-v1.5",
    "bloom_filter": "<base64-bytes>",
    "spec_embedding": "<base64-bytes>"
  },
  "governance_constraints": {
    "min_trust_score_accepted": 600,
    "accepts_classifications": ["public", "internal", "confidential"],
    "accepts_pii_classifications": ["non-personal", "anonymized"]
  },
  "resource_costs": {
    "median_latency_ms": 200,
    "estimated_token_cost_per_query": 0.0005,
    "energy_rating": "A"
  },
  "custodian_eligible": false,
  "identity_handshake": {
    "supported_methods": ["iatp-v1"],
    "endpoint": "https://api.example.com/xift/v1/handshake",
    "session_token_ttl_seconds": 900
  },
  "advertised_at": "2026-05-21T10:00:00.000Z",
  "expires_at": "2026-05-22T10:00:00.000Z",
  "capability_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:agent:alpha#key-1"
}
```

### 4.2 New Capability Fields

| Field                      | Type    | Purpose                                                              |
|----------------------------|---------|----------------------------------------------------------------------|
| `channel_capabilities`     | object  | Per-channel parameters and feature flags.                            |
| `capability_vector`        | object  | VCV per §4.3.                                                        |
| `governance_constraints`   | object  | Receiver-side baseline constraints exposed to discovery.             |
| `resource_costs`           | object  | Hints for cost-aware routing (§4.5).                                 |
| `custodian_eligible`       | boolean | Whether this agent can take the Trust Custodian role (see Custodian spec). |
| `capability_signature`     | string  | Ed25519 signature over JCS(capability document minus this field).    |
| `signing_key_id`           | string  | Key used to sign the capability document.                            |

The capability document MUST be signed. Receivers and Custodians
MUST verify the signature before using any field.

### 4.3 Versioned Capability Vectors (VCV)

The `capability_vector` is a structured object enabling efficient
multi-dimensional matching:

| Field              | Type    | Purpose                                                               |
|--------------------|---------|-----------------------------------------------------------------------|
| `embedding`        | bytes   | Dense vector summarizing the agent's core competencies.               |
| `dimensions`       | integer | Vector dimensionality (typical: 256 or 768).                          |
| `model`            | string  | Identifier of the embedding model used.                               |
| `bloom_filter`     | bytes   | Bloom filter over discrete capability tags (e.g., "tool:sql", "domain:legal"). Enables sub-millisecond pre-filtering before vector computation. |
| `spec_embedding`   | bytes   | Vector encoding the agent's behavioral specification (alignment, helpfulness/harmlessness/honesty signals). Allows queriers to filter not just by "who knows" but by "who aligns with my policies". |

Implementations MUST publish `model` and `dimensions` to enable
queriers to use compatible embeddings. Multiple capability vectors
under different models MAY appear if the implementation supports
multiple embedding schemes; in that case, `capability_vector` becomes
an array.

Rationale: This pattern (Versioned Capability Vectors with Bloom
filters and spec embeddings) is drawn from the Federation of Agents
architecture proposed in 2025 research. It enables the
"match before converse" principle in the semantic channels.

### 4.4 Governance Constraints in Discovery

`governance_constraints` exposes baseline receiver-side requirements
**at discovery time**, before any envelope is sent. This is part of
egress validation (core §8.4): a sender knows in advance whether
a candidate recipient will reject envelopes with certain
classifications, saving round-trips.

| Field                          | Purpose                                                          |
|--------------------------------|------------------------------------------------------------------|
| `min_trust_score_accepted`     | Minimum sender trust score required.                             |
| `accepts_classifications`      | Array of accepted classification values.                         |
| `accepts_pii_classifications`  | Array of accepted PII classifications.                           |
| `accepts_memory_scopes`        | OPTIONAL. Array of accepted `memory_scope` values.               |
| `requires_signed_consent_vc`   | OPTIONAL. Boolean, whether grants MUST be signed VCs (not refs). |

These are hints, not contracts. The receiver's actual policy engine
remains authoritative; constraints may be tighter than declared
(receivers MAY reject for reasons beyond what they advertise).

### 4.5 Resource Costs

| Field                              | Purpose                                                              |
|------------------------------------|----------------------------------------------------------------------|
| `median_latency_ms`                | Reported median latency for an envelope handoff.                    |
| `estimated_token_cost_per_query`   | Hint for cost-aware routing in SDR.                                  |
| `energy_rating`                    | OPTIONAL. Letter rating ('A'–'F') for energy efficiency.            |

Resource costs are advertisements; they may be inaccurate or stale.
Queriers use them as soft signals for routing decisions, not as
binding contracts.

### 4.6 Billing-Aware Resource Costs Enhancement

For billing readiness, the `resource_costs` block gains additional
fields:

```json
{
  "resource_costs": {
    "median_latency_ms": 200,
    "estimated_token_cost_per_query": 0.0005,
    "energy_rating": "A",
    "billing_enabled": true,
    "accepted_currencies": ["USDC", "SAT"],
    "accepted_rails": ["x402", "l402"],
    "billing_models_offered": ["pay-per-envelope", "subscription"],
    "free_tier_available": true,
    "free_tier_limits": {
      "envelopes_per_day": 10,
      "max_classification": "internal"
    }
  }
}
```

This allows SDR queries (Channel 5) to filter by billing
compatibility: "find agents that accept USDC and offer
pay-per-envelope billing."

---

## 5. Operation Flow: Capability Publication

```
Agent Alpha                            Peer / Custodian
   |                                          |
   | (publish advertisement)                  |
   |                                          |
   |--PUT /xift/v1/discovery/self------------>|
   |   (full advertisement,                   |
   |    capability_signature)                 |
   |                                          | verify signature
   |                                          | verify DID resolution
   |                                          | accept or reject (protocol:channel1:capability_did_mismatch, 101)
   |<--201 Created OR error-------------------|
```

In P2P pull topology, agents serve their own advertisement at
`GET /xift/v1/discovery/self` without external registration.

In Custodian-mediated topology, agents register with the Custodian
per `xift-custodian-1.0.md` §4.3.

---

## 6. Operation Flow: Capability Discovery (Pull)

```
Querier Agent                          Target Agent (or Custodian)
   |                                          |
   |--GET /xift/v1/discovery/{did}----------->|
   |   Authorization: Signature <challenge>   |
   |                                          | verify querier signature
   |                                          | apply governance_constraints
   |                                          | (egress DLP: §8)
   |<--200 OK + capability advertisement------|
   |   OR policy:channel1:discovery_visibility_denied (201)|
   |   OR protocol:channel1:capability_advertisement_expired (105)|
```

---

## 7. Operation Flow: Identity Handshake

The handshake is performed before sustained communication. Two
phases:

```
Initiator                              Responder
   |                                          |
   | (Phase A: protocol negotiation)          |
   |--POST /xift/v1/handshake/init----------->|
   |   { initiator_did,                       |
   |     supported_methods: ["iatp-v1"] }     |
   |<--200 OK { method: "iatp-v1",-----------|
   |            challenge_nonce, ... }        |
   |                                          |
   | (Phase B: identity-provider-specific)    |
   | (e.g., IATP handshake completes here     |
   |  within 200 ms budget per                |
   |  `xift-1.0-spec-channels-general.md` §2.1) |
   |                                          |
   |--POST /xift/v1/handshake/complete------->|
   |   { initiator_proof,                     |
   |     trust_score_assertion, ... }         |
   |<--200 OK { session_token,---------------|
   |            session_expires_at,           |
   |            responder_trust_score,        |
   |            responder_proof }             |
```

XIFT specifies Phase A (method negotiation) and the output of
Phase B (session token). Phase B's content depends on the
selected identity-provider method.

The `session_token` returned is used in subsequent channel
requests via `Authorization: Bearer <token>` (per
`xift-1.0-spec-channels-general.md` §1.4).

---

## 8. Egress DLP for Channel 1

Per the recommendation that egress DLP applies to every channel,
Channel 1 has specific obligations:

- The publisher MUST NOT include in its capability advertisement
  any field that would leak sensitive operational details to
  unauthorized peers (e.g., do not advertise tools the agent should
  not be known to have).
- The publisher SHOULD use **scoped advertisements** when its peer
  set spans multiple trust levels: a public advertisement with
  minimal fields, and an extended advertisement gated by trust
  score.
- When serving a discovery pull (§6), the publisher's policy
  engine MUST evaluate the querier's identity against
  `governance_constraints.min_trust_score_accepted` before
  releasing the advertisement. Failure returns `policy:channel1:discovery_visibility_denied` (201).

These obligations parallel the egress validation defined for
envelopes in core §8.4.

---

## 9. Anti-Pattern: Capability Poisoning

Adversarial agents publish inflated capability vectors.

Mitigation:
- Capability documents MUST be signed (§4.1).
- Custodians verify signatures before indexing.
- Trust score gating: capabilities from agents below threshold are
  not indexed.
- External validators (`xift-1.0-spec-extension-quality.md` §3.2)
  can vouch for capabilities.

---

## 10. Channel 1 Error Codes

Per the XIFT error model (core §12, ADR-XIFT-ERROR-MODEL-001), the
numeric `code` is the generic operational routing axis (a small per-layer
set) and the `category` string is the source of domain truth. The
section heading fixes the layer and severity; the same `code` may recur
across rows because routing is deterministic on `(code, severity)` while
the precise condition is carried by `category`. Full registry:
`xift-error-taxonomy.md`.

### 10.1 Protocol Errors

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 101 | `protocol:channel1:capability_signature_invalid` | `capability_signature` failed verification.                |
| 101 | `protocol:channel1:capability_did_mismatch` | `did` field does not match the resolved DID document.      |
| 102 | `protocol:channel1:capability_schema_invalid` | Advertisement fails schema validation.                     |
| 105 | `protocol:channel1:capability_advertisement_expired` | `expires_at` passed; refresh required.                     |
| 105 | `protocol:channel1:handshake_method_unsupported` | None of `supported_methods` overlap with responder's.      |
| 107 | `protocol:channel1:handshake_timeout` | Handshake exceeded 200 ms budget (operational warning per core §2.1, may be downgraded to `protocol:channel1:handshake_latency_high` with severity=warning). |
| 101 | `protocol:channel1:session_token_invalid` | Token verification failed (forged, tampered).              |
| 105 | `protocol:channel1:session_token_expired` | Token past `session_expires_at`.                           |
| 105 | `protocol:channel1:did_method_not_accepted` | Querier's DID method not in `supported_did_methods` (unsupported method; a precondition failure, not a policy decision). |

### 10.2 Protocol Warnings

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 105 | `protocol:channel1:advertisement_nearing_expiry` | Advertisement within 10% of TTL.                           |
| 107 | `protocol:channel1:handshake_latency_high` | Handshake completed but exceeded recommended budget.       |
| 105 | `protocol:channel1:session_token_nearing_expiry` | Token within 10% of TTL; renewal recommended.              |

### 10.3 Policy Errors

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 206 | `policy:channel1:capability_trust_too_low_to_publish` | Publisher's trust score below indexing threshold.          |
| 201 | `policy:channel1:discovery_visibility_denied` | Querier's trust score below publisher's `min_trust_score_accepted`. |

### 10.4 Policy Warnings

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 204 | `policy:channel1:partial_advertisement_returned` | Some fields elided due to querier trust level.             |
| 207 | `policy:channel1:assurance_level_below_target` | Handshake succeeded with lower-than-desired assurance.     |

---

## 11. Open Questions

1. **Handshake method registry.** §7 lists `iatp-v1` as an
   example. Should XIFT publish a non-normative registry of
   recognized handshake methods?
