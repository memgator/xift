---
title: XIFT 1.0 — Extension `governance`
status: draft (v1.1)
date: 2026-05-24
visibility: public
authors:
  - Memgator architecture working group
related:
  - xift-1.0-spec-core.md (core spec)
  - xift-1.0-spec-channels-general.md (cross-channel conventions)
  - xift-1.0-spec-extension-provenance.md
  - xift-1.0-spec-extension-encryption.md
  - xift-1.0-spec-extension-revocation.md
  - xift-1.0-spec-extension-quality.md
  - xift-1.0-spec-channel-2.md (Envelope Handoff)
  - xift-interop-1.0.md
---

# XIFT 1.0 — Extension: `governance`

This document specifies the `governance` envelope extension. Common
envelope conventions (canonical form, mandatory blocks, signature
mechanics, identity layer, error model) are specified in
`xift-1.0-spec-core.md`.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

The `governance` extension adds consent, classification,
purpose-of-use, and access-control metadata to the envelope. It is
REQUIRED for any envelope carrying knowledge subject to regulatory
regimes (GDPR, HIPAA, sector-specific) or to organizational access
policies.

An envelope without the `governance` extension carries no consent
contract and is therefore restricted to `classification = public`
exchanges. Receivers MAY refuse non-`public` envelopes lacking
`governance` with error `policy:governance:policy_rejection` (201).

This extension is one of the **core extensions** (governance,
provenance, encryption, revocation) every conformant implementation
MUST recognise; an agent MAY choose not to *process* it, but
declaring it in `supported_extensions` is the only conformant way
to advertise that processing capability (`xift-1.0-spec-channel-1.md`
§3, §4).

---

## 2. Block Structure

```json
{
  "governance": {
    "owner_did": "did:web:org.example.com:subject:s-12345",
    "agent_role": "clinical-analyst",
    "classification": "sensitive",
    "pii_classification": "personal-identifiable",
    "purpose_of_use": "service-delivery",
    "consent_vc_ref": "https://issuer.example.com/grants/abc123",
    "consent_vc_hash": "sha256:...",
    "consent_until": "2026-05-22T10:00:00Z",
    "lineage_policy": "strict",
    "policy_tags": ["no-share-outside-trust", "audit-required"]
  }
}
```

---

## 3. Fields

### 3.1 `owner_did` (Optional)

The DID of the subject whose data is being exchanged. Any
W3C-compliant DID method is accepted. XIFT does not verify
`owner_did` existence or issuer authority; that verification is the
receiver's policy responsibility.

When omitted, the receiver MAY interpret as "artifact owned by the
emitting agent itself" or reject per its policy.

### 3.2 `agent_role` (Optional)

The declared role of the emitting agent, enabling RBAC-style policy
shortcuts in the receiver's engine. Example values:

- `analyst`, `researcher`, `auditor`, `operator`, `supervisor`

`agent_role` is cryptographically bound by the envelope signature.
Receivers MAY use it as a first-pass filter before evaluating
fine-grained ABAC attributes. XIFT does not define a canonical role
taxonomy; role values are agreed between participants or within a
trust domain. The receiver's policy engine is the authority on
whether a declared role is accepted.

Rationale: NIST SP 800-207A recommends identity-tier policies
carrying sufficient context (action, verb, resource, role) for
real segmentation. Pure ABAC covers every case but RBAC shortcuts
simplify administration when trust domains pre-agree on roles.

### 3.3 `classification` (Required when `governance` present)

Sensitivity level declared by the issuer. Values are
**domain-agnostic information security levels**:

| Value           | Meaning                                                                                      |
|-----------------|----------------------------------------------------------------------------------------------|
| `public`        | No access restriction.                                                                       |
| `internal`      | Organization-internal, no special handling.                                                  |
| `confidential`  | Limited distribution. Access on need-to-know basis.                                          |
| `sensitive`     | Heightened protection required. Encryption MUST be applied (see core §3.2).                  |
| `restricted`    | Highest restriction; explicit per-action authorization required. Encryption MUST be applied. |

Trade-secret, intellectual-property, and competitive-advantage
content does not have a dedicated value: depending on the use case,
issuers map it to `confidential` (limited distribution),
`sensitive` (heightened protection with mandatory encryption), or
`restricted` (per-action authorisation).

Domain-specific examples (informative, not canonical):

- Healthcare patient data → typically maps to `sensitive` or
  `restricted`.
- Financial PII (PCI/SOX) → typically maps to `sensitive`.
- Research preprints → typically maps to `confidential`.
- Open-source agent logs → typically maps to `public` or `internal`.

Reference adapters (in `xift-interop-1.0.md`) map external
labelling systems (e.g., Microsoft Purview sensitivity labels,
Google DLP info types, AWS Macie classifications) to these
domain-agnostic levels.

Receivers MAY apply ordinal comparisons in policies. The canonical
ordering, from least to most restrictive, is:

```
public < internal < confidential < sensitive < restricted
```

Policy engines comparing by ordinal MUST use this exact sequence.

### 3.4 `pii_classification` (Optional, fail-safe default)

Identifiability state, orthogonal to sensitivity. Optional in the
wire form but with a normative fail-safe default at acceptance: when
absent, the receiver MUST treat it as `personal-identifiable`.

| Value                    | Meaning                                                     |
|--------------------------|-------------------------------------------------------------|
| `personal-identifiable`  | Identifies a natural person directly.                       |
| `pseudonymized`          | Identifiers tokenized; re-identification possible.          |
| `anonymized`             | Irreversible de-identification; not personal data per GDPR. |
| `non-personal`           | No personal data involved.                                  |

When absent but `governance` is present, the receiver MUST default
to `personal-identifiable` (fail-safe).

The distinction between `pseudonymized` and `anonymized` follows
GDPR Article 4(5) and the Austrian DPA precedent
(DSB-D123.270/0009-DSB/2018), refined by the CJEU SRB ruling (2023).
Implementations MUST treat `pseudonymized` data as personal under
GDPR Article 17 (right to erasure).

### 3.5 `purpose_of_use` (Required when `governance` present)

Declared purpose for which the recipient is authorized to use the
artifact. Values are domain-agnostic:

| Value              | Meaning                                                     |
|--------------------|-------------------------------------------------------------|
| `service-delivery` | Direct service to end-user or system consumer.              |
| `operations`       | Internal operations of the receiving organization.          |
| `research`         | De-identified research; SHOULD require `anonymized` data.   |
| `audit`            | Regulatory or internal audit.                               |
| `training`         | Model training; requires additional consent.                |
| `debugging`        | Engineering debug only; ephemeral, no persistence.          |
| `marketing`        | Analytics or marketing; requires explicit consent.          |

Domain-specific purpose codes (e.g., HL7 Purpose of Use for clinical
contexts) are mapped via reference adapters, not canonical in XIFT.

`purpose_of_use` is cryptographically bound by the envelope
signature. Misuse by the receiver is detectable via audit (core
§16.3) but not preventable by the protocol.

### 3.6 `consent_vc_ref` and `consent_vc_hash` (Optional)

Reference to a Verifiable Credential authorizing this exchange.
`consent_vc_ref` is an absolute HTTPS URL (RFC 3986 URI with
`https` scheme; JSON-schema `format: "uri"`) where the VC can be
fetched; `consent_vc_hash` is the SHA-256 of the VC's canonical
form, in the prefixed-hex form `sha256:<hex>` (core §3.3.3). Both
are OPTIONAL; when one is present the other MUST also be present.

The grant minimally contains: issuer, subject (matching
`recipient_did`), scope, declared `purpose_of_use`, `valid_from`,
`valid_until`, and a status list reference (if `revocation`
extension is in use).

### 3.7 `consent_until` (Required)

RFC3339 UTC timestamp at which the recipient's authorization expires.
After this timestamp:

- The receiver MUST NOT use the artifact for any operation.
- The receiver MUST attempt to destroy the artifact. In distributed
  systems complete destruction may not be guaranteed, but the
  obligation to attempt it is normative. Receivers SHOULD log the
  destruction attempt and its outcome.
- The receiver SHOULD log the consent-expiration event in its audit
  trail.

`consent_until` is the legally meaningful boundary of consent.

### 3.8 `lineage_policy` (Optional)

Declares revocation cascade behaviour. Defaults are conditional on
`pii_classification` (see Rules below).

| Value     | Meaning                                                       |
|-----------|---------------------------------------------------------------|
| `lax`     | Derivatives are sovereign; parent revocation does not cascade.|
| `strict`  | Derivatives inherit revocation; parent revocation cascades.   |

Rules:

- If `pii_classification ∈ {personal-identifiable, pseudonymized}`,
  `lineage_policy` defaults to `strict` and MUST NOT be downgraded
  to `lax` (error `protocol:lineage:lineage_policy_inconsistent`, 105).
- If `pii_classification ∈ {anonymized, non-personal}`, default is
  `lax`. The issuer MAY override to `strict`.
- The legally valid transition from `strict` to `lax` is via
  anonymization evidence (core §9.4).

### 3.9 `policy_tags`

Free-form array of strings consumed by the receiver's policy engine.
Emerging conventions:

- `no-share-outside-trust`
- `audit-required`
- `redact-on-promotion`
- `model-training-prohibited`

These are policy inputs, not protocol directives. Maximum
`policy_tags_count_max` per envelope (core §10).

### 3.10 `native_labels` (Optional)

Preserves the **source labelling system's** sensitivity labels verbatim,
alongside the mapped ordinal `classification` (§3.3). It exists for
round-trip fidelity and native-scheme policy; it never replaces the
ordinal. The value is an **array of scheme-scoped records** and is
**opaque to XIFT**: the protocol preserves and round-trips it but does
not parse it for any protocol decision (per ADR-XIFT-GOVERNANCE-LABELS-001).

The shape generalises how the two dominant systems model labels —
Microsoft Purview (MIP label metadata: a per-tenant label GUID/`SiteId`
plus key/value attributes) and Google Sensitive Data Protection
(`infoType.name` plus `sensitivityScore`) — neither of which is a rigid
root→leaf path.

```json
"native_labels": [
  {
    "scheme": "ms-purview",
    "scheme_version": "2026-01",
    "authority": "did:web:contoso.com",
    "tenant_ref": "cb46c030-1825-4e81-a295-151c039dbf02",
    "labels": [
      {
        "id": "2096f6a2-d2f7-48be-b329-b73aaa526e5d",
        "name": "Confidential",
        "parents": ["8c1e6a4b-..."],
        "score": { "system": "priority", "value": "75" },
        "attributes": { "SetDate": "2018-11-08T21:13:16-0800", "Method": "Privileged" }
      }
    ]
  }
]
```

Scheme record:

| Field            | Type   | Required | Description                                                                                                  |
|------------------|--------|----------|--------------------------------------------------------------------------------------------------------------|
| `scheme`         | string | yes      | Identifier of the source labelling system. **Open string** (NOT a closed enum). Recommended: `ms-purview`, `google-dlp`, `aws-macie`; org-specific schemes MAY use a URI. |
| `scheme_version` | string | no       | Scheme/version qualifier.                                                                                    |
| `authority`      | string | no       | DID/URI of the entity that owns the scheme or tenant.                                                        |
| `tenant_ref`     | string | no       | Tenant/project scope within the scheme (Purview `SiteId`, GCP project): the stable home of the `id` namespace. |
| `labels`         | array  | yes      | Label records (below). MAY be the empty array `[]`.                                                          |

Label record (every field except `id` is OPTIONAL; a foreign-tenant label
may arrive as a bare `id`):

| Field        | Type            | Required | Description                                                                                                       |
|--------------|-----------------|----------|-------------------------------------------------------------------------------------------------------------------|
| `id`         | string          | yes      | Stable opaque identifier within `scheme`/`tenant_ref` (Purview label GUID, Google `infoType.name`). Authoritative for cross-tenant identity; survives when `name` does not. |
| `name`       | string          | no       | Human display name. **Advisory only**; MAY be absent (Purview shows the GUID, not the name, across tenants).      |
| `parents`    | array of string | no       | `id`s of parent labels/groups — a loose hierarchy, not a forced path.                                             |
| `score`      | object          | no       | Native ordinal/score `{ "system": string, "value": string }`. Preserved verbatim; XIFT does not interpret it.     |
| `attributes` | object          | no       | Free key/value map (`additionalProperties` permitted) carrying source metadata verbatim.                          |

`classification` (§3.3) remains REQUIRED and authoritative for every
protocol-level ordinal comparison and egress check. `native_labels` rules:

- A receiver that does not recognise a `scheme` MUST NOT reject the
  envelope on that basis; it MAY ignore that record. This block is
  **silently ignorable**, like the `quality` extension.
- The mapped `classification` MUST be at least as restrictive as the level
  any present scheme implies. Emitting `native_labels` that imply a stricter
  level than `classification` is an egress failure (§5).
- A receiver that recognises a `scheme` and computes a stricter implied
  level than `classification` MAY reject with
  `policy:governance:native_labels_inconsistent` (201). Fail-safe to the
  stricter interpretation.
- Bounded by `native_labels_count_max` (total label records across schemes)
  and `native_labels_bytes_max` (serialized size of the whole value), core
  §10. Exceeding either is an envelope-validation rejection.
- When `classification ≥ sensitive` and the `encryption` extension is
  present, `native_labels` is carried inside the ciphertext (the labels can
  themselves be disclosive); the ordinal `classification` stays cleartext
  for intermediary policy.

---

## 4. Receiver Behaviour

A receiver that declares `governance` in `supported_extensions`
(`xift-1.0-spec-channel-1.md` §3) MUST:

1. Verify the envelope signature before evaluating any `governance`
   field (the block is signed, but signature verification is the
   prerequisite).
2. Apply `governance` fields as inputs to its policy engine
   (Cedar/Zen in the reference implementation). The receiver MUST
   NOT short-circuit policy evaluation based on a single field.
3. Enforce `consent_until`: the artifact MUST NOT be used after that
   timestamp, and MUST be subject to a destruction attempt
   (§3.7).
4. Enforce `lineage_policy = strict` cascades: derivatives produced
   from a strict-lineage source inherit revocation. The receiver
   MUST propagate revocation through its lifecycle when applicable
   (core §9).
5. Honour `policy_tags` per its own policy engine; XIFT does not
   prescribe semantics beyond the conventions in §3.9.

A receiver MAY refuse an envelope whose `governance` fields cannot
be honoured (insufficient policy support, untrusted role taxonomy,
unrecognised purpose) with the appropriate policy error code
(see §7).

---

## 5. Egress DLP for `governance`

Per core §8.4 (Egress Validation), the sender MUST validate the
`governance` block before emission:

- The sender's policy engine MUST verify the declared
  `classification`, `pii_classification`, `purpose_of_use` and
  `lineage_policy` against the recipient's
  `governance_constraints.accepts_*` declared in the recipient's
  capability advertisement (`xift-1.0-spec-channel-1.md` §4.4).
- The sender MUST NOT emit an envelope whose `governance` exceeds
  the recipient's declared acceptance bounds. Egress failure returns
  error `protocol:egress:egress_validation_failed` (105) and the
  envelope MUST NOT be transmitted.
- The sender MUST verify the `consent_vc_ref` resolves and matches
  `consent_vc_hash` (or accept the operational risk of an unverified
  grant if its own policy permits).
- The sender MUST ensure `consent_until` lies in the future at
  emission time.
- When `native_labels` (§3.10) is present, the sender MUST ensure the
  mapped `classification` is at least as restrictive as the level any
  declared scheme implies; otherwise egress fails
  (`protocol:egress:egress_validation_failed`, 105) and the envelope MUST
  NOT be transmitted. The sender MUST also keep `native_labels` within
  `native_labels_count_max` / `native_labels_bytes_max` (core §10).

---

## 6. Extension Parameters

`governance` reuses the core parameters of `xift-1.0-spec-core.md`
§10, including `policy_tags_count_max` (default 16) and the two
`native_labels` bounds added for §3.10: `native_labels_count_max`
(default 32) and `native_labels_bytes_max` (default 4096). The
defaults live in core §10 and are restated here for locality.

---

## 7. `governance` Error Codes

Per the XIFT error model (core §12, ADR-XIFT-ERROR-MODEL-001), `code`
is the generic operational routing axis and `category` is the source of
domain truth; the subsection heading fixes layer and severity.
`governance` is the primary input to policy evaluation, so it surfaces
mainly `policy`-layer categories alongside a few cross-channel
`protocol` conditions. Categories are registered in
`xift-error-taxonomy.md`; the numeric `code` is drawn from the canonical
per-layer set (core §12.1). Do not mint new numeric codes here.

### 7.1 Policy Errors

| Code | Category                                                  | Description                                             |
|------|-----------------------------------------------------------|---------------------------------------------------------|
| 201  | `policy:governance:policy_rejection`                      | Policy engine explicitly rejected.                      |
| 201  | `policy:governance:purpose_of_use_mismatch`               | Declared purpose not authorized for recipient.          |
| 201  | `policy:governance:classification_too_high`               | Receiver policy rejects this sensitivity level.         |
| 201  | `policy:governance:agent_role_not_recognized`             | Declared `agent_role` not in receiver's taxonomy.       |
| 201  | `policy:governance:native_labels_inconsistent`            | Recognised `native_labels` (§3.10) imply a stricter level than `classification`. |
| 203  | `policy:governance:consent_unsupportable`                 | Receiver cannot honor `consent_until`.                  |
| 204  | `policy:provenance:anonymization_evidence_insufficient`   | Evidence does not satisfy policy.                       |
| 206  | `policy:trust:trust_score_below_threshold`                | Sender trust score below receiver requirement.          |
| 207  | `policy:governance:consent_vc_invalid`                    | VC at `consent_vc_ref` does not validate.               |
| 207  | `policy:governance:consent_vc_hash_mismatch`              | `consent_vc_hash` does not match fetched VC.            |

The shared numeric `code` (e.g. several conditions at `201`) is by
design: routing reads `code`/`layer`/`severity`, while `category` is
the disambiguating domain truth for diagnostics and LLM remediation.

### 7.2 Protocol Errors

`governance` also drives core protocol-layer conditions:

| Code | Category                                       | Description                                                                |
|------|------------------------------------------------|----------------------------------------------------------------------------|
| 105  | `protocol:lineage:lineage_policy_inconsistent` | `lax` declared with PII (downgrade attempt; §3.8).                          |
| 105  | `protocol:revocation:grant_expired`            | `consent_until` has passed.                                                 |
| 105  | `protocol:egress:egress_validation_failed`     | Sender-side egress check (§5) failed pre-emission.                          |

### 7.3 Protocol Warnings

| Code | Category                                     | Description                                       |
|------|----------------------------------------------|---------------------------------------------------|
| 105  | `protocol:revocation:nearing_consent_expiry` | `consent_until` is within 10% of remaining TTL.   |

### 7.4 Policy Warnings

| Code | Category                            | Description                                  |
|------|-------------------------------------|----------------------------------------------|
| 206  | `policy:trust:trust_score_marginal` | Sender trust score near but above threshold. |

---

## 8. Anti-Patterns and Mitigations

### 8.1 Implicit Default Acceptance

**Pattern.** A receiver implements `governance` minimally: it
verifies the block is present and signed, but maps all unknown
`purpose_of_use` and `agent_role` values to "accepted" by default.

**Mitigation.** Receivers MUST default to **reject** on unknown enum
values (purpose, role, classification). The `pii_classification`
default rule (`personal-identifiable` when absent) is the model:
fail-safe to the most restrictive value.

### 8.2 Consent Expiry Drift

**Pattern.** A sender issues envelopes with very long
`consent_until` to avoid renewal traffic. Recipients honour them and
later discover the underlying grant was revoked.

**Mitigation.** The combination of `consent_until` (passive expiry)
and the `revocation` extension (active revocation via BSL) is
designed exactly to defend against this. Senders SHOULD NOT issue
envelopes whose `consent_until` is materially longer than the
issuing grant's `valid_until`.

### 8.3 Policy-Engine Bypass via `policy_tags`

**Pattern.** Receivers treat `policy_tags` as opaque hints and skip
their semantic enforcement.

**Mitigation.** `policy_tags` are policy inputs. Receivers' policy
engines MUST be authored to recognise the agreed conventions
(§3.9) and MUST NOT silently ignore them. Auditable rejection on
unknown tags is preferable to permissive behaviour.

### 8.4 RBAC Lock-in via `agent_role`

**Pattern.** Receivers build their policies around `agent_role`
strings, then break when senders rename or reorganise roles.

**Mitigation.** `agent_role` is a first-pass filter, not the
authoritative attribute. Receivers MUST still evaluate fine-grained
ABAC attributes (classification, pii_classification, purpose_of_use,
consent_vc) for the actual decision.

---

## 9. Conformance Tests

The `governance` extension contributes the following cases to the
conformance suite (anchored in core Appendix B and channels-general
§13):

| Case   | Subject                                                                   |
|--------|---------------------------------------------------------------------------|
| GOV-01 | Envelope with `governance` minimal (`classification + pii + purpose + consent_until`) is accepted by a conformant receiver. |
| GOV-02 | Envelope missing `pii_classification` is treated as `personal-identifiable`. |
| GOV-03 | Envelope with `lineage_policy = lax` AND `pii_classification = personal-identifiable` is rejected with error `protocol:lineage:lineage_policy_inconsistent` (105). |
| GOV-04 | Envelope with expired `consent_until` is rejected with error `protocol:revocation:grant_expired` (105).       |
| GOV-05 | Envelope with `consent_vc_hash` mismatching the fetched VC is rejected with error `policy:governance:consent_vc_hash_mismatch` (207). |
| GOV-06 | Egress validation against recipient's `accepts_classifications` rejects an envelope whose classification exceeds the recipient's bounds, with error `protocol:egress:egress_validation_failed` (105). |
| GOV-07 | A `governance` block present without `classification`, `pii_classification`, or `purpose_of_use` is rejected at envelope validation. |
| GOV-08 | Envelope with multi-scheme `native_labels` (§3.10) is accepted; a scheme-aware receiver surfaces the records, and a label whose `name` is absent is still identified by its `id`. |
| GOV-09 | Envelope with a `native_labels` record whose `scheme` is unknown to the receiver is accepted (silently ignorable); the receiver MUST NOT raise `protocol:extension:unknown_extension` (105). |
| GOV-10 | A receiver that recognises a `scheme` and computes a stricter implied level than `classification` rejects with `policy:governance:native_labels_inconsistent` (201). |
| GOV-11 | Envelope whose `native_labels` exceeds `native_labels_count_max` or `native_labels_bytes_max` (core §10) is rejected at envelope validation. |

---

## 10. Open Questions

1. **Canonical `agent_role` taxonomy.** The spec leaves `agent_role`
   open. Should XIFT promote a small set of agreed role names
   (analyst, researcher, auditor, operator, supervisor) to
   recommended status, with semantic definitions, to ease cross-org
   federation?

2. **`policy_tags` registry.** Conventions like
   `model-training-prohibited` are de-facto standards. Should
   XIFT publish an informative registry of policy tags with their
   intended semantics, while keeping the field free-form?

3. **`consent_until` for non-PII artifacts.** Required when
   `governance` is present, but artifacts with
   `pii_classification = non-personal` rarely have a legally
   meaningful expiry. Should the field become OPTIONAL in that
   specific case, with a default of "effectively unbounded" (e.g.,
   year 9999)?
