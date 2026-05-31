---
title: "XIFT 1.0 — Channel 5: Semantic Discovery Request/Response (SDR)"
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
  - xift-1.0-spec-channel-6.md
  - xift-1.0-spec-channel-7.md
  - xift-custodian-1.0.md
  - xift-interop-1.0.md
---

# XIFT 1.0 — Channel 5: Semantic Discovery Request/Response (SDR)

Common conventions (transport, authentication, back-pressure,
identity handshake primitive, reserved error code ranges) are
specified in `xift-1.0-spec-channels-general.md`. This document
specifies Channel 5 normative content.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

SDR resolves **Case 1**: a thematic pull where the querier expresses
an information need in semantic terms ("experiences about X") and
receives candidate matches without knowing in advance which agents
hold relevant content.

SDR is request/response with optional streaming aggregation. It is
**not** a conversation channel; for sustained refinement after
initial discovery, SCS (Channel 7) is used.

---

## 2. Topology

SDR works in two topologies:

- **P2P direct**: querier sends `XiftSemanticQuery` to one or more
  candidate peers selected via Channel 1 discovery. Suitable for
  small meshes (< 50 agents).
- **Custodian-mediated**: querier sends query to a Trust Custodian
  that maintains an HNSW-shardable index of capability vectors. The
  Custodian returns candidate DIDs ranked by composite score. The
  querier then either fetches via Channel 2 (Handoff) or opens
  Channel 7 (SCS). MANDATORY at mesh > 50 agents (core §10).

---

## 3. XiftSemanticQuery Message

The querier sends:

```
POST /xift/v1/sdr
Content-Type: application/json
Authorization: Signature <signed-challenge>

{
  "query_id": "01HXY...",
  "querier_did": "did:web:org.example.com:agent:querier",
  "created_at": "2026-05-21T10:00:00.000Z",
  "query_text": "experiences with onboarding small-business clients",
  "query_embedding": "<base64-bytes>",
  "embedding_model": "nomic-embed-text-v1.5",
  "bloom_required_capabilities": "<base64-bytes>",
  "constraints": {
    "min_trust_score": 700,
    "max_classification": "confidential",
    "max_pii_classification": "anonymized",
    "purpose_of_use": "operations",
    "memory_scopes": ["episodic", "semantic"],
    "max_results": 5,
    "max_latency_ms": 2000,
    "cost_budget_tokens": 5000
  },
  "policy_tags_required": ["audit-required"],
  "scope_redaction_applied": true,
  "query_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:agent:querier#key-1"
}
```

| Field                        | Type    | Purpose                                                            |
|------------------------------|---------|--------------------------------------------------------------------|
| `query_id`                   | ULID    | Unique identifier for this query.                                  |
| `querier_did`                | DID     | Querying agent's DID.                                              |
| `query_text`                 | string  | Natural-language statement of need.                                |
| `query_embedding`            | bytes   | OPTIONAL. Pre-computed embedding to skip server-side encoding.    |
| `embedding_model`            | string  | Identifier of the embedding model used.                            |
| `bloom_required_capabilities`| bytes   | OPTIONAL. Bloom filter of capabilities the responder MUST have.    |
| `constraints`                | object  | Constraints on acceptable responders. See §4.                     |
| `policy_tags_required`       | array   | OPTIONAL. Tags that responding artifacts MUST carry.               |
| `scope_redaction_applied`    | boolean | Asserts that the querier has already redacted PII from query_text.|
| `query_signature`            | string  | Ed25519 signature over JCS(query minus this field).               |
| `signing_key_id`             | string  | Key used to sign the query.                                        |

The query MUST be signed. Custodians and peers MUST verify the
signature before processing.

---

## 4. Constraints Object

| Field                    | Purpose                                                          |
|--------------------------|------------------------------------------------------------------|
| `min_trust_score`        | Responder's trust score MUST be ≥ this value.                    |
| `max_classification`     | Returned artifacts MUST have classification ≤ this.              |
| `max_pii_classification` | Returned artifacts MUST have pii_classification ≤ this (anonymized < pseudonymized < personal-identifiable). |
| `purpose_of_use`         | Purpose under which the querier will use returned artifacts.     |
| `memory_scopes`          | Array of acceptable `memory_scope` values.                       |
| `max_results`            | Maximum number of candidate matches to return.                   |
| `max_latency_ms`         | Cutoff for waiting on responses; partial results accepted.       |
| `cost_budget_tokens`     | Soft hint for budget-aware routing decisions.                    |
| `max_cost_per_result`    | OPTIONAL. Billing constraint. See §4.1.                          |

`max_classification` and `max_pii_classification` are **egress
constraints**: the querier declares the highest level of sensitivity
it can responsibly handle for the declared `purpose_of_use`. This
is part of egress DLP — the querier doesn't just receive whatever
matches semantically; it constrains what it asks for.

### 4.1 Billing Constraint: `max_cost_per_result`

The `XiftSemanticQuery` constraints object gains an OPTIONAL
billing-aware constraint:

```json
{
  "constraints": {
    "...existing constraints...",
    "max_cost_per_result": {
      "amount": "0.01",
      "currency": "USDC"
    }
  }
}
```

Responders whose price exceeds this limit are excluded from results.
The Trust Custodian can pre-filter using `resource_costs` from
capability advertisements (see
`xift-1.0-spec-channel-1.md` §4.6).

---

## 5. XiftSemanticResponse Message (Bundle)

The responder (peer or Custodian) returns:

```
HTTP 200 OK
Content-Type: application/json

{
  "query_id": "01HXY...",
  "responder_did": "did:web:org.example.com:custodian-A",
  "created_at": "2026-05-21T10:00:01.500Z",
  "match_count": 3,
  "matches": [
    {
      "candidate_did": "did:web:org.example.com:agent:beta",
      "envelope_id_hint": "01HXX...",
      "composite_score": 0.87,
      "score_breakdown": {
        "semantic_alignment": 0.92,
        "policy_compatibility": 0.85,
        "resource_fit": 0.81,
        "spec_similarity": 0.90
      },
      "preview": "Anonymized summary fragment ≤ 200 chars",
      "memory_scope": "semantic",
      "classification": "internal",
      "pii_classification": "anonymized",
      "purpose_compatible": true,
      "handoff_endpoint": "https://agent-beta.example.com/xift/v1/envelopes",
      "scs_endpoint": "https://agent-beta.example.com/xift/v1/scs"
    }
  ],
  "completed": false,
  "partial_reason": "max_latency_ms reached; 2 candidates pending",
  "responder_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:custodian-A#key-1"
}
```

| Field                  | Purpose                                                            |
|------------------------|--------------------------------------------------------------------|
| `query_id`             | Echoed from the original query.                                    |
| `responder_did`        | DID of the responder (Custodian or peer).                          |
| `match_count`          | Number of matches in this bundle (may be < `max_results`).         |
| `matches`              | Array of match objects.                                            |
| `completed`            | Whether this is the final response or a partial one.               |
| `partial_reason`       | If `completed=false`, why (timeout, ongoing aggregation).          |
| `responder_signature`  | Ed25519 signature.                                                 |

---

## 6. Match Object

| Field                  | Purpose                                                                |
|------------------------|------------------------------------------------------------------------|
| `candidate_did`        | DID of the agent that holds the candidate artifact.                    |
| `envelope_id_hint`     | OPTIONAL. Specific artifact identifier, if responder knows it.         |
| `composite_score`      | Aggregate match score in [0.0, 1.0].                                   |
| `score_breakdown`      | Four-dimensional decomposition. See §7.                                |
| `preview`              | Short, redacted summary (≤ `sdr_preview_size_max`, see §11).           |
| `memory_scope`         | Scope of the candidate artifact.                                       |
| `classification`       | Sensitivity of the candidate.                                          |
| `pii_classification`   | Identifiability of the candidate.                                      |
| `purpose_compatible`   | Whether the candidate's declared `purpose_of_use` matches query.       |
| `handoff_endpoint`     | URL to fetch the full envelope via Channel 2.                          |
| `scs_endpoint`         | OPTIONAL. URL to open Channel 7 (SCS) with this candidate.            |

The `preview` MUST be redacted of PII. It is provided to help the
querier decide which candidates to fetch in full. Previews longer
than `sdr_preview_size_max` are truncated.

---

## 7. Composite Score (Four-Dimensional)

The `composite_score` is computed by the responder from four
dimensions, each in [0.0, 1.0]:

| Dimension              | Meaning                                                                |
|------------------------|------------------------------------------------------------------------|
| `semantic_alignment`   | Cosine similarity between query embedding and candidate's content/capability embedding. |
| `policy_compatibility` | How well the candidate's governance attributes match the query constraints. |
| `resource_fit`         | Compatibility with the query's `max_latency_ms` and `cost_budget_tokens`. |
| `spec_similarity`      | Cosine similarity between querier's and candidate's spec embeddings (behavioral alignment). |

The aggregation function (weighted sum, geometric mean, etc.) is
implementation-defined. Responders SHOULD document their aggregation
in capability advertisements for transparency. Queriers MAY ignore
`composite_score` and rank by their own function over
`score_breakdown`.

---

## 8. Streaming Aggregation (Optional)

For long-running queries with many candidates, the responder MAY
return SSE-streamed partial results:

```
GET /xift/v1/sdr/{query_id}/stream
Accept: text/event-stream
```

Events:

```
event: partial_match
data: { ... single Match object ... }

event: completed
data: { "match_count": 7, "responder_signature": "..." }
```

Streaming is at the responder's discretion. Queriers MUST handle both
batch and streaming responses.

---

## 9. Top-K and Scatter-Gather

In P2P direct mode, the querier sends the same `XiftSemanticQuery`
to N peers in parallel (scatter), waits for `max_latency_ms` (or
until `max_results` are gathered), and aggregates the union of
matches (gather). Duplicates by `envelope_id_hint` MUST be
deduplicated.

In Custodian-mediated mode, the Custodian performs scatter-gather
internally and returns the top-K aggregated.

---

## 10. SDR Egress Obligations

Per core §8.4 (egress validation MUST happen before any envelope
is emitted), SDR adds the following channel-specific obligations:

Before sending a `XiftSemanticQuery`:

- The querier MUST validate that `query_text` does not contain PII
  beyond what `purpose_of_use` and target peer trust scores permit.
- The querier MUST set `scope_redaction_applied: true` only after
  performing PII redaction on the query.
- If the query carries `policy_tags_required`, the querier MUST
  ensure those tags align with the declared `purpose_of_use`.

Falsely asserting `scope_redaction_applied: true` is a policy
violation; receivers that detect residual PII MAY emit `policy:channel5:preview_redaction_insufficient` (204, warning)
(`preview_redaction_insufficient`) and propagate a trust score
penalty signal.

---

## 11. SDR Normative Parameters

Channel 5-specific parameters extending core §10:

| Parameter                                          | Default     | Purpose                                                       |
|----------------------------------------------------|-------------|---------------------------------------------------------------|
| `sdr_query_size_max`                               | 4 KB        | Maximum `XiftSemanticQuery` size.                             |
| `sdr_preview_size_max`                             | 200 chars   | Maximum `preview` length per match.                           |
| `sdr_max_results_hard_cap`                         | 50          | Absolute cap on `max_results` in any query.                   |
| `sdr_max_latency_default_ms`                       | 2000        | Default `max_latency_ms` if querier omits.                    |

---

## 12. Channel 5 Anti-Patterns and Mitigations

### 12.1 Cold-Start Discovery

New agents with novel capabilities remain unmatched.

Mitigation:
- Custodian bootstraps new agents into the HNSW index on
  registration.
- Initial trust score baseline (500 in reference implementation)
  provides acceptance threshold for non-sensitive matches.
- `quality` extension allows initial self-declared confidence (see
  `xift-1.0-spec-channels-general.md` §8).

### 12.2 LLM Cost Runaway

Mitigation:
- Three-layer model (core §2): LLM only on model-layer codes.
- SDR's deterministic matching first; LLM only on
  `composite_score` ambiguity.
- `cost_budget_tokens` in SDR queries provides budget hints.
- Configurable error thresholds (core §12.4).

### 12.3 Embedding Lock-in

Mitigation:
- Capability vectors carry `model` and `dimensions` (see
  `xift-1.0-spec-channel-1.md` §4.3).
- Multiple capability vectors per agent allowed (different models).
- SDR queriers declare their `embedding_model`; responders MAY
  reject incompatible models with `protocol:channel5:embedding_model_unsupported` (105).

---

## 13. SDR Error Codes (Extends the core Catalog)

SDR-specific conditions. Per the XIFT error model (core §12,
ADR-XIFT-ERROR-MODEL-001), `code` is the generic routing axis and
`category` is the source of domain truth:

| Code | Layer    | Severity | Category                          | Description                                          |
|------|----------|----------|-----------------------------------|------------------------------------------------------|
| 101 | protocol | error | `protocol:channel5:query_signature_invalid` | `query_signature` did not verify.                    |
| 105 | protocol | error | `protocol:channel5:embedding_model_unsupported` | Responder does not support `embedding_model`.        |
| 108 | protocol | error | `protocol:channel5:query_size_exceeded` | Query exceeds size limit.                            |
| 104 | protocol | warning | `protocol:channel5:partial_results_only` | Returned fewer matches than `max_results`.           |
| 201 | policy | error | `policy:channel5:query_outside_governance` | Query's `max_classification` exceeds responder's policy. |
| 202 | policy | error | `policy:channel5:cost_budget_insufficient` | Responder's cost exceeds `cost_budget_tokens`.       |
| 204 | policy | warning | `policy:channel5:preview_redaction_insufficient` | Responder suspects preview may contain residual PII; querier should re-redact. |

---

## 14. Open Questions

1. **Embedding model registry.** Agents declare embedding models in
   capability vectors and SDR queries. Should XIFT provide a
   non-normative registry of model identifiers (akin to a JOSE
   algorithm registry) so that vendors don't collide?
