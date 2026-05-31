---
title: XIFT 1.0 — Extension `quality`
status: draft (v1.0)
date: 2026-05-24
visibility: public
authors:
  - Memgator architecture working group
related:
  - xift-1.0-spec-core.md (core spec)
  - xift-1.0-spec-channels-general.md (cross-channel conventions)
  - xift-1.0-spec-extension-governance.md
  - xift-1.0-spec-extension-provenance.md
  - xift-1.0-spec-extension-encryption.md
  - xift-1.0-spec-extension-revocation.md
  - xift-1.0-spec-channel-2.md (Envelope Handoff)
  - xift-1.0-spec-channel-5.md (Semantic Discovery)
  - xift-1.0-spec-channel-6.md (SIEA)
---

# XIFT 1.0 — Extension: `quality`

This document specifies the `quality` envelope extension. Common
envelope conventions (canonical form, mandatory blocks, signature
mechanics, identity layer, error model) are specified in
`xift-1.0-spec-core.md`.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

The `quality` extension declares quality metrics about a knowledge
artifact: how often it has been applied, with what success rate,
with what self- and externally-assessed confidence, and what
qualitative profile (categories, sample size, freshness) it has.

`quality` is **independent of any specific channel** and can
accompany any envelope on any channel. Receivers that do not declare
support for `quality` ignore the block silently; receivers that do
may use it as a policy input.

Rationale for it being a full envelope extension (rather than a
sub-block of a channel's payload metadata): quality is
artifact-level information that travels with the artifact, not
channel-level information specific to discovery or refinement. An
artifact emitted via Channel 2 (Handoff) for storage carries the
same quality metrics as an artifact returned in an SDR response or
referenced from a SIEA match notification. Defining quality as an
extension keeps it portable across channels.

`quality` is NOT one of the four mandatory-recognition **core
extensions** (`governance`, `provenance`, `encryption`,
`revocation`). It is the fifth declared extension; non-supporting
receivers MUST ignore it silently rather than reject (see §4).

> **Encryption scope.** Per `xift-1.0-spec-extension-encryption.md`
> §1, when the `encryption` extension is present the `quality`
> fields are within the encryption scope (carried inside the
> ciphertext), not in the cleartext envelope metadata. A receiver
> that does not decrypt therefore cannot read `quality`; this is
> consistent with the silently-ignorable model. The remaining
> metadata blocks (`governance`, `provenance`, `revocation`,
> identity) stay in cleartext for policy evaluation by
> intermediaries.

---

## 2. Block Structure

```json
{
  "quality": {
    "evaluated_by": "did:web:org.example.com:agent:emitter",
    "evaluated_at": "2026-05-21T10:00:00Z",
    "evaluation_window_seconds": 86400,
    "metrics": {
      "applied_count": 247,
      "completion_rate": 0.94,
      "fallback_rate": 0.03,
      "user_acceptance_rate": null,
      "downstream_promotion_count": 18
    },
    "confidence": {
      "self_assessed_confidence": 0.85,
      "external_validation_count": 2,
      "external_validators": [
        "did:web:org.example.com:agent:auditor-1"
      ]
    },
    "profile": {
      "task_categories": ["fraud-detection", "transaction-anomaly"],
      "sample_size_indicator": "small",
      "freshness_days": 12
    }
  }
}
```

---

## 3. Fields

| Field                          | Type    | Required | Description                                                                                              |
|--------------------------------|---------|----------|----------------------------------------------------------------------------------------------------------|
| `evaluated_by`                 | DID     | yes      | DID of the agent that produced these metrics.                                                            |
| `evaluated_at`                 | RFC3339 | yes      | When the evaluation was performed (UTC, millisecond precision).                                          |
| `evaluation_window_seconds`    | integer | yes      | Time window over which metrics were collected. MUST be > 0.                                              |
| `metrics`                      | object  | yes      | Quantitative quality indicators (§3.1).                                                                  |
| `confidence`                   | object  | no       | Self- and externally-assessed confidence (§3.2). MAY be omitted when the issuer has no confidence claim. |
| `profile`                      | object  | no       | Qualitative descriptors (§3.3). MAY be omitted.                                                          |

### 3.1 `metrics` Sub-Object

| Metric                        | Type    | Required | Meaning                                                                                                                                                                                                                              |
|-------------------------------|---------|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `applied_count`               | integer | yes      | Number of times the artifact has been used during the evaluation window. MUST be ≥ 0.                                                                                                                                                |
| `completion_rate`             | number  | yes      | Ratio of applications resulting in successful completion. Range [0.0, 1.0].                                                                                                                                                          |
| `fallback_rate`               | number  | yes      | Ratio requiring fallback to an alternative. Range [0.0, 1.0]. `completion_rate + fallback_rate ≤ 1.0` (the residual is the share of outright failures).                                                                              |
| `user_acceptance_rate`        | number  | no       | Ratio of end-user acceptance when applicable. Range [0.0, 1.0]. MAY be `null` when not measured (e.g., headless agent pipelines without a human acceptance signal).                                                                  |
| `downstream_promotion_count`  | integer | no       | Number of times this artifact was promoted to a higher CoALA stratum by receivers (e.g., `episodic → semantic`). Self-reported by the emitter from signals it has collected; omit when the emitter has no visibility into promotion. |

All metrics are self-reported by `evaluated_by`. Receivers MAY trust
or discount them based on the issuer's trust score and external
validation count (§3.2).

### 3.2 `confidence` Sub-Object

| Field                          | Type         | Required | Description                                                                                                                                       |
|--------------------------------|--------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| `self_assessed_confidence`     | number       | yes      | Issuer's own confidence. Range [0.0, 1.0].                                                                                                       |
| `external_validation_count`    | integer      | yes      | Number of external validators that have endorsed this artifact. MUST be ≥ 0 and equal to `length(external_validators)`.                          |
| `external_validators`          | array of DID | yes      | DIDs of validators that have endorsed this artifact. Endorsements are out-of-band (e.g., via signed claims). MAY be the empty array `[]`.        |

### 3.3 `profile` Sub-Object

| Field                   | Type            | Required | Description                                                                                                                                  |
|-------------------------|-----------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------|
| `task_categories`       | array of string | yes      | Tags identifying the categories where the artifact applies. MAY be the empty array `[]`.                                                     |
| `sample_size_indicator` | enum            | yes      | Qualitative sample-size descriptor. Closed enumeration: `small`, `medium`, `large`. Implementations MAY agree on out-of-band thresholds.    |
| `freshness_days`        | integer         | yes      | Age of the artifact in days. Non-negative 16-bit integer, range [0, 32767]. Computed as `floor((now − artifact_creation) / 1 day)`.         |

---

## 4. Receiver Behaviour

A receiver MUST declare `quality` in its `supported_extensions`
(`xift-1.0-spec-channel-1.md` §3, §4) to **parse** the extension
block. If not declared:

- The receiver MUST NOT reject the envelope solely because it
  contains `quality`. This extension is always **silently
  ignorable** — it does not produce error
  `protocol:extension:unknown_extension` (105).
- The receiver MAY treat the envelope as if the extension were
  absent.

If declared:

- The receiver SHOULD pass the block to its policy engine as
  OPTIONAL input.
- The receiver MUST NOT make policy decisions solely on `quality`
  values that have no signed audit trail. Combine with
  `external_validation_count` and `confidence` for higher-stakes
  decisions.

This soft-acceptance model is intentional: it addresses the concern
about implementation complexity. Receivers that do not care about
quality continue working without modification.

---

## 5. Egress DLP for `quality`

Per core §8.4 (Egress Validation):

- The sender MUST sign `evaluated_by` consistently with the
  envelope's `agent_did`. Cross-signed metrics (where
  `evaluated_by` differs from `agent_did`) MUST carry an
  out-of-band proof; the protocol does not enforce verification but
  receivers MAY do so.
- The sender SHOULD NOT publish `quality` metrics whose values are
  obviously stale (`evaluated_at` materially older than the
  envelope's `created_at`) or implausible (`completion_rate +
  fallback_rate > 1.0`). These do not error at the protocol level
  but undermine the issuer's trust score.

---

## 6. Extension Parameters

No `quality`-specific parameters are added by this specification.
The core parameters of `xift-1.0-spec-core.md` §10 apply.

---

## 7. `quality` Error Codes

`quality` does NOT introduce protocol errors. By design, an unknown
`quality` block is **silently ignored**, not rejected.

Policy receivers MAY produce their own warnings or refusals based on
`quality` content (e.g., `completion_rate` too low for the requested
operation); those decisions surface as **policy** errors and reuse the
`policy`-layer categories already defined for the relevant channel or
extension (typically `policy:governance:policy_rejection` at code 201,
with `policy_ref` pointing to the quality-gating policy). Because
`quality` is silently ignorable, a non-supporting receiver never
reaches this path; the policy error is raised only by a receiver that
declared `quality` and chose to gate on its values.

This extension is deliberately **error-free at the protocol layer**.

---

## 8. Anti-Patterns and Mitigations

### 8.1 Quality Forgery

**Pattern.** An issuer self-publishes inflated metrics
(`completion_rate = 0.99`) to game discovery and matching.

**Mitigation.** All metrics carry `evaluated_by`. Receivers MAY
require that `evaluated_by` match `agent_did` (self-report) or that
`external_validation_count > 0` for high-stakes use. Trust score
adjustments at the receiver's policy engine are the operational
defence.

### 8.2 Quality Drift

**Pattern.** Stale metrics linger long after the underlying behavior
has changed (e.g., model degradation, dataset drift), but the
envelope keeps citing old high numbers.

**Mitigation.** `evaluated_at` lets receivers detect stale metrics
and discount them. Receivers SHOULD ignore metrics older than a
policy-defined freshness window for high-stakes decisions.

### 8.3 Metrics Gaming via Tiny Samples

**Pattern.** An issuer reports `applied_count = 3,
completion_rate = 1.0`. Statistically meaningless but looks great.

**Mitigation.** `profile.sample_size_indicator` and `applied_count`
let receivers apply a minimum-sample threshold. Receivers SHOULD
also weigh `external_validation_count` more heavily than
`self_assessed_confidence` for low-`applied_count` artifacts.

### 8.4 Soft Acceptance Misused as Trust

**Pattern.** A receiver treats the **presence** of a `quality`
block as evidence of quality, regardless of the values inside.

**Mitigation.** Receivers' policy engines MUST evaluate the
*values*, not just presence. Conformance tests QLT-04 (see §9)
exercise this exact failure mode.

---

## 9. Conformance Tests

The `quality` extension contributes the following cases to the
conformance suite (anchored in core Appendix B and channels-general
§13):

| Case   | Subject                                                                                                       |
|--------|---------------------------------------------------------------------------------------------------------------|
| QLT-01 | Envelope with `quality` and a receiver NOT declaring `quality` is accepted (no `protocol:extension:unknown_extension`, 105).                    |
| QLT-02 | Envelope with `quality` and a receiver declaring `quality` is accepted; metrics MAY be surfaced to policy.    |
| QLT-03 | Envelope with `evaluation_window_seconds` ≤ 0 OR `evaluated_at` in the future is rejected at sender egress.   |
| QLT-04 | A receiver that gates on `completion_rate ≥ 0.9` rejects an envelope reporting `completion_rate = 0.5` with a policy error (`policy:governance:policy_rejection`, 201, with `policy_ref` set), not a protocol error. |
| QLT-05 | Envelope with `metrics.completion_rate + metrics.fallback_rate > 1.0` SHOULD warn at sender egress; receiver MAY accept but mark the envelope's trust posture downward. |

---

## 10. Interaction with Other Mechanisms

### 10.1 Interaction with Billing (Pay-Per-Result)

Quality metrics can serve as inputs to `pay-per-result` settlement:
the payment layer may require
`quality.metrics.completion_rate > 0.9` before releasing escrowed
funds. This is a payment-layer concern (XIFT phase 3, see
`xift-1.0-spec-channels-general.md` §11); XIFT carries the metrics,
the payment layer interprets them against its own thresholds.

### 10.2 Interaction with Channel 5 (SDR) and Channel 6 (SIEA)

When `quality` is part of an envelope returned by SDR or referenced
by a SIEA announcement, the querier or subscriber MAY use the
metrics as additional scoring inputs alongside `composite_score`.
The scoring JDM (channel-5 §3.7) is the authoritative scorer; XIFT
does not redefine the score breakdown to include `quality`.

### 10.3 Interaction with `provenance`

`quality` is artifact-level; `provenance.derivation_method_hash`
identifies the method that produced the artifact. A receiver can
correlate the two: artifacts derived from the same
`derivation_method_hash` should accumulate consistent quality
metrics. Significant drift between same-method artifacts is a
signal worth monitoring.

---

## 11. Open Questions

1. **External validator endorsements format.** v1.0 lists
   `external_validators` as DIDs only. Should XIFT specify a signed
   endorsement object (`validator_did + endorsed_envelope_id +
   endorsed_at + validator_signature`) that travels separately or
   inline?

2. **Per-task-category metrics.** Some artifacts perform well on one
   category and poorly on another. Should `metrics` become an array
   keyed by `task_category`, or stay aggregate?

3. **Quality decay function.** Receivers ignore stale metrics by
   policy. Should XIFT publish a recommended decay function (e.g.,
   half-life by `freshness_days`) for cross-receiver
   comparability?
