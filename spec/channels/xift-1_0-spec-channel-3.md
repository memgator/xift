---
title: "XIFT 1.0 — Channel 3: Status Verification (BSL Pull)"
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
  - xift-1.0-spec-channel-4.md
  - xift-1.0-spec-channel-5.md
  - xift-1.0-spec-channel-6.md
  - xift-1.0-spec-channel-7.md
  - xift-custodian-1.0.md
  - xift-interop-1.0.md
---

# XIFT 1.0 — Channel 3: Status Verification (BSL Pull)

Common conventions (transport, authentication, back-pressure,
identity handshake primitive, reserved error code ranges) are
specified in `xift-1.0-spec-channels-general.md`. This document
specifies Channel 3 normative content.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

Channel 3 is the **synchronous revocation check**: a receiver pulls
a Bitstring Status List (BSL) to verify that an envelope's grant
has not been revoked. It complements Channel 4 (push notification
of revocations) — pull verifies state at a moment in time, push
informs of changes between pulls.

Channel 3 is engaged when:

- An envelope with `revocation` extension is being processed and
  the cached BSL is stale per `bsl_max_staleness_seconds`
  (default 300 s).
- The receiver is initializing or recovering from a cache miss.
- A `revocation` extension's `max_staleness_seconds` is smaller
  than the default, requiring fresher verification.

---

## 2. Topology

Channel 3 has two topologies:

- **Direct from issuer** (default, also fallback): the receiver
  fetches the BSL from the issuer's published URL (the
  `revocation.status_list_url` field of the envelope).
- **Custodian-aggregated** (> 50 agents): the receiver fetches from
  a Trust Custodian's Status Aggregation Service per
  `xift-custodian-1.0.md` §5. The Custodian polls issuers on behalf
  of receivers.

Both topologies are conformant. The receiver MAY prefer the
Custodian-aggregated route when available, falling back to direct
on Custodian failure.

---

## 3. BSL Format

XIFT uses **W3C Bitstring Status List v1.0** (May 2025
Recommendation) as the BSL format without modification. The BSL is
itself a Verifiable Credential containing:

- An issuer DID.
- A bitstring (gzip-compressed, base64url-encoded).
- A bit index assignment (per grant).
- Its own signature.

XIFT does NOT redefine BSL. See the W3C specification for the
complete format.

---

## 4. Operation Flow

```
Receiver                               BSL Host (issuer or Custodian)
   |                                          |
   |--GET <status_list_url>------------------>|
   |   If-None-Match: "<cached_etag>"         |
   |   Accept: application/vc+ld+json         |
   |                                          |
   |<--200 OK + BSL credential ---------------|
   |   Cache-Control: max-age=300             |
   |   ETag: "<etag>"                         |
   |   OR 304 Not Modified (cache still good) |
   |   OR error                               |
   |                                          |
   | verify BSL signature                     |
   | verify BSL issuer matches expected       |
   | extract bit at status_list_index         |
   | if bit==1: protocol:revocation:grant_revoked (105)|
   | if bit == 0: accept                      |
```

---

## 5. Caching Rules

Receivers MUST implement caching with the following discipline:

- **Cache key**: `(status_list_url, status_list_hash)`. The hash
  detects when the issuer rotates lists.
- **Cache lifetime**: governed by `max_staleness_seconds` from
  the envelope's `revocation` block (REQUIRED to honor), bounded
  below by the HTTP `Cache-Control` directive (MAY honor as upper
  bound) and bounded above by `bsl_max_staleness_seconds` (default
  300 s, the protocol-level cap).
- **HTTP cache validators**: receivers SHOULD use `If-None-Match`
  and `If-Modified-Since` to minimize bandwidth. A 304 response
  resets the cache freshness window.
- **Cache invalidation**: a Channel 4 `bsl_updated` event for the
  same `status_list_url` MUST invalidate the cached entry.

---

## 6. Fail-Closed Behavior

When the receiver cannot obtain a fresh BSL within its staleness
window, it MUST fail closed: the envelope is rejected with error
`protocol:channel3:status_list_unavailable` (106).

This applies to:

- Network failure to reach the BSL host.
- BSL signature verification failure.
- Receiver's cached BSL being older than `max_staleness_seconds`
  and refresh failing.
- Custodian returning a BSL whose hash does not match the envelope's
  declared `status_list_hash`.

The fail-closed posture is normative per Principle 5 (core §1.1).
It is intentional even when it produces availability friction:
permissive fallback would allow stale-revoked grants to be honored.

---

## 7. Herd Privacy

Per `xift-1.0-spec-extension-revocation.md` §6 and the W3C BSL
specification, Channel 3 preserves herd privacy: the receiver
downloads the entire BSL, not a per-grant query, so the BSL host
cannot infer which grant the receiver is checking. The minimum BSL
length of 131,072 bits (`bsl_min_length_bits`) is enforced.

The receiver MUST NOT log the specific `status_list_index` it
queried beyond what is needed for its own audit trail. Custodians
serving BSLs MUST NOT log per-receiver index access.

---

## 8. Egress DLP for Channel 3

Egress DLP is less directly applicable to Channel 3 because the
request itself carries no governance metadata. However:

- The receiver MUST NOT include any envelope-derived identifiers in
  the HTTP request beyond what is needed (no query parameters
  leaking artifact IDs).
- When using a Custodian, the receiver MUST verify the Custodian's
  trust score before consuming the aggregated BSL, to avoid
  poisoned status lists.

---

## 9. Channel 3 Error Codes

Per the XIFT error model (core §12, ADR-XIFT-ERROR-MODEL-001), `code` is
the generic routing axis and `category` is the source of domain truth;
the subsection heading fixes layer and severity.

Channel 3 reuses `protocol:channel3:status_list_unavailable` (106) and `protocol:revocation:grant_revoked` (105)
(`grant_revoked`) from the core's core catalog. The codes below are
specific to Channel 3 wire-flow.

### 9.1 Protocol Errors

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 101 | `protocol:channel3:bsl_signature_invalid` | BSL credential failed signature verification.              |
| 101 | `protocol:channel3:bsl_issuer_unexpected` | BSL issuer differs from the envelope's expected issuer.    |
| 102 | `protocol:channel3:bsl_format_invalid` | BSL does not conform to W3C v1.0 format.                   |
| 105 | `protocol:channel3:bsl_too_short` | BSL length below `bsl_min_length_bits`; herd privacy broken. |
| 102 | `protocol:channel3:bsl_hash_mismatch` | BSL hash does not match envelope's `status_list_hash`.     |
| 102 | `protocol:channel3:bsl_index_out_of_range` | Envelope's `status_list_index` exceeds BSL length.         |

### 9.2 Protocol Warnings

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 106 | `protocol:channel3:bsl_cache_near_expiry` | Cached BSL within 80% of staleness window.                 |
| 106 | `protocol:channel3:bsl_freshness_below_target` | BSL fetch succeeded but is older than ideal.               |
| 106 | `protocol:channel3:direct_fetch_recommended` | Custodian's BSL appears stale; direct fetch suggested.     |

### 9.3 Policy Errors

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 206 | `policy:channel3:bsl_host_trust_too_low` | BSL host's trust score below receiver's threshold.         |

---

## 10. Open Questions

1. **`bsl_too_short` enforcement.** Should `bsl_too_short` (`protocol:channel3:bsl_too_short`, 105) be
   a warning instead of an error? Some deployments may accept
   smaller BSLs at the cost of herd privacy.
