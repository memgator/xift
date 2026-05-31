---
title: XIFT 1.0 — Extension `encryption`
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
  - xift-1.0-spec-extension-revocation.md
  - xift-1.0-spec-extension-quality.md
  - xift-1.0-spec-channel-2.md (Envelope Handoff)
  - xift-interop-1.0.md
---

# XIFT 1.0 — Extension: `encryption`

This document specifies the `encryption` envelope extension. Common
envelope conventions (canonical form, mandatory blocks, signature
mechanics, identity layer, cryptography defaults, error model) are
specified in `xift-1.0-spec-core.md`.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

The `encryption` extension declares that the envelope's payload is
encrypted end-to-end between the issuer and the recipient(s), using
HPKE (RFC 9180) or an equivalent scheme.

Encryption protects payload confidentiality across the wire, in
storage-mediated handoff (`xift-1.0-spec-channel-2.md` §5), and at
rest after delivery. The signature over the envelope (core §8.3)
remains over the unencrypted plaintext canonical form; that is how
the receiver verifies authenticity after decryption.

XIFT does NOT use the `encryption` block to encrypt the **envelope
metadata** itself; metadata (envelope_id, agent_did, governance,
provenance, revocation, ...) remains readable so that intermediaries
and audit can evaluate policy without decryption. Only the payload
body and (when present) the `quality` extension fields are within
the encryption scope.

This is one of the **core extensions** every conformant
implementation MUST recognise (`xift-1.0-spec-channel-1.md` §3, §4).

---

## 2. When Required vs Optional

- **REQUIRED** when `governance.classification ∈ {sensitive,
  restricted}`. Envelopes failing this constraint are rejected
  with error `protocol:encryption:mandatory_encryption_missing` (105).
- **OPTIONAL** for all other classifications. Issuers MAY always
  opt-in.
- **NOT APPLICABLE** for envelopes without `governance`; such
  envelopes are restricted to `public` classification semantics and
  do not benefit from encryption.

---

## 3. Block Structure

```json
{
  "encryption": {
    "scheme": "hpke-x25519-sha256-aes256gcm",
    "recipient_kid": "did:key:z6LSbysY...#enc-key-1",
    "ephemeral_pubkey": "<base64-bytes>",
    "nonce": "<base64-bytes>",
    "aad_hash": "sha256:...",
    "ciphertext_hash": "sha256:..."
  }
}
```

---

## 4. Fields

| Field              | Type   | Required | Description                                                                              |
|--------------------|--------|----------|------------------------------------------------------------------------------------------|
| `scheme`           | string | yes      | Cipher suite identifier. See §5.                                                          |
| `recipient_kid`    | string | yes      | DID URL fragment resolving to the recipient's X25519 encryption key.                      |
| `ephemeral_pubkey` | string | yes      | Sender's HPKE ephemeral public key. Standard base64 (with padding) of the 32-byte X25519 public key. RFC 9180 §5. |
| `nonce`            | string | yes      | AEAD nonce. Standard base64 (with padding) of the 12-byte (96-bit) nonce for both AES-256-GCM and ChaCha20-Poly1305 (`Nn = 12` per RFC 9180). Derivation is library-internal. |
| `aad_hash`         | string | yes      | SHA-256 of the Additional Authenticated Data bound to the AEAD operation. Prefixed-hex form `sha256:<hex>` (core §3.3.3). |
| `ciphertext_hash`  | string | yes      | SHA-256 of the ciphertext bytes. Prefixed-hex form `sha256:<hex>` (core §3.3.3). Allows integrity check without decrypting. |

The ciphertext itself is carried in the envelope's `payload_inline`
or fetched from `content_ref` (core §3.3), not in this block.

---

## 5. Supported Schemes

| Scheme identifier                       | Description                                |
|-----------------------------------------|--------------------------------------------|
| `hpke-x25519-sha256-aes256gcm`          | RFC 9180 HPKE. **Default; MUST be supported.** |
| `hpke-x25519-sha256-chacha20poly1305`   | HPKE with ChaCha20-Poly1305 AEAD.          |
| `age-x25519`                            | age encryption (lower-sensitivity use).    |

Implementations MUST support the default scheme. Other schemes are
OPTIONAL; capability declared via `supported_encryption_schemes` in
the capability advertisement (`xift-1.0-spec-channel-1.md` §3).

Post-quantum schemes (ML-KEM, hybrid X25519+ML-KEM) are tracked in
core §15.1 but are NOT part of XIFT v1.0.

---

## 6. Key Resolution

`recipient_kid` is a DID URL fragment resolving to an X25519
encryption key. How the key is published depends on the DID method:

- W3C DID Documents with `keyAgreement` verification relationships.
- Side-channel key directories when the DID method does not natively
  support encryption keys.
- Implementation-specific extensions (e.g., the reference
  implementation uses the Agent Mesh E2EE component, with a
  pluggable `KeyProvider` host trait per
  `xift-reference-implementation-architecture.md` §3, §4).

Senders MUST verify the resolved encryption key against the
recipient's signed capability advertisement (specifically that
`recipient_kid` is among the keys the recipient has bound to its
DID document) before encrypting.

---

## 7. Receiver Behaviour

A receiver that declares `encryption` in `supported_extensions` MUST:

1. Verify the envelope signature (over the canonical plaintext) AS
   FIRST STEP — before any decryption attempt. This binds the
   `encryption` block contents (including `recipient_kid` and the
   hashes) to the issuer.
2. Verify `recipient_kid` resolves to one of the receiver's own
   encryption keys; otherwise reject with
   `protocol:channel2:crypto_recipient_kid_mismatch` (105) when
   `recipient_kid` does not resolve to a held encryption key (this is a
   key-resolution failure, distinct from the `recipient_did` check that
   raises `protocol:channel2:recipient_mismatch`), or
   `protocol:extension:unknown_extension` (105) when the `scheme` is
   unsupported.
3. Verify `ciphertext_hash` against the received ciphertext bytes
   BEFORE decryption (defence in depth against malformed AEAD
   ciphertexts).
4. Reconstruct the AAD and verify `aad_hash` against it BEFORE
   decryption (the AAD is an input to the AEAD operation).
5. Decrypt the payload using the scheme indicated by `scheme`,
   producing plaintext bytes. The AEAD tag check happens here.
6. Verify `payload_hash` (from the envelope, not from this block)
   against the decrypted plaintext.

A receiver MUST treat any verification failure as terminal and emit
error `protocol:crypto:signature_verification_failed` (101) when the
failure is cryptographic in nature, or
`protocol:integrity:payload_hash_mismatch` (102) when the plaintext
integrity check fails.

---

## 8. Egress DLP for `encryption`

Per core §8.4, the sender MUST:

- Verify that `classification ∈ {sensitive, restricted}` is paired
  with an `encryption` block; otherwise self-reject with error
  `protocol:encryption:mandatory_encryption_missing` (105).
- Verify the recipient's capability advertisement declares the
  chosen `scheme` in `supported_encryption_schemes`. Choosing a
  scheme the recipient does not advertise is an egress failure
  (error `protocol:egress:egress_validation_failed`, 105).
- Ensure encryption keys (both the recipient's `keyAgreement` key
  and the sender's ephemeral key) come from a `KeyProvider` boundary
  and never leave that boundary in cleartext.

---

## 9. Extension Parameters

`encryption` has no parameters beyond those declared in
`supported_encryption_schemes` of the capability advertisement
(`xift-1.0-spec-channel-1.md` §4.1). No new normative parameters
are added by this specification.

---

## 10. `encryption` Error Codes

Per the XIFT error model (core §12, ADR-XIFT-ERROR-MODEL-001), `code`
is the generic operational routing axis and `category` is the source of
domain truth; the subsection heading fixes layer and severity. All the
conditions below are `protocol`-layer errors registered in
`xift-error-taxonomy.md`:

| Code | Category                                       | Description                                                          |
|------|------------------------------------------------|----------------------------------------------------------------------|
| 101  | `protocol:crypto:signature_verification_failed`| Envelope signature over the canonical form failed (precondition).    |
| 102  | `protocol:integrity:payload_hash_mismatch`     | Decrypted plaintext does not hash to `payload_hash`.                 |
| 105  | `protocol:extension:unknown_extension`         | Receiver does not support the declared `encryption.scheme`.          |
| 105  | `protocol:encryption:mandatory_encryption_missing` | Classification ≥ `sensitive` but no `encryption` block present.  |
| 105  | `protocol:channel2:crypto_recipient_kid_mismatch` | `recipient_kid` does not resolve to one of the receiver's own encryption keys (§7 step 2). Distinct from `protocol:channel2:recipient_mismatch`, which is the `recipient_did` check. |

This extension does not introduce a numeric code; cryptographic
failures reuse the canonical `protocol`-layer routing codes (core §12.1)
so receivers can apply uniform error-routing policies and disambiguate
by `category`.

---

## 11. Why Not DIDComm

DIDComm's JWE provides analogous functionality. XIFT does not adopt
it because: (a) the reference implementation's identity provider does
not implement DIDComm, and (b) HPKE primitives are simpler to
implement and audit than the full JOSE stack for XIFT's narrow
domain.

Implementations using DID methods that natively support DIDComm MAY
provide a DIDComm adapter, documented in `xift-interop-1.0.md`. The
adapter MUST translate to one of the schemes in §5 at the XIFT
boundary; XIFT does not gain a DIDComm-native scheme identifier.

---

## 12. Anti-Patterns and Mitigations

### 12.1 Mandatory-Encryption Bypass via Classification Downgrade

**Pattern.** An issuer with `sensitive` content declares
`classification = confidential` to avoid the mandatory-encryption
constraint of §2.

**Mitigation.** Receivers' policy engines MUST cross-check declared
classification against known content patterns (DLP heuristics,
sample-level checks) and reject envelopes with suspicious mismatches.
This is a policy-layer concern, not a protocol enforcement, but the
fail-safe default of treating unknown `pii_classification` as
`personal-identifiable` (governance §3.4) and refusing PII in
`internal`/`confidential` for sensitive sectors is a defence.

### 12.2 Encryption Without Egress Validation

**Pattern.** A sender encrypts to the wrong recipient because it
trusted a stale capability advertisement.

**Mitigation.** Senders MUST re-fetch (or freshness-check) the
recipient's capability advertisement before encrypting to a new
recipient. The recipient's `expires_at` defines the freshness bound
(core §3.3 of channel-1).

### 12.3 AAD Omission

**Pattern.** A sender omits Additional Authenticated Data (or
includes only trivial AAD), enabling certain replay attacks.

**Mitigation.** The `aad_hash` field is REQUIRED and the AAD MUST
include at minimum `envelope_id`, `agent_did`, `recipient_did`, and
`correlation_id`. The receiver MUST reconstruct the AAD from these
mandatory envelope fields and verify the hash matches before
decryption.

### 12.4 Library Misconfiguration: Reused Nonces

**Pattern.** A custom-rolled HPKE implementation reuses nonces
across messages, breaking AEAD security.

**Mitigation.** XIFT mandates RFC 9180 compliance. Implementations
MUST use audited HPKE libraries; the reference implementation uses
`hpke-rs` (impl §4.3). The reference implementation's fuzzing
harness flags nonce-reuse patterns; this is an implementation-level
safeguard rather than a single-envelope wire conformance case
(nonce reuse is only detectable across messages, not from one
envelope).

---

## 13. Conformance Tests

The `encryption` extension contributes the following cases to the
conformance suite (anchored in core Appendix B and channels-general
§13):

| Case   | Subject                                                                                                       |
|--------|---------------------------------------------------------------------------------------------------------------|
| ENC-01 | Envelope with `classification = sensitive` and no `encryption` block is rejected with error `protocol:encryption:mandatory_encryption_missing` (105).              |
| ENC-02 | Envelope with `classification = restricted` and `scheme = hpke-x25519-sha256-aes256gcm` round-trips correctly.  |
| ENC-03 | Envelope with `scheme = <unknown>` is rejected with error `protocol:extension:unknown_extension` (105).                                                |
| ENC-04 | Envelope whose `ciphertext_hash` does not match the received ciphertext bytes is rejected before decryption.   |
| ENC-05 | Envelope whose decrypted plaintext does not hash to `payload_hash` is rejected with error `protocol:integrity:payload_hash_mismatch` (102).                 |
| ENC-06 | Sender egress validation rejects a `scheme` not in recipient's `supported_encryption_schemes` with error `protocol:egress:egress_validation_failed` (105).  |

---

## 14. Open Questions

1. **Multi-recipient encryption.** v1.0 supports a single
   `recipient_kid` per envelope. Multi-agent CSS sessions
   (channel-7) currently rely on pair-wise envelopes; multi-recipient
   HPKE (RFC 9180 §6) would let one envelope encrypt to a group.
   Worth specifying in a future revision?

2. **`age-x25519` use cases.** Why does the spec include `age` as
   an alternative? It is simpler to integrate in CLI workflows but
   has weaker formal AEAD properties than HPKE. Should it be
   demoted to "non-default, discouraged for new deployments"?

3. **Post-quantum migration path.** Core §15.1 tracks ML-KEM. When
   adopted, what is the wire-compatible transition? Cipher-agile
   `scheme` allows a hybrid `hpke-x25519-mlkem768-sha256-aes256gcm`
   without breaking the envelope schema, but operational migration
   needs design.
