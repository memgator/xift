---
title: XIFT 1.0 — Extension `provenance`
status: draft (v1.0)
date: 2026-05-24
visibility: public
authors:
  - Memgator architecture working group
related:
  - xift-1.0-spec-core.md (core spec)
  - xift-1.0-spec-channels-general.md (cross-channel conventions)
  - xift-1.0-spec-extension-governance.md
  - xift-1.0-spec-extension-encryption.md
  - xift-1.0-spec-extension-revocation.md
  - xift-1.0-spec-extension-quality.md
  - xift-1.0-spec-channel-2.md (Envelope Handoff)
---

# XIFT 1.0 — Extension: `provenance`

This document specifies the `provenance` envelope extension. Common
envelope conventions (canonical form, mandatory blocks, signature
mechanics, identity layer, error model) are specified in
`xift-1.0-spec-core.md`.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

The `provenance` extension carries the **derivation lineage** of a
knowledge artifact: which parent artifacts it was derived from, what
operation produced it, by which agent, when, and (when applicable)
what evidence supports a privacy-state transition.

`provenance` enables three classes of receiver decisions that are
not possible from `governance` alone:

- **Revocation cascade**: when a parent is revoked, derivatives
  with `lineage_policy = strict` must follow (core §9; the cascade
  walks `parent_ids` recursively).
- **Audit and explainability**: a derivative's audit trail leads
  back through `parent_ids` to its sources, with `derivation_type`
  declaring the *kind* of operation performed at each step.
- **Privacy-state attestation**: the `anonymization_evidence` field
  supports the legally meaningful transition from
  `pii_classification = personal-identifiable` to `anonymized`.

This is one of the **core extensions** every conformant
implementation MUST recognise (`xift-1.0-spec-channel-1.md` §3, §4).

---

## 2. Block Structure

```json
{
  "provenance": {
    "parent_ids": ["01HXX5VQ7K9M3J8N2P4R6T8WAY"],
    "derivation_type": "distillation",
    "stratum_in": "episodic",
    "stratum_out": "semantic",
    "derivation_agent_did": "did:key:z6MkhaXg...",
    "derivation_timestamp": "2026-05-21T10:00:00Z",
    "derivation_method_hash": "sha256:...",
    "anonymization_evidence": null
  }
}
```

---

## 3. Fields

| Field                    | Type      | Required | Description                                                                                                  |
|--------------------------|-----------|----------|--------------------------------------------------------------------------------------------------------------|
| `parent_ids`             | array     | yes      | `envelope_id`s of sources, each a Crockford ULID (26 chars, pattern `^[0-9A-HJKMNP-TV-Z]{26}$`). Empty array for leaf artifacts. Max chain depth: `lineage_chain_max` (core §10). |
| `derivation_type`        | enum      | yes      | See §3.1.                                                                                                    |
| `stratum_in`             | enum      | yes      | Source CoALA stratum: `working`, `episodic`, `semantic`, `procedural`.                                       |
| `stratum_out`            | enum      | yes      | Destination CoALA stratum (same enum).                                                                       |
| `derivation_agent_did`   | DID       | yes      | Agent that performed derivation. MAY differ from the envelope's `agent_did`.                                  |
| `derivation_timestamp`   | RFC3339   | yes      | When derivation occurred (UTC, millisecond precision).                                                       |
| `derivation_method_hash` | string    | no       | OPTIONAL. Hash of derivation method/prompt for reproducibility. Prefixed-hex form `sha256:<hex>` (core §3.3.3). |
| `anonymization_evidence` | object    | conditional | REQUIRED when transitioning `pii_classification` from `personal-identifiable`/`pseudonymized` to `anonymized` (core §9.4). |

Note: payload-adjacent metadata (quality metrics, profiling,
confidence scores) is **not** part of `provenance`; it lives in the
`quality` extension (`xift-1.0-spec-extension-quality.md`).

### 3.1 `derivation_type` Values

XIFT v1.0 defines six values. This list is subject to review after
six months of deployment.

| Value                | Meaning                                                                                                                                                                                                                             | Original Values Mapping         |
| :------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------ |
| **`redaction`**      | **Cleanup.** Operations intended to remove or mask sensitive data (PII) to ensure integrity and privacy. Aligned with data minimization principles.                                                                                 | `redaction`                     |
| **`transformation`** | **Reformatting and Correction.** Changes in structure, syntax, or form (e.g., from JSON to plain text) without material content gain/loss or alteration of underlying meaning. Also includes fixing errors without semantic change. | `transformation`, `fix`         |
| **`distillation`**   | **Semantic Compression.** Reduction of informational volume by summarizing key points or extracting abstract principles and patterns from the source material.                                                                      | `summarization`, `distillation` |
| **`augmentation`**   | **Contextual Enrichment.** Improvement of the artifact by adding complementary information or specializing its content for a specific domain or context.                                                                            | `enrichment`, `specialization`  |
| **`synthesis`**      | **Multi-source Fusion.** Merging of multiple parent artifacts (requiring multiple `parent_ids`) into a single record or a statistical combination (aggregations).                                                                   | `consolidation`, `aggregation`  |
| **`extraction`**     | **Direct Inference.** Generation of a new pattern, insight, or knowledge derived directly from the agent's execution, reasoning process, or tool output.                                                                            | `extraction`                    |

`transformation` and `redaction` are distinct: `transformation`
repairs errors or reshapes form without loss of meaning; `redaction`
eliminates sensitive data. They have different regulatory
implications and applicable rules.

### 3.2 `anonymization_evidence` Sub-Object

When `derivation_type = redaction` AND the derivation transitions
`pii_classification` from `personal-identifiable` or `pseudonymized`
to `anonymized`, this sub-object MUST be populated:

```json
{
  "anonymization_evidence": {
    "method": "k-anonymity",
    "method_parameters": { "k": 5 },
    "evaluator_did": "did:web:org.example.com:evaluator:1",
    "evaluation_timestamp": "2026-05-21T09:30:00Z",
    "evaluation_signature": "<base64url-encoded Ed25519 signature>"
  }
}
```

| Field                    | Type    | Required | Description                                                                                                                                                                                                                            |
|--------------------------|---------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `method`                 | enum    | yes      | Anonymization method identifier. Recognised values (extensible): `k-anonymity`, `differential-privacy`, `synthetic-generation`, `aggregation-only`, `llm-distillation-verified`.                                                        |
| `method_parameters`      | object  | yes      | Method-specific parameters. Schema depends on `method` (e.g., `{ "k": 5 }` for `k-anonymity`, `{ "epsilon": 0.5 }` for `differential-privacy`). MAY be the empty object `{}` for parameterless methods (e.g., `aggregation-only`).      |
| `evaluator_did`          | DID     | yes      | DID of the entity that attests the anonymization. The name `evaluator_did` (not `auditor_did`) is chosen to avoid confusion with the audit-log subsystem.                                                                              |
| `evaluation_timestamp`   | RFC3339 | no       | When the evaluation was performed (UTC, millisecond precision). RECOMMENDED for regulatory audit trails; MAY be omitted in batch-attestation flows.                                                                                   |
| `evaluation_signature`   | string  | yes      | Ed25519 signature by `evaluator_did`'s signing key over the JCS-canonical form of `{envelope_id, method, method_parameters, evaluator_did, evaluation_timestamp?}`. Base64url-encoded per core §8.3 (NOT the prefixed-hex hash form). |

The signed payload omits any field absent at emission time (JCS
rules); receivers MUST reconstruct the canonical form from the
fields actually present in `anonymization_evidence` to verify the
signature.

> **Why a signature and not a bare hash.** A SHA-256 hash would
> establish integrity but not authentication: anyone could recompute
> it over forged contents. The signature binds the attestation to
> `evaluator_did` non-repudiably, using the same Ed25519 + JCS
> construction as the envelope signature (core §8.3). No new
> cryptographic primitive is introduced.

> **Self-attestation case.** When `evaluator_did == agent_did`, the
> envelope-level signature already covers this block. Issuers MUST
> still populate `evaluation_signature` (using the same key) for
> schema uniformity; receivers MAY short-circuit verification in
> this case as an optimisation.

The evaluator-trust criteria for `anonymization_evidence` are
specified in core §9.4. Insufficient or rejected evidence yields
error `policy:provenance:anonymization_evidence_insufficient` (204).

---

## 4. Receiver Behaviour

A receiver that declares `provenance` in `supported_extensions` MUST:

1. Verify the envelope signature before evaluating any `provenance`
   field.
2. Reject envelopes whose `parent_ids` chain (recursively resolved
   against artifacts the receiver already holds) exceeds
   `lineage_chain_max` (core §10), with error
   `protocol:lineage:lineage_chain_too_deep` (108).
3. For each `parent_id`, the receiver MAY pull the parent (if not
   already held) to validate the chain. The receiver MUST NOT
   silently accept unresolvable parents in `strict` lineage chains.
4. Honour the `lineage_policy = strict` cascade: revocation of a
   parent (signalled via Channel 3 or Channel 4) MUST trigger
   revocation of all `strict`-policy derivatives.
5. When `anonymization_evidence` is present, evaluate it against the
   receiver's anonymization-trust policy (core §9.4). Failure yields
   error `policy:provenance:anonymization_evidence_insufficient` (204).
6. Persist `provenance` alongside the artifact for the receiver's
   audit trail.

A receiver MAY refuse an envelope whose `provenance` does not
satisfy its policy (unknown `derivation_type`, untrusted
`derivation_agent_did`, missing `derivation_method_hash` when
required) with the appropriate policy error.

---

## 5. Egress DLP for `provenance`

Per core §8.4, the sender MUST validate `provenance` before
emission:

- The sender MUST ensure `parent_ids` chain does not exceed
  `lineage_chain_max` in its own lineage graph.
- The sender MUST NOT downgrade `lineage_policy` from `strict` to
  `lax` when `pii_classification ∈ {personal-identifiable,
  pseudonymized}` (error `protocol:lineage:lineage_policy_inconsistent`,
  105, enforced via `governance` §3.8).
- When emitting an anonymization step, the sender MUST attach
  `anonymization_evidence` (§3.2). Emitting an envelope that
  transitions to `anonymized` without evidence is an egress failure
  (error `protocol:egress:egress_validation_failed`, 105).

---

## 6. Extension Parameters

| Parameter             | Default | Layer      | Purpose                                  |
|-----------------------|---------|------------|------------------------------------------|
| `lineage_chain_max`   | 10      | Provenance | Max recursive depth of `parent_ids`.     |

The default lives in core §10 and is restated here for locality.

---

## 7. `provenance` Error Codes

Per the XIFT error model (core §12, ADR-XIFT-ERROR-MODEL-001), `code`
is the generic operational routing axis and `category` is the source of
domain truth; the subsection heading fixes layer and severity.
`provenance` reuses these categories registered in
`xift-error-taxonomy.md`:

### 7.1 Protocol Errors

| Code | Category                                       | Description                                  |
|------|------------------------------------------------|----------------------------------------------|
| 105  | `protocol:lineage:lineage_policy_inconsistent` | `lax` declared with PII (downgrade attempt). |
| 108  | `protocol:lineage:lineage_chain_too_deep`      | `parent_ids` chain exceeds `lineage_chain_max`. |

### 7.2 Policy Errors

| Code | Category                                                | Description                                       |
|------|---------------------------------------------------------|---------------------------------------------------|
| 204  | `policy:provenance:anonymization_evidence_insufficient` | `anonymization_evidence` does not satisfy policy. |

### 7.3 Protocol Warnings

| Code | Category                              | Description                                      |
|------|---------------------------------------|--------------------------------------------------|
| 108  | `protocol:lineage:large_lineage_chain`| `parent_ids` chain > 80% of `lineage_chain_max`. |

No `provenance`-specific numeric codes are added by this
specification.

---

## 8. Anti-Patterns and Mitigations

### 8.1 Orphan Lineage Claims

**Pattern.** An issuer emits an envelope citing `parent_ids` that
the receiver cannot resolve (because the issuer is unwilling to
share the parents, or because they were never persisted).

**Mitigation.** Receivers operating under `strict` lineage MUST
reject artifacts with unresolvable parents (refusing to accept
lineage they cannot audit). Receivers operating under `lax` lineage
MAY accept the artifact but MUST mark the lineage chain
"unresolved" in their audit trail; they MUST NOT silently treat the
chain as if it had been verified.

### 8.2 Cascade Storm

**Pattern.** A single revocation at a high-level source cascades to
a very large derivative tree, producing a notification storm and
mass invalidation of receiver caches.

**Mitigation.** Receivers MUST handle cascade revocation
asynchronously and MUST rate-limit the resulting Channel 4 traffic
per `rate_limit_envelopes_per_minute_per_did`. Issuers SHOULD
avoid revoking high-fan-out grants atomically; gradual revocation
windows are recommended for grants with > 100 known derivatives.

### 8.3 Anonymization Theatre

**Pattern.** A `redaction` step claims `anonymization_evidence`
but the evidence is weak (e.g., `k-anonymity` with k=2 on a small
dataset) and re-identification remains feasible.

**Mitigation.** Receivers' anonymization-trust policies MUST set
minimum thresholds for accepted methods and parameters; envelopes
with weak evidence are rejected with error
`policy:provenance:anonymization_evidence_insufficient` (204). The receiver's
threshold is policy-specified, not protocol-specified.

### 8.4 Method-Hash Stripping

**Pattern.** Issuers omit `derivation_method_hash` to obscure the
provenance audit trail of distillation/extraction operations.

**Mitigation.** The field is OPTIONAL by the spec, but receivers
MAY require it in their policy for `derivation_type ∈ {distillation,
extraction, synthesis}`. Issuers operating under audit obligations
SHOULD always populate it.

---

## 9. Conformance Tests

The `provenance` extension contributes the following cases to the
conformance suite (anchored in core Appendix B and channels-general
§13):

| Case   | Subject                                                                                                       |
|--------|---------------------------------------------------------------------------------------------------------------|
| PRO-01 | Envelope with `provenance` and empty `parent_ids` (leaf) is accepted.                                          |
| PRO-02 | Envelope with `parent_ids` chain depth > `lineage_chain_max` is rejected with error `protocol:lineage:lineage_chain_too_deep` (108).                       |
| PRO-03 | Envelope transitioning `pii_classification` to `anonymized` without `anonymization_evidence` is rejected (`protocol:egress:egress_validation_failed`, 105, at sender or `policy:provenance:anonymization_evidence_insufficient`, 204, at receiver). |
| PRO-04 | Each of the six `derivation_type` values is accepted by a conformant receiver.                                |
| PRO-05 | Cascade revocation of a `strict`-lineage parent propagates to derivatives held by the receiver.                |
| PRO-06 | `lineage_policy = lax` on an envelope with PII (`personal-identifiable` or `pseudonymized`) is rejected with error `protocol:lineage:lineage_policy_inconsistent` (105). |

---

## 10. Open Questions

1. **Cross-issuer lineage trust.** When `parent_ids` reference
   artifacts from a different issuer, what is the conformant way to
   evaluate the chain? Currently each receiver decides per policy.
   Should XIFT specify a minimum trust-evaluation contract?

2. **`derivation_method_hash` registry.** Different organisations
   hash different inputs (prompt + model + sampling params + tools
   used + …). Should XIFT publish an informative recipe for what
   goes into `derivation_method_hash`?

3. **`derivation_type` extensibility.** Six values cover common
   cases. Is there a clean extension point for domain-specific types
   (e.g., `medical_synthesis`, `legal_redaction`) without polluting
   the canonical enum?
