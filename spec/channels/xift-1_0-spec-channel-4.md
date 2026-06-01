---
title: "XIFT 1.0 — Channel 4: Change Notification (Revocation Push)"
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
  - xift-1.0-spec-channel-5.md
  - xift-1.0-spec-channel-6.md
  - xift-1.0-spec-channel-7.md
  - xift-custodian-1.0.md
  - xift-interop-1.0.md
---

# XIFT 1.0 — Channel 4: Change Notification (Revocation Push)

Common conventions (transport, authentication, back-pressure,
identity handshake primitive, reserved error code ranges) are
specified in `xift-1.0-spec-channels-general.md`. This document
specifies Channel 4 normative content.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

Channel 4 is the **asynchronous push** of state changes that
receivers need to know about between Channel 3 polls. The primary
event is revocation, but the channel also carries:

- Capability advertisement changes (delta updates).
- Trust Custodian state transitions (activation, decommissioning,
  failover).
- BSL refresh notifications.

Channel 4 complements Channel 3: where Channel 3 verifies state at
a moment, Channel 4 informs of changes in real time. Together they
provide both **freshness on demand** and **immediacy on event**.

---

## 2. Topology

Channel 4 is **publish-subscribe via SSE**:

- The publisher (BSL host, Custodian, or capability publisher)
  exposes an SSE endpoint.
- Subscribers connect via long-lived SSE GET and receive events as
  they occur.
- Reconnection is the subscriber's responsibility, with `Last-Event-ID`
  for resumption.

In Custodian-mediated topology, the Custodian is the typical
publisher: it aggregates events from multiple issuers and fans them
out to subscribed receivers. In P2P topology, each publisher serves
its own Channel 4 endpoint.

---

## 3. Subscription Flow

```
Subscriber                             Publisher
   |                                          |
   |--GET /xift/v1/notifications-------------->|
   |   Authorization: Bearer <session_token>  |
   |   Accept: text/event-stream              |
   |   Last-Event-ID: "<id>" (on resume)      |
   |                                          | verify session_token
   |                                          | verify subscriber visibility
   |<--200 OK + text/event-stream-------------|
   |   (held open)                            |
   |                                          |
   |   << SSE event stream begins >>          |
   |                                          |
   |<-event: bsl_updated                      |
   |  id: 01HZA...                            |
   |  data: { ... XiftRevocationEvent ... }   |
   |                                          |
   |<-event: capability_changed               |
   |  id: 01HZB...                            |
   |  data: { ... XiftCapabilityChangeEvent ...} |
   |                                          |
   | (subscriber processes events;            |
   |  invalidates caches; updates internal    |
   |  state)                                  |
```

Mermaid version:
```mermaid
sequenceDiagram
    autonumber
    actor Subscriber
    actor Publisher

    Subscriber->>Publisher: GET /xift/v1/notifications<br/>Authorization: Bearer <session_token><br/>Accept: text/event-stream<br/>Last-Event-ID: "<id>" (on resume)
    Note over Publisher: verify session_token
    Note over Publisher: verify subscriber visibility
    Publisher-->>Subscriber: 200 OK + text/event-stream (held open)

    Note over Subscriber, Publisher: << SSE event stream begins >>

    Publisher-->>Subscriber: event: bsl_updated<br/>id: 01HZA...<br/>data: { ... XiftRevocationEvent ... }
    Publisher-->>Subscriber: event: capability_changed<br/>id: 01HZB...<br/>data: { ... XiftCapabilityChangeEvent ... }

    Note over Subscriber: subscriber processes events;<br/>invalidates caches; updates internal state
```

---

## 4. Event Message: XiftRevocationEvent

When a grant is revoked (a bit flips in a BSL), the publisher emits:

```json
{
  "event_id": "01HZA...",
  "event_type": "revocation",
  "publisher_did": "did:web:org.example.com:issuer-1",
  "published_at": "2026-05-21T10:00:00.000Z",
  "bsl_reference": {
    "status_list_url": "https://issuer.example.com/bsl/list-2026-05",
    "status_list_index": 47291,
    "status_list_new_hash": "sha256:..."
  },
  "envelope_id_affected": "01HXX5VQ7K9M3J8N2P4R6T8WAY",
  "revocation_reason_code": "tenant-policy",
  "revocation_reason_text": null,
  "event_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:issuer-1#key-1"
}
```

| Field                          | Description                                                |
|--------------------------------|------------------------------------------------------------|
| `event_id`                     | ULID for this event. Used by subscribers for `Last-Event-ID`. |
| `event_type`                   | Always `revocation` for this event class.                  |
| `publisher_did`                | DID of the entity publishing (issuer or Custodian).        |
| `published_at`                 | RFC3339, millisecond precision.                            |
| `bsl_reference.status_list_url`| URL of the BSL whose bit changed.                          |
| `bsl_reference.status_list_index` | The bit index that was flipped (set to 1 = revoked).    |
| `bsl_reference.status_list_new_hash` | Hash of the BSL after the change.                    |
| `envelope_id_affected`         | OPTIONAL. The specific envelope this revocation applies to, when known. |
| `revocation_reason_code`       | Machine-readable code: `tenant-policy`, `consent-withdrawn`, `key-compromise`, `audit-finding`, `other`. |
| `revocation_reason_text`       | OPTIONAL natural-language explanation. MUST NOT contain PII. |
| `event_signature`              | Ed25519 over JCS of all fields except this one.            |

The subscriber, on receiving the event, MUST:

1. Verify `event_signature`.
2. Verify `publisher_did` matches the expected publisher.
3. Invalidate any cached BSL matching `status_list_url`.
4. If holding any artifacts referencing this BSL bit, mark them as
   revoked and apply cascade per the lineage policy (core §9).

---

## 5. Event Message: XiftCapabilityChangeEvent

When an agent's capability advertisement changes:

```json
{
  "event_id": "01HZB...",
  "event_type": "capability_changed",
  "publisher_did": "did:web:org.example.com:agent:alpha",
  "published_at": "2026-05-21T10:01:00.000Z",
  "subject_did": "did:web:org.example.com:agent:alpha",
  "change_type": "update",
  "previous_version": 11,
  "new_version": 12,
  "changed_fields": [
    "channel_capabilities.css",
    "resource_costs.median_latency_ms"
  ],
  "fetch_url": "https://api.example.com/xift/v1/discovery/self",
  "event_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:agent:alpha#key-1"
}
```

`change_type` values: `update`, `withdraw`, `expire`.

The subscriber MAY fetch the updated capability advertisement from
`fetch_url` to obtain the full new version.

---

## 6. Event Message: XiftCustodianStateEvent

When a Trust Custodian transitions state:

```json
{
  "event_id": "01HZC...",
  "event_type": "custodian_state",
  "publisher_did": "did:web:org.example.com:agent:custodian-1",
  "published_at": "2026-05-21T10:02:00.000Z",
  "previous_state": "awakening",
  "new_state": "active",
  "services_offered": {
    "capability_index": true,
    "status_aggregation": true,
    "identity_cache": true
  },
  "event_signature": "<base64url-bytes>"
}
```

See `xift-custodian-1.0.md` §2 for the complete state machine.

---

## 7. Subscriber Reconnection

SSE connections are subject to network interruptions. Subscribers
MUST handle reconnection:

- On disconnect, the subscriber MAY reconnect with
  `Last-Event-ID: <last_received_event_id>` in the request header.
- The publisher SHOULD replay events emitted after that ID, up to
  a publisher-defined buffer window (default 5 minutes,
  `notification_replay_buffer_seconds`).
- Events older than the buffer window are NOT replayed; the
  subscriber MUST treat its cache as potentially stale and
  re-verify on demand via Channel 3.

The replay buffer is per-subscriber-session, not global. Publishers
are not required to maintain unbounded history.

---

## 8. Egress DLP for Channel 4

Channel 4 events carry references to envelopes and BSL indices, but
NOT to payload content. However:

- The publisher MUST evaluate subscriber visibility before sending
  events about specific envelopes. A subscriber that was not a
  recipient of an envelope SHOULD NOT receive events about its
  revocation, unless the subscriber has policy-justified need (e.g.,
  it derived an artifact from the revoked source under strict
  lineage).
- `revocation_reason_text` (§4) is free-form but MUST NOT contain
  PII. Publishers MUST redact before emitting.
- The `envelope_id_affected` field is OPTIONAL; publishers MAY emit
  events with only `bsl_reference` populated to reduce information
  leakage about specific artifacts.

---

## 9. Connection Lifecycle and Liveness

Long-lived SSE connections require explicit liveness handling:

- The publisher SHOULD emit a `keepalive` comment frame (per SSE
  spec, lines beginning with `:`) every 30 seconds to detect dead
  connections.
- The subscriber SHOULD treat absence of keepalives for 90 seconds
  as disconnection and initiate reconnection.
- The publisher MAY terminate a connection with a final event
  `event: stream_terminated` carrying a reason (`protocol:channel4:notification_stream_terminated`, 106; see below).

---

## 10. Implementation Notes (Non-Normative)

### 10.1 SSE Library Choice

Channel 4's SSE implementation is unconstrained by XIFT. Reference
implementation uses an async Rust runtime with `axum`'s SSE
support; other implementations may use Node.js EventSource, Python
sse-starlette, etc.

---

## 11. Channel 4 Error Codes

Per the XIFT error model (core §12, ADR-XIFT-ERROR-MODEL-001), `code` is
the generic routing axis and `category` is the source of domain truth;
the subsection heading fixes layer and severity.

### 11.1 Protocol Errors

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 101 | `protocol:channel4:notification_session_required` | Channel 4 request without valid session token.             |
| 111 | `protocol:channel4:notification_stream_unsupported` | Publisher does not implement Channel 4.                    |
| 106 | `protocol:channel4:notification_stream_terminated` | Publisher closed the stream (graceful shutdown, restart).  |
| 101 | `protocol:channel4:event_signature_invalid` | An incoming event's signature failed verification.         |
| 101 | `protocol:channel4:event_publisher_unexpected` | Event `publisher_did` does not match expected publisher.   |
| 108 | `protocol:channel4:event_replay_buffer_exceeded` | `Last-Event-ID` is older than replay buffer; full resync needed. |
| 102 | `protocol:channel4:event_schema_invalid` | Event payload fails schema validation.                     |
| 106 | `protocol:channel4:notification_keepalive_lost` | Subscriber detected absence of keepalives; reconnecting.   |
| 108 | `protocol:channel4:notification_connection_refused` | Publisher refused the SSE or WebSocket connection due to subscriber capacity exhaustion (§7.6 of channels-general) or other publisher-side constraint. The response MUST include a `Retry-After` header. |
| 101 | `protocol:channel4:notification_reauth_required` | Session token expired mid-stream; re-handshake needed.     |

### 11.2 Protocol Warnings

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 103 | `protocol:channel4:notification_high_event_rate` | Subscriber receiving events faster than recommended rate.  |
| 108 | `protocol:channel4:notification_buffer_nearing_full` | Publisher's replay buffer 80% full; resync recommended.    |
| 107 | `protocol:channel4:keepalive_delayed` | Keepalive emission delayed beyond 30 s but within 90 s.    |

### 11.3 Policy Errors

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 201 | `policy:channel4:notification_visibility_denied` | Subscriber not authorized for events about this scope.     |
| 206 | `policy:channel4:subscriber_trust_too_low` | Subscriber trust score below publisher's threshold.        |

### 11.4 Policy Warnings

| Code | Category                              | Description                                                |
|------|---------------------------------------|------------------------------------------------------------|
| 204 | `policy:channel4:event_payload_redacted` | Some event fields were elided for the subscriber's trust level. |

---

## 12. Open Questions

1. **Channel 4 event filtering.** Should subscribers be able to
   declare filters at subscription time (e.g., "only revocations,
   not capability changes")? Currently the subscriber receives the
   full stream and filters client-side.

2. **Multi-publisher Channel 4 federation.** When a subscriber wants
   to receive events from multiple publishers, does it open one
   SSE per publisher, or is there a federation pattern?
