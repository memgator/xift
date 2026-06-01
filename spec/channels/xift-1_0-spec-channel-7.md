---
title: "XIFT 1.0 — Channel 7: Sequential Conversation Session (SCS)"
status: draft (v1.1)
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
  - xift-1.0-spec-channel-6.md
  - xift-custodian-1.0.md
  - xift-interop-1.0.md
---

# XIFT 1.0 — Channel 7: Sequential Conversation Session (SCS)

Common conventions (transport, authentication, back-pressure,
identity handshake primitive, reserved error code ranges) are
specified in `xift-1.0-spec-channels-general.md`. This document
specifies Channel 7 normative content.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

SCS resolves **Case 3**: a sustained, multi-turn, bidirectional
conversation between two or more agents to refine shared
understanding or collaboratively produce an artifact.

SCS supports:

- 1:1 sessions (default).
- Multi-agent sessions (3+ participants) — without E2EE in v1.0
  (MLS group support deferred to a future release).
- Smart clustering with k-rounds of refinement.
- Consensus voting for collaborative output finalization.
- Session journals for downstream consolidation by the host
  (Memgator in reference implementation).

---

## 2. Session Establishment

SCS sessions are initiated via:

```
POST /xift/v1/scs/sessions
Content-Type: application/json
Authorization: Signature <signed-challenge>

{
  "session_request_id": "01HY0...",
  "initiator_did": "did:web:org.example.com:agent:alpha",
  "invited_dids": ["did:web:org.example.com:agent:beta"],
  "created_at": "2026-05-21T11:00:00.000Z",
  "session_purpose": "Refine the fraud-detection ruleset from announcement 01HX0...",
  "related_envelope_id": "01HXX...",
  "related_announcement_id": "01HX0...",
  "max_duration_seconds": 1800,
  "transport_preference": "sse",
  "smart_clustering": {
    "enabled": true,
    "max_rounds": 5,
    "consensus_threshold": 0.66
  },
  "session_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:agent:alpha#key-1"
}
```

Response:

```
HTTP 201 Created

{
  "session_id": "01HY1...",
  "session_token": "<opaque-token-derived-from-identity-handshake>",
  "stream_endpoint": "https://api.example.com/xift/v1/scs/streams/01HY1...",
  "accepted_invitees": ["did:web:org.example.com:agent:beta"],
  "declined_invitees": [],
  "session_expires_at": "2026-05-21T11:30:00Z"
}
```

| Field                       | Purpose                                                            |
|-----------------------------|--------------------------------------------------------------------|
| `session_id`                | ULID for this session.                                             |
| `session_token`             | Opaque token derived from the identity handshake; carried in all subsequent messages without re-handshake. |
| `stream_endpoint`           | URL for the SSE or WebSocket stream.                               |
| `accepted_invitees`         | Subset of invitees that accepted.                                  |
| `declined_invitees`         | Invitees that rejected (with optional reason codes).               |

The session request MAY carry an OPTIONAL `session_billing_model`
field that declares the billing arrangement for the session (e.g.,
flat fee, per-message, per-round). Detailed schema for this field is
deferred to the billing extension specification; SCS only carries
the reference.

---

## 3. Session Token

The `session_token` enables stateless authorization of all messages
in the session without re-running the identity handshake per message.
It MUST be derived from the initial handshake (e.g., HMAC of session
key) and bound to the `session_id` and participants. Token TTL
matches `session_expires_at`.

Token rotation MAY occur via a `session_key_rotation` message (§5).

---

## 4. Message Format on Stream

Once the session is open, the stream carries `XiftSessionMessage`
objects:

```json
{
  "session_id": "01HY1...",
  "message_seq": 4,
  "sender_did": "did:web:org.example.com:agent:alpha",
  "created_at": "2026-05-21T11:05:00.000Z",
  "message_type": "draft",
  "round": 2,
  "in_reply_to_seq": 3,
  "content": {
    "text": "Proposed refined rule set...",
    "artifact_ref": null
  },
  "vote": null,
  "session_token": "<token>",
  "message_signature": "<base64url-bytes>"
}
```

| Field                | Purpose                                                                 |
|----------------------|-------------------------------------------------------------------------|
| `message_seq`        | Monotonic counter per session, per sender. Enables ordering and replay detection. |
| `message_type`       | See §5.                                                                 |
| `round`              | Refinement round number (1-indexed).                                    |
| `in_reply_to_seq`    | OPTIONAL. Sequence number of the message being responded to.            |
| `content`            | Object with text and/or `artifact_ref` (URL to a full envelope).        |
| `vote`               | Populated only for `vote` message_type. See §7.                         |
| `session_token`      | Echoed for stateless verification.                                      |

---

## 5. Message Types

| Type              | Meaning                                                                 |
|-------------------|-------------------------------------------------------------------------|
| `draft`           | A participant proposes content (text or artifact reference).            |
| `critique`        | A participant comments on a draft (in_reply_to_seq points to draft).    |
| `revision`        | An updated draft incorporating critiques.                               |
| `vote`            | Vote on a draft (consensus voting).                                     |
| `task_complete`   | Signal that the cluster considers the conversation concluded.           |
| `synopsis`        | End-of-session consolidated summary produced by initiator.              |
| `session_key_rotation` | Trigger token rotation mid-session.                                |
| `session_close`   | Explicit session termination.                                           |
| `ontology_probe`     | (`ontology` ext.) Request alignment for a set of concepts; carries a scoped SKOS projection. See §6.1. |
| `ontology_assertion` | (`ontology` ext.) Assert candidate alignment cells for the probed concepts.                            |
| `ontology_ack`       | (`ontology` ext.) Accept/reject asserted cells; consolidated cells land in the `synopsis`.             |

---

## 6. Smart Clustering and K-Rounds

When `smart_clustering.enabled = true` in the session request, the
session follows a structured refinement pattern:

1. **Round 1**: initiator emits initial `draft`.
2. **Each subsequent round**: participants emit `critique` and/or
   `revision` messages.
3. After `max_rounds` or upon consensus (§7), the session moves to
   `task_complete`.
4. The initiator emits a final `synopsis` consolidating the
   conversation outcome.

Smart clustering is optional; sessions can also be free-form
(`smart_clustering.enabled = false`).

Rationale: k-round refinement reduces hallucination risk in
multi-agent reasoning and produces auditable consolidation paths.
This pattern is drawn from 2025 research on multi-agent
collaboration.

### 6.1 Reciprocal Ontology Alignment Loop (`ontology` ext.)

When both participants declare the `ontology` extension and opt in for
the session, SCS is the **only** channel that hosts the reciprocal
alignment loop (`xift-1.0-spec-extension-ontology.md` §3.5). The loop
**reuses the existing round, journal and synopsis machinery unchanged**
— it adds no consensus semantics (consensus, voting weights and round
limits remain exactly as in §7 and ADR-XIFT-SCS-CONSENSUS-WEIGHTS-002):

1. A participant emits `ontology_probe` with a scoped SKOS projection of
   the concepts needing alignment.
2. The counterparty emits `ontology_assertion` with candidate alignment
   cells (`xift-1.0-spec-extension-ontology.md` §3.2), derived under
   frugal tiering (deterministic first, model tier only on borderline
   cells).
3. Participants exchange `ontology_ack` to accept/reject cells.
4. The final `synopsis` carries the **consolidated alignment cells**.

The model tier is non-deterministic and therefore **advisory and never
consensus-bearing**; a low `alignment_score` surfaces as the warning
`model:ontology:alignment_score_low` (303) unless a deployment configures
`ontology_alignment_min_score`. Cells in the signed synopsis MAY be
cached and reused to seed later Channel 5/6 exchanges, invalidated on a
`context_hash` change or after `ontology_cell_max_age_seconds`.

---

## 7. Consensus Voting

When voting is required (e.g., to mark a round complete):

```json
{
  "session_id": "01HY1...",
  "message_seq": 17,
  "sender_did": "did:web:org.example.com:agent:beta",
  "created_at": "...",
  "message_type": "vote",
  "round": 3,
  "in_reply_to_seq": 16,
  "content": null,
  "vote": {
    "subject_seq": 15,
    "value": "approve",
    "weight": 1.0,
    "reason": "Captures the edge cases I raised in seq 12."
  },
  "session_token": "<token>",
  "message_signature": "<base64url-bytes>"
}
```

| Vote field      | Purpose                                                                   |
|-----------------|---------------------------------------------------------------------------|
| `subject_seq`   | The message being voted on.                                               |
| `value`         | `approve`, `reject`, or `abstain`.                                        |
| `weight`        | OPTIONAL. Vote weight (default 1.0); MAY be derived from trust score.    |
| `reason`        | Free-text justification.                                                  |

Consensus is reached when the weighted-approve ratio (over approve
+ reject votes) meets `consensus_threshold` from the session request.
At that point, any participant MAY emit a `task_complete` message.

---

## 8. Session Journal

The initiator (or a designated participant) maintains a session
journal: an ordered log of all messages with their signatures. The
journal is consumed by the host (Memgator in reference
implementation) at session close to consolidate learnings into
memory.

The journal format is implementation-defined; XIFT does not
prescribe it. The synopsis emitted at session close is XIFT-defined.

---

## 9. Sensitivity Constraints for Multi-Agent Sessions

Because v1.0 does not support multi-agent E2EE (MLS group support
deferred to a future release), the following constraint applies:

**Multi-agent SCS sessions (3+ participants) MUST NOT carry
envelopes or content with `classification ≥ sensitive`.** Sessions
attempting this MUST be rejected at establishment with `policy:channel7:multi_agent_classification_too_high` (201).

1:1 SCS sessions retain full classification range, using HPKE
pair-wise encryption per envelope.

---

## 10. SCS Egress Obligations

Per core §8.4 (egress validation MUST happen before any envelope
is emitted), SCS adds the following channel-specific obligations:

For each `XiftSessionMessage`:

- The sender MUST validate that content respects the multi-agent
  classification constraint (§9).
- If the session crosses trust domains, the sender MUST verify each
  participant's trust score remains above the threshold declared at
  session start. Mid-session score drops below threshold MUST
  trigger `policy:channel7:participant_below_trust_threshold` (206) and session termination.

---

## 11. SCS Normative Parameters

Channel 7-specific parameters extending core §10:

| Parameter                                          | Default     | Purpose                                                       |
|----------------------------------------------------|-------------|---------------------------------------------------------------|
| `scs_session_max_duration_seconds`                 | 3600        | 1 hour. Hard limit on session duration.                       |
| `scs_max_concurrent_sessions_per_did`              | 16          | Per-agent concurrent session quota.                           |
| `scs_max_participants_per_session`                 | 8           | Limit for multi-agent sessions.                               |
| `scs_max_rounds_per_session`                       | 10          | Hard cap on refinement rounds.                                |
| `scs_max_message_size_kb`                          | 32          | Maximum size of any single session message.                   |
| `scs_session_token_ttl_seconds`                    | 3600        | Matches session duration; rotation supported.                 |

---

## 12. Channel 7 Anti-Patterns and Mitigations

### 12.1 Consensus Deadlock

Multi-agent sessions failing to reach consensus indefinitely.

Mitigation:
- `scs_max_rounds_per_session` hard cap.
- `policy:channel7:consensus_unreachable` (203, warning) emitted when a round closes without consensus.
- Initiator MAY emit `task_complete` even without consensus
  (with synopsis noting the disagreement).

---

## 13. SCS Error Codes

Per the XIFT error model (core §12, ADR-XIFT-ERROR-MODEL-001), `code` is
the generic routing axis and `category` is the source of domain truth;
the table's layer and severity columns complete the routing tuple.


| Code | Layer    | Severity | Category                          | Description                                          |
|------|----------|----------|-----------------------------------|------------------------------------------------------|
| 102 | protocol | error | `protocol:channel7:session_request_invalid` | Session request signature or structure invalid.      |
| 101 | protocol | error | `protocol:channel7:session_token_invalid` | Token verification failed.                           |
| 105 | protocol | error | `protocol:channel7:message_seq_out_of_order` | Sequence number violation.                           |
| 105 | protocol | error | `protocol:channel7:session_expired` | Session past `session_expires_at`.                   |
| 108 | protocol | error | `protocol:channel7:session_quota_exceeded` | Participant exceeded `max_concurrent_sessions`.      |
| 105 | protocol | warning | `protocol:channel7:session_nearing_expiry` | Session within 10% of duration.                      |
| 108 | protocol | warning | `protocol:channel7:round_limit_approaching` | Within 1 round of `max_rounds`.                      |
| 201 | policy | error | `policy:channel7:multi_agent_classification_too_high` | Multi-agent session refused for sensitive content. |
| 206 | policy | error | `policy:channel7:participant_below_trust_threshold` | An invitee's trust score is too low.              |
| 203 | policy | warning | `policy:channel7:consensus_unreachable` | Round closing without consensus; flagging.           |

---

## 14. Open Questions

1. **Multi-agent E2EE.** MLS group support (RFC 9420) deferred to
   a future release. Until then, sensitive content in multi-agent SCS sessions
   is hard-rejected (§9). Is there a pair-wise broadcast pattern
   (each participant pair has its own HPKE channel within the
   session) that's worth specifying as interim?

2. **Session journal format.** Currently implementation-defined.
   Memgator reference implementation will define a format; should
   XIFT promote it to recommended?

3. **Consensus voting weights.** Vote weight defaulting to 1.0 is
   simple but doesn't capture trust differentials. Should weights
   default to a function of trust score? This could create
   plutocratic dynamics.

4. **SCS streaming transport.** The specification supports SSE;
   WebSocket is mentioned as escalation. Should explicit fallback
   rules be in the spec, or left to capability negotiation?
