---
title: "XIFT 1.0 — Channel 6: Semantic Interest & Experience Announce (SIEA)"
status: draft (v1.0)
date: 2026-05-23
visibility: public
authors:
  - Memgator architecture working group
related:
  - xift-1.0-spec-core.md (core spec)
  - xift-1.0-spec-channels-general.md (general channel specifications)
  - xift-1.0-spec-channel-1.md
  - xift-1.0-spec-channel-2.md
  - xift-1.0-spec-channel-3.md
  - xift-1.0-spec-channel-4.md
  - xift-1.0-spec-channel-5.md
  - xift-1.0-spec-channel-7.md
  - xift-custodian-1.0.md
  - xift-interop-1.0.md
---

# XIFT 1.0 — Channel 6: Semantic Interest & Experience Announce (SIEA)

Common conventions (transport, authentication, back-pressure,
identity handshake primitive, reserved error code ranges) are
specified in `xift-1.0-spec-channels-general.md`. This document
specifies Channel 6 normative content.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

SIEA resolves **Case 2**: agents declare topic of interest (with context),
other agents announce experiences as they accumulate, and the system
matches interests with announcements asymmetrically. No pre-existing
relationship between announcer and interested party is required.

SIEA is **publish + persistent-subscribe**, not request/response.
It complements SDR: where SDR is a synchronous pull at a moment of
need, SIEA is an asynchronous push when something interesting
happens.

---

## 2. Topology

SIEA strongly favors Custodian-mediated topology:

- **Custodian-mediated** (default): announcers publish to a
  Custodian; interested parties subscribe to the Custodian; the
  Custodian matches announcements to subscriptions and routes
  notifications.
- **P2P broadcast** (small meshes only, < 20 agents): announcers
  broadcast to all known peers via Channel 1; peers filter locally
  against their own interests. Inefficient above small thresholds.

Above 50 agents, Custodian-mediated topology is MANDATORY (core
§10).

---

## 3. XiftInterestSubscription Message

A subscriber declares persistent interest:

```
POST /xift/v1/siea/subscriptions
Content-Type: application/json
Authorization: Signature <signed-challenge>

{
  "subscription_id": "01HXZ...",
  "subscriber_did": "did:web:org.example.com:agent:subscriber",
  "created_at": "2026-05-21T10:00:00.000Z",
  "expires_at": "2026-06-21T10:00:00Z",
  "interest_text": "fraud detection patterns in fintech apps",
  "interest_embedding": "<base64-bytes>",
  "embedding_model": "nomic-embed-text-v1.5",
  "bloom_required_capabilities": "<base64-bytes>",
  "constraints": {
    "min_trust_score": 600,
    "max_classification": "internal",
    "max_pii_classification": "anonymized",
    "purpose_of_use": "operations",
    "memory_scopes": ["semantic", "procedural"]
  },
  "delivery_endpoint": "https://api.example.com/xift/v1/siea/inbox",
  "max_match_notifications_per_hour": 10,
  "subscription_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:agent:subscriber#key-1"
}
```

| Field                                | Purpose                                                            |
|--------------------------------------|--------------------------------------------------------------------|
| `subscription_id`                    | ULID; used for renewal and revocation.                             |
| `subscriber_did`                     | DID of the agent expressing interest.                              |
| `expires_at`                         | Subscription validity. MUST be ≤ `siea_subscription_max_duration` (§8). |
| `interest_text`                      | Natural-language description of interest.                          |
| `interest_embedding`                 | Pre-computed embedding.                                            |
| `constraints`                        | Match constraints (mirror of SDR constraints).                     |
| `delivery_endpoint`                  | Where to push match notifications.                                 |
| `max_match_notifications_per_hour`   | Subscriber-declared rate limit on inbound notifications.           |
| `subscription_signature`             | Ed25519 signature.                                                 |

Subscriptions MAY carry an OPTIONAL `max_cost_per_notification`
billing constraint in the `constraints` object (same shape as SDR's
`max_cost_per_result`). When set, the Custodian filters out
announcements from announcers whose price exceeds this limit.

---

## 4. XiftExperienceAnnouncement Message

An announcer publishes the availability of an artifact:

```
POST /xift/v1/siea/announcements
Content-Type: application/json
Authorization: Signature <signed-challenge>

{
  "announcement_id": "01HX0...",
  "announcer_did": "did:web:org.example.com:agent:announcer",
  "created_at": "2026-05-21T10:30:00.000Z",
  "expires_at": "2026-05-21T22:30:00Z",
  "envelope_id": "01HXX...",
  "abstract_text": "Fraud detection rules learned from 12 months of e-commerce orders",
  "abstract_embedding": "<base64-bytes>",
  "embedding_model": "nomic-embed-text-v1.5",
  "discoverable_capabilities": "<base64-bytes>",
  "memory_scope": "procedural",
  "classification": "internal",
  "pii_classification": "anonymized",
  "purpose_of_use": "operations",
  "handoff_endpoint": "https://announcer.example.com/xift/v1/envelopes",
  "policy_tags": ["model-training-prohibited"],
  "announcement_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:agent:announcer#key-1"
}
```

| Field                          | Purpose                                                            |
|--------------------------------|--------------------------------------------------------------------|
| `announcement_id`              | ULID; used for retraction.                                         |
| `envelope_id`                  | The artifact being announced (existing or future envelope).        |
| `expires_at`                   | Announcement validity. MUST be ≤ `siea_announcement_max_duration`.|
| `abstract_text`                | Natural-language abstract (≤ `siea_abstract_size_max`).           |
| `abstract_embedding`           | Vector for semantic matching.                                      |
| `discoverable_capabilities`    | Bloom filter of capabilities the artifact relates to.              |
| `memory_scope` / `classification` / `pii_classification` / `purpose_of_use` | Replicate envelope governance for matching. |
| `handoff_endpoint`             | Where the subscriber fetches the envelope via Channel 2.           |
| `announcement_signature`       | Ed25519 signature.                                                 |

The abstract MUST NOT contain PII. Egress validation
(core §8.4) applies: announcer's policy engine MUST validate
the announcement before publication.

---

## 5. XiftMatchNotification Message

When a Custodian (or peer in P2P) matches a subscription with an
announcement, it pushes:

```
POST {subscriber's delivery_endpoint}
Content-Type: application/json
Authorization: Signature <signed-challenge from Custodian>

{
  "notification_id": "01HX1...",
  "custodian_did": "did:web:org.example.com:custodian-A",
  "subscription_id": "01HXZ...",
  "announcement_id": "01HX0...",
  "announcer_did": "did:web:org.example.com:agent:announcer",
  "envelope_id": "01HXX...",
  "composite_score": 0.83,
  "score_breakdown": {
    "semantic_alignment": 0.91,
    "policy_compatibility": 1.00,
    "resource_fit": 0.65,
    "spec_similarity": 0.78
  },
  "created_at": "2026-05-21T10:30:05.000Z",
  "handoff_endpoint": "https://announcer.example.com/xift/v1/envelopes",
  "notification_signature": "<base64url-bytes>"
}
```

The subscriber MAY then fetch the envelope via Channel 2, open a
Channel 7 (CSS) session with the announcer, or ignore the
notification.

---

## 6. Subscription and Announcement Lifecycle

- Subscribers MAY renew before `expires_at` by re-posting the
  subscription with the same `subscription_id`.
- Subscribers MAY revoke by sending DELETE to
  `/xift/v1/siea/subscriptions/{subscription_id}`.
- Announcers MAY retract via DELETE to
  `/xift/v1/siea/announcements/{announcement_id}`.
- Custodians MAY auto-expire records past their `expires_at` without
  notification.

---

## 7. Rate Limiting and Fanout Control

The Custodian MUST enforce both:

- The subscriber's declared `max_match_notifications_per_hour`.
- A protocol-level cap `siea_global_fanout_per_announcement_max`
  (§8), limiting how many subscribers any single announcement
  reaches. This is **fanout control** — the Custodian acts as a
  filter against fan-out explosion (lesson from federated systems).

When the cap is exceeded, the Custodian SHOULD prioritize delivery
by `composite_score` and emit `protocol:channel6:notification_deprioritized`
(108, warning) to subscribers whose notification was deprioritized.

---

## 8. SIEA Egress Obligations

Per core §8.4 (egress validation MUST happen before any envelope
is emitted), SIEA adds the following channel-specific obligations:

Before publishing a `XiftExperienceAnnouncement`:

- The announcer's policy engine MUST validate that `abstract_text`
  is PII-free.
- The abstract MUST be sufficient for matching but minimal for
  confidentiality. The protocol does not enforce length, but
  policies SHOULD set `siea_abstract_size_max` as a hard ceiling.

---

## 9. SIEA Normative Parameters

Channel 6-specific parameters extending core §10:

| Parameter                                          | Default     | Purpose                                                       |
|----------------------------------------------------|-------------|---------------------------------------------------------------|
| `siea_subscription_max_duration_seconds`           | 2592000     | 30 days. Hard limit on subscription TTL.                      |
| `siea_announcement_max_duration_seconds`           | 86400       | 24 hours. Hard limit on announcement TTL.                     |
| `siea_abstract_size_max`                           | 1 KB        | Maximum announcement abstract size.                           |
| `siea_global_fanout_per_announcement_max`          | 100         | Maximum subscribers notified per announcement.                |
| `siea_max_active_subscriptions_per_did`            | 32          | Per-agent subscription quota.                                 |

---

## 10. Channel 6 Anti-Patterns and Mitigations

### 10.1 Fanout Explosion

Mitigation:
- `siea_global_fanout_per_announcement_max` is the explicit cap.
- Custodian deprioritizes over-cap notifications instead of queuing.
- Lessons from federated systems applied directly.

---

## 11. SIEA Error Codes

Per the XIFT error model (core §12, ADR-XIFT-ERROR-MODEL-001), `code` is
the generic routing axis and `category` is the source of domain truth;
the table's layer and severity columns complete the routing tuple.


| Code | Layer    | Severity | Category                          | Description                                          |
|------|----------|----------|-----------------------------------|------------------------------------------------------|
| 101 | protocol | error | `protocol:channel6:subscription_signature_invalid` | Subscription signature did not verify.               |
| 101 | protocol | error | `protocol:channel6:announcement_signature_invalid` | Announcement signature did not verify.               |
| 105 | protocol | error | `protocol:channel6:subscription_expired` | Subscription has expired.                            |
| 108 | protocol | error | `protocol:channel6:subscription_quota_exceeded` | Subscriber exceeded `max_active_subscriptions`.      |
| 105 | protocol | warning | `protocol:channel6:subscription_nearing_expiry` | Subscription within 10% of TTL.                      |
| 108 | protocol | warning | `protocol:channel6:notification_deprioritized` | Subscriber deprioritized due to fanout cap.          |
| 201 | policy | error | `policy:channel6:announcement_outside_governance` | Announcement governance fails subscriber's constraints. |
| 204 | policy | warning | `policy:channel6:abstract_redaction_suspect` | Custodian flags potential PII in abstract.           |
