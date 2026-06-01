---
title: "XIFT 1.0 — Channel 2: Envelope Handoff"
status: draft (v1.0)
date: 2026-05-23
visibility: public
authors:
  - Memgator architecture working group
related:
  - xift-1.0-spec-core.md (core spec)
  - xift-1.0-spec-channels-general.md (general channel specifications)
  - xift-1.0-spec-channel-1.md
  - xift-1.0-spec-channel-3.md
  - xift-1.0-spec-channel-4.md
  - xift-1.0-spec-channel-5.md
  - xift-1.0-spec-channel-6.md
  - xift-1.0-spec-channel-7.md
  - xift-custodian-1.0.md
  - xift-interop-1.0.md
---

# XIFT 1.0 — Channel 2: Envelope Handoff

Common conventions (transport, authentication, back-pressure,
identity handshake primitive, reserved error code ranges) are
specified in `xift-1.0-spec-channels-general.md`. This document
specifies Channel 2 normative content.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

Channel 2 is the **direct delivery** of a signed KnowledgeObject
(predecessor name: `MemoryObject`) from one agent to another. It is
the most-used channel: every envelope that crosses a session
boundary travels through Channel 2 (or through dial-back from a
`content_ref`).

Channel 2 handles two payload modes:

- **Inline**: payload base64-encoded inside the envelope's
  `payload_inline` field, ≤ `payload_inline_size_max` (default 64
  KB).
- **Reference**: payload at a `content_ref` URI, fetched separately
  via the dial-back flow (§4).

---

## 2. Topology

Channel 2 is strictly P2P (or storage-mediated, per §5). The
sender knows the recipient by DID; the Trust Custodian does NOT
mediate envelope handoffs. This preserves the privacy property of
the design: the Custodian never sees payloads.

---

## 3. Operation Flow: Inline Handoff

```
Sender                                 Receiver
   |                                          |
   | (egress DLP per core §8.4)            |
   | (envelope construction, sign with        |
   |  canonical_signature)                    |
   |                                          |
   |--POST /xift/v1/envelopes----------------->|
   |   Authorization: Bearer <session_token>  |
   |   Content-Type: application/json         |
   |   Body: <KnowledgeObject envelope>       |
   |                                          | verify session_token
   |                                          | verify canonical_signature
   |                                          | verify payload_hash if present
   |                                          | check extension support
   |                                          | hand to policy engine
   |                                          | (Cedar/Zen evaluation)
   |                                          | (auxiliary LLM if ambiguous)
   |                                          |
   |<--200 OK + { accepted: true } ------------|
   |   OR error code (1xxx/3xxx)              |
   |   OR warning (2xxx/4xxx) + accepted:true |
```

The response body includes:

```json
{
  "envelope_id": "01HXX...",
  "accepted": true,
  "correlation_id_echo": "01HYY...",
  "warnings": [],
  "receiver_signature": "<base64url-bytes>"
}
```

When the envelope is rejected:

```json
{
  "envelope_id": "01HXX...",
  "accepted": false,
  "error": { "code": 205, "layer": "policy", "category": "policy:scope:memory_scope_not_accepted", ... },
  "receiver_signature": "<base64url-bytes>"
}
```

The `receiver_signature` is the receiver's Ed25519 signature over
the response object (excluding the signature itself). This gives
the sender a non-repudiable receipt of acceptance or rejection.

---

## 4. Operation Flow: Dial-Back (content_ref)

When the envelope uses `content_ref` instead of `payload_inline`,
the receiver fetches the payload after accepting the envelope.

```
Sender                                 Receiver
   |                                          |
   |--POST /xift/v1/envelopes----------------->|
   |   (envelope with content_ref,            |
   |    payload_hash)                         |
   |                                          | verify envelope signature
   |                                          | accept envelope (preliminary)
   |<--202 Accepted ------------------------- |
   |                                          |
   |                                          | (dial-back to fetch payload)
   |<-GET <content_ref>-----------------------|
   |  Authorization: Signature                |
   |    <challenge signed by recipient_did>   |
   |                                          |
   | verify challenge signature              |
   | verify requester == recipient_did       |
   | verify challenge freshness (≤ 60s)      |
   | verify dial-back URL TTL (≤ 5 min)      |
   |                                          |
   |--200 OK + payload bytes----------------->|
   |   Content-Type: <content_type>          |
   |                                          | verify payload_hash matches
   |                                          | hand to policy engine
   |                                          |
   |                                          | (final acceptance via Channel 4
   |                                          |  or via 200 OK on a follow-up
   |                                          |  envelope confirmation request)
```

### 4.1 Challenge Signature

The challenge signed by the recipient MUST include:

- A nonce (≥ 128 bits of entropy).
- The recipient's DID.
- The artifact ID being fetched.
- A timestamp within the last 60 seconds.

The sender verifies all four. The 60-second window is strict: older
challenges are rejected with `protocol:channel2:dial_back_challenge_invalid` (101).

### 4.2 Dial-Back URL TTL

The `content_ref` URL itself has a lifetime ≤ 5 minutes. The sender
enforces this by either:

- Signing the URL with a short-lived signature embedded in the URL
  (e.g., AWS-style presigned URL pattern).
- Maintaining a server-side expiry table keyed by URL.

Expired URLs return `protocol:channel2:dial_back_url_expired` (105).

---

## 5. Storage-Mediated Handoff (Optional)

Per core §14.4, when both peers share storage infrastructure,
`content_ref` MAY be a non-HTTPS URI:

- `file://path/to/artifact.bin` (shared filesystem)
- `s3://bucket/key` (object storage with shared credentials)
- `gs://bucket/key` (Google Cloud Storage)
- `azure://container/blob` (Azure Blob Storage)

In these modes:

- The dial-back flow (§4) is replaced by direct storage access.
- The envelope MUST be encrypted at rest unless the deployment
  explicitly audits content for non-sensitive use.
- The `payload_hash` field is REQUIRED to verify integrity after
  retrieval.
- Authentication of the requester relies on the storage system's
  access control (IAM policies, file system permissions), not on
  the XIFT challenge signature.

Storage-mediated handoff is appropriate for high-throughput intra-
cluster exchange. It is the deployer's decision; XIFT does not
normatively endorse or forbid it. The reference implementation
supports this mode as an opt-in for performance-critical
deployments.

---

## 6. Egress DLP for Channel 2

The egress DLP requirement of core §8.4 applies in full to
Channel 2:

- The sender MUST validate `recipient_did` authorization against
  the artifact's `governance` extension before emission.
- The sender MUST verify recipient capabilities support all
  declared `extensions` (consult the recipient's capability
  advertisement, see `xift-1.0-spec-channel-1.md` §3).
- The sender MUST check the recipient's
  `governance_constraints.accepts_classifications` against the
  envelope's classification to avoid futile transmission.

Failure of egress validation returns `protocol:egress:egress_validation_failed` (105)
(`egress_validation_failed`) and the envelope MUST NOT be
transmitted.

---

## 7. Billing-Aware Receipt Enhancement

The Channel 2 receipt (§3) already includes a `receiver_signature`
for delivery proof. For billing-enabled envelopes, the receipt
gains an additional field:

```json
{
  "envelope_id": "01HXX...",
  "accepted": true,
  "billing_acknowledgment": {
    "payment_proof_ref": "https://x402.example.com/proofs/p-12345",
    "settled_amount": "0.005",
    "settled_currency": "USDC",
    "settlement_timestamp": "2026-05-22T10:00:01Z"
  },
  "receiver_signature": "<base64url-bytes>"
}
```

This turns the receipt into a **settlement confirmation**: a signed
proof that the provider received both the payment and the envelope.
It can itself be anchored as a VC for audit.

Cross-channel billing conditions (`policy:financial:payment_required`,
`policy:financial:payment_proof_invalid`,
`policy:financial:payment_rail_unsupported`,
`policy:financial:payment_expired`, and related warnings) are
catalogued in `xift-1.0-spec-channels-general.md` §11.

---

## 8. Implementation Notes (Non-Normative)

### 8.1 Storage of Receipts

Receivers' signed receipts (§3) are non-repudiation evidence.
Senders SHOULD persist them in their audit stream. The
storage format is implementation-defined.

---

## 9. Channel 2 Error Codes

Per the XIFT error model (core §12, ADR-XIFT-ERROR-MODEL-001), `code` is
the generic operational routing axis and `category` is the source of
domain truth; the subsection heading fixes layer and severity.

Channel 2 reuses several cross-channel conditions from the core
catalogue (`protocol:crypto:signature_verification_failed`,
`protocol:crypto:canonicalization_failed`,
`protocol:encryption:mandatory_encryption_missing`,
`protocol:integrity:payload_hash_mismatch`,
`protocol:channel2:inline_size_exceeded`,
`protocol:rate:rate_limit_exceeded`,
`protocol:channel2:recipient_mismatch`,
`protocol:egress:egress_validation_failed`). The conditions below are
specific to the Channel 2 wire-flow.

### 9.1 Protocol Errors

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 102 | `protocol:channel2:handoff_body_malformed` | Request body is not a valid JSON KnowledgeObject.          |
| 106 | `protocol:channel2:content_ref_unreachable` | Receiver could not fetch the `content_ref` URL.            |
| 101 | `protocol:channel2:dial_back_challenge_invalid` | Challenge signature failed or timestamp expired.           |
| 105 | `protocol:channel2:dial_back_url_expired` | `content_ref` URL TTL exceeded.                            |
| 105 | `protocol:channel2:storage_uri_unsupported` | `content_ref` uses a storage scheme not supported by receiver. |
| 108 | `protocol:channel2:payload_size_exceeded` | Payload fetched via `content_ref` exceeds receiver limit.  |

### 9.2 Protocol Warnings

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 107 | `protocol:channel2:storage_access_slow` | Storage-mediated fetch exceeded latency target.            |
| 102 | `protocol:channel2:payload_hash_omitted_inline` | Inline payload arrived without `payload_hash`; accepted.   |

### 9.3 Policy Errors

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 201 | `policy:channel2:receipt_signing_refused` | Receiver refuses to provide a signed receipt (policy).     |

### 9.4 Policy Warnings

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 203 | `policy:channel2:inline_recommended_over_reference` | Receiver suggests inline for next time (small payload via ref).|
| 203 | `policy:channel2:reference_recommended_over_inline` | Receiver suggests `content_ref` for next time (large payload inline). |

---

## 10. Open Questions

1. **Receipt signature obligations.** §3 specifies receipts SHOULD
   be signed by the receiver. Should this be MUST when the envelope
   carries `restricted` classification? Currently policy-decided.

2. **Storage-mediated handoff authentication.** §5 delegates auth
   to the storage system. Is there a XIFT-level convention worth
   specifying for binding the storage credential to the
   `recipient_did`?
