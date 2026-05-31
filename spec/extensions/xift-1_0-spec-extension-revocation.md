---
title: XIFT 1.0 — Extension `revocation`
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
  - xift-1.0-spec-extension-quality.md
  - xift-1.0-spec-channel-3.md (Status Verification — BSL pull)
  - xift-1.0-spec-channel-4.md (Change Notification — revocation push)
  - xift-custodian-1.0.md (Trust Custodian; BSL aggregation)
---

# XIFT 1.0 — Extension: `revocation`

This document specifies the `revocation` envelope extension. Common
envelope conventions (canonical form, mandatory blocks, signature
mechanics, identity layer, error model) are specified in
`xift-1.0-spec-core.md`. The wire flow for BSL pull is specified in
`xift-1.0-spec-channel-3.md`; the wire flow for revocation push is
specified in `xift-1.0-spec-channel-4.md`.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

The `revocation` extension declares that a knowledge artifact's
authorisation is subject to **active revocation** via a W3C
Bitstring Status List v1.0 (BSL, May 2025 Recommendation), in
addition to the passive TTL check from `consent_until`
(`xift-1.0-spec-extension-governance.md` §3.7).

Two-layer revocation:

- **Passive (TTL)**: `consent_until` expires; the receiver MUST
  stop using the artifact regardless of BSL state.
- **Active (BSL)**: the issuer flips a bit in its BSL; receivers
  with cached or held artifacts pointing at that bit must stop
  using them immediately.

`revocation` is what enables credential-revocation cascades through
lineage (`xift-1.0-spec-extension-provenance.md` §4) when
`lineage_policy = strict`.

This is one of the **core extensions** every conformant
implementation MUST recognise (`xift-1.0-spec-channel-1.md` §3, §4).

---

## 2. Block Structure

```json
{
  "revocation": {
    "status_list_url": "https://issuer.example.com/bsl/list-2026-05",
    "status_list_index": 47291,
    "status_list_hash": "sha256:...",
    "max_staleness_seconds": 300
  }
}
```

---

## 3. Fields

| Field                    | Type    | Required | Description                                                                                                  |
|--------------------------|---------|----------|--------------------------------------------------------------------------------------------------------------|
| `status_list_url`        | URL     | yes      | The BSL Verifiable Credential's URL. Receivers MAY use a Custodian-aggregated URL instead (`xift-custodian-1.0.md` §5). |
| `status_list_index`      | integer | yes      | The bit index assigned to this artifact's grant. Less than the BSL's length.                                  |
| `status_list_hash`       | string  | yes      | SHA-256 of the BSL credential at issuance time, prefixed-hex form `sha256:<hex>` (core §3.3.3). Detects rotation/replacement at the host. |
| `max_staleness_seconds`  | integer | no       | Per-artifact cap on BSL cache age, tightening (but never relaxing) `bsl_max_staleness_seconds` (core §10).     |

When `max_staleness_seconds` is omitted, the receiver applies
`bsl_max_staleness_seconds` (default 300 s, core §10).

---

## 4. Receiver Behaviour

When the `revocation` extension is present:

1. Fetch the BSL at `status_list_url` per the Channel 3 flow
   (`xift-1.0-spec-channel-3.md` §4), honouring HTTP cache headers
   but not exceeding the effective staleness window (the smaller of
   `max_staleness_seconds` and `bsl_max_staleness_seconds`).
2. Verify the BSL's own signature; BSLs are Verifiable Credentials
   signed by the issuer.
3. Verify the BSL hash against `status_list_hash`; mismatch is error
   `protocol:channel3:bsl_hash_mismatch` (102).
4. Read the bit at `status_list_index`. If 1, the grant is revoked;
   reject with error `protocol:revocation:grant_revoked` (105).
5. If the BSL is unreachable AND the cached entry exceeded the
   effective staleness window, fail closed: reject with error
   `protocol:channel3:status_list_unavailable` (106).
6. If a Channel 4 (`xift-1.0-spec-channel-4.md`) push notification
   for `status_list_url` arrives between pulls, invalidate the
   receiver's cached entry for that URL and re-fetch on next use.

Receivers MUST persist the artifact's BSL reference for the cascade
discipline of `lineage_policy = strict`: when a parent is revoked,
strict-lineage derivatives MUST also be considered revoked.

---

## 5. Hosting

By default the issuer hosts its own BSL. Custodian-mediated hosting
is specified in `xift-custodian-1.0.md` §5 and becomes mandatory at
the mesh sizes declared in core §10
(`mesh_custodian_activation_threshold = 25`).

The host serving the BSL — whether the issuer or a Custodian — is
referenced in the wire by `status_list_url`. The Trust Score of
that host gates whether a receiver consumes the BSL at all
(channel-3 §9.3, error `policy:channel3:bsl_host_trust_too_low`, 206).

---

## 6. Herd Privacy

The BSL pull flow preserves **herd privacy**: receivers download the
entire bitstring, not a per-grant query, so the BSL host cannot
infer which grant the receiver is checking
(`xift-1.0-spec-channel-3.md` §7).

XIFT enforces the W3C BSL minimum length of `bsl_min_length_bits =
131072` bits (core §10). BSLs shorter than that break herd privacy
and MUST be rejected with error `protocol:channel3:bsl_too_short` (105).

Receivers MUST NOT log the specific `status_list_index` they queried
beyond what is needed for their own audit trail. Custodians serving
BSLs MUST NOT log per-receiver index access.

---

## 7. Egress DLP for `revocation`

Per core §8.4, the sender MUST:

- Verify the BSL at `status_list_url` is reachable at emission time;
  emitting an envelope whose BSL is already unreachable is an egress
  failure (error `protocol:egress:egress_validation_failed`, 105).
- Verify the BSL's signature; do not emit envelopes pointing at an
  invalid BSL.
- Ensure `status_list_index` is within the BSL's length.
- Compute the BSL hash and bind it as `status_list_hash`. The sender
  MUST NOT emit with a stale hash if it knows the BSL has rotated.

---

## 8. Extension Parameters

| Parameter                                 | Default | Layer      | Purpose                                                                |
|-------------------------------------------|---------|------------|------------------------------------------------------------------------|
| `bsl_min_length_bits`                     | 131072  | Revocation | W3C BSL minimum length for herd privacy.                                |
| `bsl_max_staleness_seconds`               | 300     | Revocation | Maximum cache age of a fetched BSL.                                     |
| `mesh_custodian_activation_threshold`     | 25      | Mesh       | Agent count at which Custodian-eligible agents MUST activate BSL aggregation. |
| `mesh_custodian_deactivation_threshold`   | 15      | Mesh       | Deactivation threshold; hysteresis with the activation threshold to prevent flapping. |
| `mesh_p2p_hard_limit`                     | 50      | Mesh       | Hard limit on direct (non-aggregated) BSL hosting at the issuer.        |

All defaults live in core §10 and are restated here for locality.

---

## 9. `revocation` Error Codes

Per the XIFT error model (core §12, ADR-XIFT-ERROR-MODEL-001), `code`
is the generic operational routing axis and `category` is the source of
domain truth; the subsection heading fixes layer and severity.
`revocation` reuses these `protocol`-layer error categories registered
in `xift-error-taxonomy.md`:

| Code | Category                                  | Description                                                          |
|------|-------------------------------------------|----------------------------------------------------------------------|
| 106  | `protocol:channel3:status_list_unavailable`| BSL fetch failed; cache exceeded staleness. Fail-closed.            |
| 105  | `protocol:revocation:grant_revoked`       | BSL bit set; grant actively revoked.                                 |
| 105  | `protocol:revocation:grant_expired`       | `consent_until` has passed (interacts with passive revocation).      |

`revocation` operations also surface the Channel-3-specific conditions —
including the BSL cache freshness warning
**`protocol:channel3:bsl_cache_near_expiry` (106, warning)** at 80 % of
the staleness window — defined in `xift-1.0-spec-channel-3.md` §9 (the
`protocol:channel3:*` and `policy:channel3:bsl_host_trust_too_low`
categories), plus the Channel-4-specific conditions for push
notifications defined in `xift-1.0-spec-channel-4.md` §11 (the
`protocol:channel4:*` and `policy:channel4:*` categories).

This extension does not register independent warnings. The BSL
freshness warning previously catalogued here as
`bsl_staleness_approaching` is superseded by
`protocol:channel3:bsl_cache_near_expiry` (106, warning) in the
Channel-3 catalogue and retired.

---

## 10. Anti-Patterns and Mitigations

### 10.1 Cache Poisoning via Stale BSL

**Pattern.** A receiver accepts a stale BSL that does not reflect a
recent revocation, continuing to use an already-revoked artifact.

**Mitigation.** Fail-closed (§4 step 5) is the protocol-level
defence. Receivers MUST NOT extend `bsl_max_staleness_seconds`
beyond the core default without explicit ADR documentation. Channel
4 push notifications complement Channel 3 pulls; receivers SHOULD
subscribe to Channel 4 wherever feasible.

### 10.2 BSL Rotation Without Hash Update

**Pattern.** An issuer rotates its BSL URL without updating the
artifact's `status_list_hash`, leaving a receiver checking the wrong
list.

**Mitigation.** Receivers MUST verify the BSL hash against
`status_list_hash` on every fetch (§4 step 3, error
`protocol:channel3:bsl_hash_mismatch`, 102). The hash
binding is what defends against silent rotation.

### 10.3 BSL Length Below Herd Privacy Floor

**Pattern.** A small issuer publishes a BSL with only a few
thousand bits to save bandwidth, breaking herd privacy.

**Mitigation.** Hard rejection with error
`protocol:channel3:bsl_too_short` (105) at the receiver
(§6). Issuers MUST pad their BSL to `bsl_min_length_bits` (131,072
by default).

### 10.4 Custodian Trust Drift

**Pattern.** A receiver consumes BSLs from a Custodian whose trust
score has dropped below the receiver's threshold, accepting
potentially poisoned aggregations.

**Mitigation.** Receivers MUST verify Custodian trust score at each
fetch (channel-3 §8); below threshold yields error
`policy:channel3:bsl_host_trust_too_low` (206). In
practice, receivers cache the Custodian's trust score per
`identity_handshake_cache_ttl_seconds`.

### 10.5 Cascade Storm on Mass Revocation

**Pattern.** An issuer revokes a high-fan-out grant atomically; the
cascade through `strict`-lineage derivatives produces a Channel 4
notification storm and overwhelms subscribers.

**Mitigation.** Issuers SHOULD avoid revoking high-fan-out grants
atomically; gradual revocation windows are RECOMMENDED for grants
with > 100 known derivatives. Receivers MUST rate-limit per
`rate_limit_envelopes_per_minute_per_did` to absorb the storm.

---

## 11. Conformance Tests

The `revocation` extension contributes the following cases to the
conformance suite (anchored in core Appendix B and channels-general
§13):

| Case   | Subject                                                                                                       |
|--------|---------------------------------------------------------------------------------------------------------------|
| REV-01 | Envelope with `revocation` and BSL bit = 0 is accepted by a conformant receiver.                              |
| REV-02 | Envelope with BSL bit = 1 is rejected with error `protocol:revocation:grant_revoked` (105).                                                        |
| REV-03 | Envelope whose BSL is unreachable AND cache exceeded staleness is rejected with error `protocol:channel3:status_list_unavailable` (106).                    |
| REV-04 | BSL shorter than `bsl_min_length_bits` is rejected with error `protocol:channel3:bsl_too_short` (105).                                            |
| REV-05 | BSL hash mismatch against `status_list_hash` is rejected with error `protocol:channel3:bsl_hash_mismatch` (102).                                      |
| REV-06 | Channel 4 push of a `revocation` event invalidates the receiver's BSL cache for `status_list_url`.             |
| REV-07 | Cascade revocation propagates from a `strict`-lineage parent to its derivatives held by the receiver.          |

---

## 12. Open Questions

1. **Per-recipient BSL bit allocation.** v1.0 assumes a single bit
   per grant. Some deployments want per-recipient bits to revoke
   selectively. Should XIFT specify a "BSL with multiplexed bit
   addressing" extension, or is that out of scope?

2. **Federation of Custodian BSL aggregators.** When multiple
   Custodians serve overlapping issuers, how do consumers pick the
   freshest BSL? Currently the choice is policy-level.

3. **Two-bit status (revoked vs suspended).** The W3C BSL spec
   supports multi-bit statuses (suspended/revoked/etc.). XIFT v1.0
   uses one bit only. Worth specifying a "suspended" status that
   blocks use but is reversible?
