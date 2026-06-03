---
title: XIFT 1.0 — Trust Custodian Specification
status: draft (v1.0)
date: 2026-05-21
visibility: public
authors:
  - Memgator architecture working group
related:
  - xift-1.0-spec-core.md (core spec)
  - xift-1.0-spec-channels-general.md (cross-channel conventions)
  - xift-1.0-spec-channel-1.md (Discovery & Handshake)
  - xift-1.0-spec-channel-3.md (Status Verification)
  - xift-1.0-spec-channel-4.md (Change Notification)
  - xift-1.0-spec-channel-5.md (Semantic Discovery)
  - xift-1.0-spec-channel-6.md (SIEA)
  - xift-interop-1.0.md (interop profile)
---

# XIFT 1.0 — Trust Custodian Specification

## 0. Document Status

This document is the **Trust Custodian specification**, a companion
to the XIFT v1.0 protocol. It depends on the core for the
envelope and identity model, and on the semantic channels (SDR,
SIEA) that the Custodian serves.

The Trust Custodian is an OPTIONAL role at mesh sizes ≤ 50 agents and
becomes MANDATORY above this threshold per core §10. This document
specifies the Custodian's three services, its wire protocol with
agents, its state machine for activation and failover, its
multi-Custodian coordination patterns, its threat model, and its
conformance test obligations.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Role Overview

### 1.1 What the Trust Custodian Is

The Trust Custodian is a **specialized agent role** that provides
three services to a federated mesh of XIFT agents above a critical
size:

1. **Capability Index Service**: maintains a signed, indexed
   directory of agent capability documents, enabling sub-linear
   semantic discovery via HNSW or equivalent vector indices.
2. **Status Aggregation Service**: caches and serves W3C Bitstring
   Status Lists from multiple issuers, reducing polling load and
   enabling efficient cross-mesh revocation propagation.
3. **Identity Cache Service**: caches mutual authentication
   handshake results to amortize the 200 ms identity verification
   budget across many sessions.

A Custodian is an XIFT agent like any other — it has its own DID,
signs envelopes when it acts as an issuer or receiver, and is
subject to all protocol rules. Its distinguishing feature is the
declaration of `custodian_eligible: true` in its capability
document (`xift-1.0-spec-channel-1.md` §4.1) and the activation of one or more of the
three services above.

### 1.2 What the Trust Custodian Is NOT

The Custodian role is constrained by what it MUST NOT do. These
constraints preserve the integrity of XIFT's three-layer model and
its zero-trust principles.

- **MUST NOT access payloads.** All payloads remain encrypted
  end-to-end pair-wise between issuer and recipient. The Custodian
  routes metadata only; it cannot decrypt nor read payload content.
- **MUST NOT sign envelopes on behalf of others.** All envelopes
  carry signatures from their original issuers. A Custodian acting
  as a router does not re-sign; it forwards as-is.
- **MUST NOT apply policy.** Policy decisions (Cedar/Zen
  evaluation) happen at the receiver, never at the Custodian. The
  Custodian's job is to make discovery and revocation efficient,
  not to authorize.
- **MUST NOT issue or modify trust scores.** Trust scores come
  from the identity provider (Agent Mesh in the reference
  implementation). The Custodian reads them as inputs to ranking
  and gating, but does not compute them.
- **MUST NOT mediate Channel 7 (SCS) sessions.** SCS is direct
  agent-to-agent. The Custodian's role ends after discovery
  (Channels 5 and 6) returns endpoints.

### 1.3 Why This Role Exists

Three problems emerge when a mesh grows beyond approximately 50
agents (core §10):

- **Discovery explosion**: P2P semantic discovery requires N × N
  queries worst case. At 50 agents, this is 2,500 potential
  exchanges per discovery wave. The Custodian reduces this to N
  queries per agent against a single shared index.
- **Revocation polling overhead**: each issuer hosts its own BSL.
  Without aggregation, every receiver polls every issuer's BSL,
  multiplying network and compute load. The Custodian aggregates.
- **Handshake recomputation**: identity handshakes (200 ms budget)
  recomputed per session waste resources when an agent pair has
  recently authenticated. The Custodian caches.

The Custodian solves these without becoming a single point of
failure, because (a) it can be deactivated cleanly when the mesh
shrinks, (b) its services can be split across multiple agents
(§5), and (c) failover is defined (§4).

---

## 2. Activation State Machine

### 2.1 States

A custodian-eligible agent can be in one of four states:

| State             | Meaning                                                                                      |
| ----------------- | -------------------------------------------------------------------------------------------- |
| `dormant`         | Eligible but not active. Mesh size below activation threshold.                               |
| `warming`         | Transitioning from dormant to active. Bootstrapping indices.                                 |
| `active`          | Serving as Custodian. Indices populated; services operational.                               |
| `deactivating` | Transitioning from active to dormant. Draining state to other Custodians or to deactivation. |

State is local to each custodian-eligible agent; there is no
global state machine. Coordination happens through the discovery
mechanism and the capability document, which advertises the agent's
current state.

### 2.2 Transition Triggers

Transitions are driven by two thresholds from core §10:

- `mesh_custodian_activation_threshold = 25`
- `mesh_custodian_deactivation_threshold = 15`

A custodian-eligible agent monitors its **observed mesh size** —
the count of distinct DIDs from which it has received a valid,
signed capability document via Channel 1 (Discovery) within the
last observation window (default 5 minutes; see §11).

| From           | To             | Trigger                                                                                               |
| -------------- | -------------- | ----------------------------------------------------------------------------------------------------- |
| `dormant`      | `warming`      | Observed mesh size > 25 AND elected as primary (§3).                                                  |
| `warming`      | `active`       | Indices populated and services accepting requests.                                                    |
| `active`       | `deactivating` | Observed mesh size ≤ 15 AND another active Custodian remains, OR elected leader signals decommission. |
| `deactivating` | `dormant`      | All in-flight requests drained; indices handed off.                                                   |
| `active`       | `warming`      | Recovery from index corruption requiring rebuild.                                                     |

### 2.3 Hysteresis (Threshold 40 vs 50)

The deactivation threshold (40) is lower than the activation
threshold (50) intentionally. This 10-agent gap prevents flapping
when mesh size oscillates around the boundary. An agent that crosses
50 stays Custodian until the count falls to 40, regardless of
intermediate values.

### 2.4 Warming Procedure

When transitioning from `dormant` to `warming`, the elected
Custodian MUST:

1. Update its capability document to advertise its new state and
   service endpoints.
2. Re-publish the capability document via Channel 1 (Discovery) so
   all peers observe the change.
3. Pull capability documents from all known agents in the mesh
   (bootstrap the HNSW index).
4. Begin accepting BSL submissions from issuers that wish to
   delegate.
5. Begin accepting identity handshake cache lookups.
6. Once steps 3–5 are operational, transition to `active`.

The warming procedure SHOULD complete within
`custodian_warming_max_seconds` (default 60 s, see §11). If it
fails, the agent MUST revert to `dormant` and the next-eligible
agent is elected.

### 2.5 Deactivating Procedure

When transitioning from `active` to `deactivating`:

1. The Custodian publishes a `xift:custodian_deactivating` flag
   in its capability document.
2. New requests are redirected (HTTP 307 Temporary Redirect) to a
   designated successor or, if none, returned with `protocol:custodian:no_custodian_available`
   (106, warning).
3. In-flight requests are completed.
4. Indices are either handed off to the successor or dropped (in
   case of decommission to dormant without successor — appropriate
   when mesh shrinks below 40).
5. Once drained, the Custodian transitions to `dormant`.

Deactivating SHOULD complete within
`custodian_deactivating_max_seconds` (default 120 s). Requests
received during deactivating MAY be handled or refused
depending on the Custodian's drain policy.

### 2.6 Degraded P2P Mode

When the mesh has no active Custodian (because all
custodian-eligible agents are dormant, deactivating, or
unreachable), agents continue operating in **degraded P2P mode**:

- Channels 1–4 (Discovery, Handoff, Status Verification, Change
  Notification) continue normally.
- Channel 5 (SDR) operates in P2P direct mode
  (`xift-1.0-spec-channel-5.md` §2), capped at 50 contact attempts
  per query.
- Channel 6 (SIEA) operates in P2P broadcast mode if mesh size ≤
  20, otherwise SIEA is unavailable (subscribers receive
  `protocol:custodian:siea_unavailable_degraded_mode`, 106, warning).
- Channel 7 (SCS) is unaffected (it does not depend on Custodian).
- BSL polling reverts to per-issuer direct polling.
- Identity handshakes are recomputed per session (no cache).

Degraded mode is not a fault state — it is a documented operating
mode. Knowledge exchange is not blocking for agents' operational work;
the protocol degrades gracefully rather than blocks.

---

## 3. Leader Election and Multi-Custodian Topology

### 3.1 Election Algorithm

When multiple agents have `custodian_eligible: true` and mesh size
crosses the activation threshold, exactly one MUST become primary
**for each Custodian service**. The three services (Capability
Index, Status Aggregation, Identity Cache) elect independently,
allowing role distribution (§3.4).

Election uses **deterministic ordering by trust score, with DID
tiebreaker**:

```
For each service S in {capability_index, status_aggregation, identity_cache}:
    candidates = { agents with custodian_eligible: true AND state ∈ {dormant, warming} }
    primary = argmax_a∈candidates (
        trust_score(a),
        tiebreak: lowest_lexicographic(a.did)
    )
    primary transitions: dormant → warming
    all other candidates remain dormant for service S
```

This is **not Byzantine consensus**. It is **deterministic
capability-based selection**: every honest agent that observes the
same set of candidates and their trust scores reaches the same
conclusion locally. No voting protocol is needed.

### 3.2 Election Triggers

Election runs:

- When an agent transitions to `warming` and needs to verify it
  is still the elected primary.
- When a primary Custodian transitions to `deactivating` (the
  remaining eligible agents re-elect).
- When a primary Custodian becomes unreachable for more than
  `custodian_failover_timeout_seconds` (default 30 s).
- When the trust score of the current primary drops below the
  threshold `min_trust_score_for_custodian` (default 700).

### 3.3 Split-Brain Prevention

Because election is deterministic and local, split-brain is
**prevented by construction** when all agents observe the same data.
The failure mode is **observation skew**: two agents see different
subsets of the mesh and elect different primaries.

Mitigation:

- The capability document broadcast via Channel 1 includes
  `last_updated_at` and `version`. Agents that receive conflicting
  Custodian advertisements MUST prefer the most recent
  `last_updated_at` from the eligible agent with highest trust
  score among the candidates they have observed.
- If two `warming` Custodians for the same service publish
  capabilities, the one with lower trust score MUST observe the
  other and transition back to `dormant` within
  `custodian_split_brain_resolution_seconds` (default 15 s).
- Receivers MAY query multiple Custodians during the resolution
  window and accept the first valid response.

### 3.4 Multi-Custodian Topology: Service Distribution

The three Custodian services MAY be hosted by:

- **A single agent** (`unified topology`): all three services on
  one Custodian. Simplest deployment; appropriate for tight,
  single-tenant meshes.
- **Three different agents** (`distributed topology`): each service
  on its own primary. More resilient; failure of one service does
  not affect others.
- **Hybrid** (any of the 2⁻ topology variants): for example,
  Capability Index and Status Aggregation on one agent, Identity
  Cache on another.

Distribution is signaled in the capability document via per-service
`xift:custodian_service` flags:

```json
{
  "did": "did:web:org.example.com:agent:custodian-1",
  "custodian_eligible": true,
  "custodian_services_offered": {
    "capability_index": true,
    "status_aggregation": false,
    "identity_cache": true
  },
  "...": "..."
}
```

A deployment policy (not normative) decides which agent offers which
service. The election algorithm runs per service.

### 3.5 Custodian-of-Custodians (Out of Scope)

A future release will address inter-Custodian federation for
cross-tenant deployments. v1.0 assumes one Custodian topology per
mesh, with no federation between meshes.

---

## 4. Service 1: Capability Index

### 4.1 Purpose

Maintains a queryable index of signed capability documents from all
agents in the mesh. Serves SDR (`xift-1.0-spec-channel-5.md`) and
powers SIEA matching (`xift-1.0-spec-channel-6.md`).

### 4.2 Index Type

The index SHOULD be HNSW (Hierarchical Navigable Small World) for
sub-linear semantic retrieval. Alternatives (IVF, brute-force for
small meshes) are conformant if they meet the SLO of
`capability_query_latency_p95_ms` (default 500 ms, see §11).

The index stores, per capability document:

- The full `capability_vector` block (embedding, dimensions, model,
  bloom_filter, spec_embedding).
- A subset of `governance_constraints` for pre-filtering.
- The agent DID and its `trust_score` (refreshed via Δ-gossip).
- The capability document signature (for re-verification on serve).
- A `last_updated_at` timestamp.

### 4.3 Registration Wire Protocol

An agent registers or updates its capability document with the
Custodian via:

```
POST /xift/v1/custodian/capability_index
Content-Type: application/json
Authorization: Signature <signed-challenge>

{
  "registration_id": "01HY2...",
  "agent_did": "did:web:org.example.com:agent:alpha",
  "capability_document": { ... full document per channel-1 §4.1 ... },
  "registration_timestamp": "2026-05-21T10:00:00.000Z",
  "registration_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:agent:alpha#key-1"
}
```

The Custodian:

1. Verifies `registration_signature` and the embedded
   `capability_signature`.
2. Verifies `agent_did` resolves via the identity provider.
3. Verifies `agent_did`'s trust score is above
   `min_trust_score_for_indexing` (default 500).
4. Updates the index with the new capability document.
5. Echoes Δ-gossip notifications to other agents (§4.5).

Response:

```
HTTP 201 Created

{
  "registration_id": "01HY2...",
  "indexed_at": "2026-05-21T10:00:00.250Z",
  "expires_at": "2026-05-22T10:00:00.250Z",
  "custodian_signature": "<base64url-bytes>"
}
```

Registrations have a TTL (`capability_registration_ttl_seconds`,
default 86400 = 24 h). Agents MUST refresh before expiry.
Unrefreshed registrations are auto-removed.

### 4.4 Query Wire Protocol

The Custodian serves SDR queries (`xift-1.0-spec-channel-5.md` §3)
directly. When a querier sends a `XiftSemanticQuery` to the
Custodian's `xift_sdr_v1` endpoint, the Custodian:

1. Verifies query signature.
2. Verifies querier DID and trust score.
3. Pre-filters candidates by:
   - Bloom filter intersection (sub-millisecond).
   - `governance_constraints` compatibility.
   - Trust score thresholds.
4. Runs HNSW nearest-neighbor search on the pre-filtered set.
5. Computes composite scores (`xift-1.0-spec-channel-5.md` §7).
6. Returns top-K matches via `XiftSemanticResponse`.

### 4.5 Δ-Gossip for Index Updates

To minimize bandwidth in active meshes, capability changes are
propagated as **deltas** rather than full document re-publication:

```
POST /xift/v1/custodian/capability_index/delta
Content-Type: application/json

{
  "delta_id": "01HY3...",
  "agent_did": "did:web:org.example.com:agent:alpha",
  "base_capability_version": 11,
  "new_capability_version": 12,
  "changed_fields": {
    "capability_vector.embedding": "<new-base64>",
    "resource_costs.median_latency_ms": 250
  },
  "delta_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:agent:alpha#key-1"
}
```

The Custodian applies deltas atomically and propagates a
notification via Channel 4 (Change Notification) to subscribed
agents. Deltas SHOULD be ≤ 4 KB. Larger changes MUST trigger full
re-registration (§4.3).

### 4.6 Index Failover

When a Capability Index Custodian fails:

1. Failover timer (`custodian_failover_timeout_seconds`, default
   30 s) elapses.
2. Election runs again (§3.1); next-eligible agent is selected.
3. The new primary's `warming` procedure pulls all current
   capability documents from agents in the mesh.
4. Until the new primary reaches `active`, agents fall back to
   P2P direct mode for SDR (`xift-1.0-spec-channel-5.md` §2).

Index state is NOT replicated proactively to standby Custodians.
The rebuild from capability documents during warming is the
recovery mechanism. This is intentional: replication adds
complexity and the rebuild is bounded by
`custodian_warming_max_seconds`.

### 4.7 Capability Index SLO

| Metric                                    | Target           |
|-------------------------------------------|------------------|
| `capability_query_latency_p95_ms`         | ≤ 500 ms         |
| `capability_index_freshness_seconds`      | ≤ 60 s after delta |
| `capability_registration_success_rate`    | ≥ 99.9 %         |

---

## 5. Service 2: Status Aggregation

### 5.1 Purpose

Caches and serves W3C Bitstring Status Lists (BSL) from multiple
issuers, reducing the per-receiver polling load on issuers and
enabling efficient revocation propagation.

### 5.2 Delegation Model

Issuers delegate BSL hosting to the Custodian via:

```
POST /xift/v1/custodian/status_aggregation/delegate
Content-Type: application/json
Authorization: Signature <signed-challenge>

{
  "delegation_id": "01HY4...",
  "issuer_did": "did:web:org.example.com:issuer-1",
  "bsl_id": "list-2026-05",
  "bsl_url": "https://issuer.example.com/bsl/list-2026-05",
  "bsl_signature_verification_key_id": "did:web:org.example.com:issuer-1#key-1",
  "delegation_expires_at": "2026-06-21T10:00:00Z",
  "delegation_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:issuer-1#key-1"
}
```

The Custodian:

1. Verifies the delegation signature.
2. Verifies the issuer's trust score is above
   `min_trust_score_for_bsl_hosting` (default 700).
3. Fetches the current BSL from `bsl_url` and verifies it.
4. Begins serving the BSL at
   `/xift/v1/custodian/status_aggregation/{bsl_id}`.
5. Polls the issuer for BSL updates per `bsl_poll_interval_seconds`
   (default 60 s, configurable per issuer).

Delegation is **issuer-initiated and revocable**. Issuers MAY revoke
delegation via:

```
DELETE /xift/v1/custodian/status_aggregation/delegate/{delegation_id}
```

### 5.3 BSL Update Propagation

When the Custodian detects a BSL change (new bit set):

1. The Custodian verifies the new BSL's signature.
2. The Custodian updates its cached copy atomically.
3. The Custodian pushes a `bsl_updated` event via Channel 4 (Change
   Notification) to all subscribed receivers.
4. Subscribed receivers fetch the new BSL or process the event.

Update propagation SHOULD complete within
`bsl_propagation_target_seconds` (default 30 s).

### 5.4 Privacy Preservation

The Custodian MUST preserve the herd privacy property of BSL:

- The Custodian serves the **entire BSL bitstring**, not individual
  bit queries.
- The Custodian MUST NOT log which receiver queried which BSL
  beyond the minimum needed for rate limiting.
- The Custodian's cached BSL MUST satisfy
  `bsl_min_length_bits` (core §10, default 131,072).

### 5.5 Status Aggregation Failover

When a Status Aggregation Custodian fails:

1. Failover timer elapses.
2. Election runs.
3. The new primary's `warming` procedure re-fetches delegated
   BSLs from their respective issuers.
4. Until rebuild completes, receivers fall back to direct polling
   of each issuer's BSL.

### 5.6 Status Aggregation SLO

| Metric                                | Target           |
|---------------------------------------|------------------|
| `bsl_serve_latency_p95_ms`            | ≤ 100 ms         |
| `bsl_propagation_target_seconds`      | ≤ 30 s           |
| `bsl_aggregation_freshness_seconds`   | ≤ 60 s           |

---

## 6. Service 3: Identity Cache

### 6.1 Purpose

Caches mutual authentication handshake results so that agent pairs
that have recently authenticated can resume sessions without
recomputing the 200 ms handshake.

### 6.2 Cache Model

The Custodian maintains an indexed cache of handshake outcomes:

| Field                  | Purpose                                                  |
|------------------------|----------------------------------------------------------|
| `pair_id`              | Hash of (agent_did_a, agent_did_b) lexicographically sorted. |
| `handshake_timestamp`  | When the original handshake completed.                   |
| `expiry`               | TTL: `identity_handshake_cache_ttl_seconds` (core §10, default 900). |
| `trust_scores_at_handshake` | Snapshot of both agents' trust scores at handshake time. |
| `handshake_attestation` | Signed attestation from both parties confirming successful handshake. |

Critically: the Custodian stores **attestations**, not the session
keys themselves. Session keys remain in the endpoints' memory only.

### 6.3 Lookup Wire Protocol

An agent looking up a cached handshake:

```
GET /xift/v1/custodian/identity_cache/pair?did_a={did_a}&did_b={did_b}
Authorization: Signature <signed-challenge>
```

Response:

```
HTTP 200 OK

{
  "cached": true,
  "pair_id": "<hash>",
  "handshake_timestamp": "2026-05-21T09:55:00.000Z",
  "expiry": "2026-05-21T10:10:00.000Z",
  "trust_scores_at_handshake": {
    "did_a": 750,
    "did_b": 780
  },
  "handshake_attestation": "<base64url-bytes>",
  "custodian_signature": "<base64url-bytes>"
}
```

If `cached: true`, the requesting agent MAY skip the full
handshake and use the attestation as proof of recent successful
authentication. The agent MUST verify:

1. The Custodian's signature on the response.
2. The `handshake_attestation` is from a Custodian within
   acceptable trust score range.
3. The expiry has not passed.

### 6.4 Cache Invalidation

The cache MUST be invalidated when:

- The TTL expires (`identity_handshake_cache_ttl_seconds`).
- Either agent's trust score drops below the threshold that was
  acceptable at handshake time.
- Either agent's DID document is updated (key rotation event).
- The Custodian receives an explicit invalidation request from
  either agent.

Invalidation propagates via Channel 4 (Change Notification) to
agents that have recently used the cached entry.

### 6.5 Identity Cache Failover

When an Identity Cache Custodian fails:

1. Failover timer elapses.
2. Election runs.
3. The new primary starts with an empty cache. Agents fall back to
   fresh handshakes until the cache repopulates.

This is the simplest failover of the three services because the
cache contents are by definition transient.

### 6.6 Identity Cache SLO

| Metric                                | Target           |
|---------------------------------------|------------------|
| `identity_cache_lookup_latency_p95_ms` | ≤ 50 ms         |
| `identity_cache_hit_rate_target`      | ≥ 70 %           |
| `identity_cache_freshness_seconds`    | TTL-bounded      |

---

## 7. SIEA Fanout Control

The Custodian is the natural enforcement point for SIEA fanout
caps. `xift-1.0-spec-channel-6.md` §7 specifies
`siea_global_fanout_per_announcement_max` (default 100) as a hard
cap on how many subscribers any single announcement reaches.

### 7.1 Algorithm

When an announcement arrives, the Custodian:

1. Identifies all subscriptions whose interest semantically matches
   the announcement (via the Capability Index VCV).
2. Ranks the matches by composite score
   (`xift-1.0-spec-channel-5.md` §7).
3. If matches > cap, deprioritizes the lowest-scored matches.
4. Pushes notifications to the top-K matches.
5. For deprioritized matches, the Custodian SHOULD send a
   notification with `protocol:channel6:notification_deprioritized` (108)
   (`notification_deprioritized`) indicating that the match
   existed but was not delivered due to fanout cap.

### 7.2 Per-Subscriber Rate Limits

The Custodian also enforces the subscriber's declared
`max_match_notifications_per_hour` (`xift-1.0-spec-channel-6.md`
§3). When this is
reached:

- Further notifications to that subscriber are deferred until the
  next hour.
- The Custodian SHOULD inform the subscriber via `protocol:custodian:subscriber_rate_limit_reached` (103, warning)
  (`subscriber_rate_limit_reached`).

### 7.3 Fanout Audit

The Custodian MAY maintain an audit log of fanout decisions
(deprioritizations, deferrals) for compliance review by the
deployment. The audit log MUST NOT include subscriber-specific
content beyond the DID and the decision.

---

## 8. Wire Protocol Summary

### 8.1 Custodian Endpoints

A Custodian advertises the following endpoints in its capability
document (`xift-1.0-spec-channel-1.md` §4.1):

| Endpoint                                                  | Service                | Method   |
|-----------------------------------------------------------|------------------------|----------|
| `/xift/v1/custodian/capability_index`                     | Capability Index       | POST     |
| `/xift/v1/custodian/capability_index/delta`               | Capability Index       | POST     |
| `/xift/v1/custodian/capability_index/{agent_did}`         | Capability Index       | GET, DELETE |
| `/xift/v1/sdr`                                            | Capability Index       | POST (extends `xift-1.0-spec-channel-5.md`) |
| `/xift/v1/custodian/status_aggregation/delegate`          | Status Aggregation     | POST     |
| `/xift/v1/custodian/status_aggregation/delegate/{id}`     | Status Aggregation     | DELETE   |
| `/xift/v1/custodian/status_aggregation/{bsl_id}`          | Status Aggregation     | GET      |
| `/xift/v1/custodian/identity_cache/pair`                  | Identity Cache         | GET      |
| `/xift/v1/custodian/identity_cache/invalidate`            | Identity Cache         | POST     |
| `/xift/v1/custodian/state`                                | All                    | GET      |
| `/xift/v1/custodian/decommission`                         | All                    | POST     |

### 8.2 State Inquiry

Any agent can query a Custodian's current state:

```
GET /xift/v1/custodian/state
```

Response:

```json
{
  "custodian_did": "did:web:org.example.com:agent:custodian-1",
  "state": "active",
  "services_offered": {
    "capability_index": true,
    "status_aggregation": true,
    "identity_cache": true
  },
  "indexed_capabilities_count": 47,
  "aggregated_bsls_count": 12,
  "cached_handshake_pairs": 156,
  "observed_mesh_size": 52,
  "last_updated_at": "2026-05-21T10:00:00Z",
  "state_signature": "<base64url-bytes>"
}
```

This allows agents to verify Custodian health, observe mesh size,
and make routing decisions.

---

## 9. Threat Model Specific to Custodian

### 9.1 Adversaries

In addition to the core adversaries, the Custodian role introduces:

8. **Compromised Custodian** — An attacker controls the
   Custodian and attempts to bias discovery (filtering out
   legitimate agents, prioritizing malicious ones), poison the
   capability index, or withhold revocation propagation.
9. **Custodian impersonator** — An attacker advertises itself as
   `custodian_eligible: true` with falsified trust score to
   become elected.
10. **Index poisoner** — An attacker registers many sybil
    identities with crafted capability documents to flood the
    index.
11. **BSL withholder** — A delegated Custodian fails to propagate
    revocation updates, extending the validity of revoked grants.

### 9.2 Prevented

| Threat                                  | Mechanism                                                |
|-----------------------------------------|----------------------------------------------------------|
| Custodian forges capability documents   | Custodian re-signs nothing; documents carry original issuer signatures (§1.2). |
| Custodian decrypts payloads             | Payloads are HPKE-encrypted pair-wise; Custodian holds no decryption keys (§1.2). |
| Custodian-issued false trust scores     | Trust scores come from identity provider, not Custodian (§1.2). |
| Custodian-imposed policy decisions      | Policy is receiver's responsibility (§1.2).             |
| Custodian impersonator without trust    | Election requires trust score ≥ `min_trust_score_for_custodian`; verified at every election. |

### 9.3 Detected but Not Prevented

| Threat                                       | Detection                              |
|----------------------------------------------|----------------------------------------|
| Compromised Custodian filtering discovery    | Diverse Custodian queries (agents MAY query multiple) reveal inconsistencies. |
| Compromised Custodian withholding BSL update | Issuers continue serving BSL at original URL; receivers MAY fall back to direct poll. |
| Index poisoning via sybils                   | Trust score gating (§4.3) and external validation (`xift-1.0-spec-channel-1.md` §9). |
| Custodian latency degradation                | SLOs (§§4.7, 5.6, 6.6) are observable; failover triggers if exceeded. |

### 9.4 Defense in Depth: Multi-Custodian + Direct Fallback

The architecture provides three layers of defense against
Custodian compromise:

1. **Multi-Custodian topology** (§3.4): an attacker compromising
   one Custodian doesn't compromise the others.
2. **Direct fallback** (§2.6): agents can always bypass Custodians
   and operate P2P. This means a Custodian cannot become a true
   single point of failure or compromise.
3. **Trust score gating**: Custodians themselves are subject to
   the same trust score scrutiny as any agent. A misbehaving
   Custodian's trust score will degrade, eventually disqualifying
   it from election.

### 9.5 Out of Scope for Custodian v1

- Byzantine fault tolerance in Custodian elections (election is
  deterministic, not Byzantine-resilient).
- Cross-tenant Custodian federation (deferred to a future release).
- Custodian-of-Custodians (deferred to a future release).
- Custodian operation with non-trusted election peers
  (assumed: all custodian-eligible agents are within the same
  trust domain).

---

## 10. Custodian Error Codes

Custodian-specific conditions. Per the XIFT error model (core §12,
ADR-XIFT-ERROR-MODEL-001), the numeric `code` is the generic
operational routing axis and the `category` string is the source of
domain truth; the Custodian is identified by the `custodian` `domain`
segment, not by a numeric sub-range. The subsection heading fixes layer
and severity.

### 10.1 Protocol Errors

| Code | Category                                  | Description                                          |
|------|-------------------------------------------|------------------------------------------------------|
| 101 | `protocol:custodian:registration_signature_invalid` | Capability registration signature did not verify.    |
| 105 | `protocol:custodian:delta_base_version_unknown` | Δ-gossip delta references unknown base version.      |
| 101 | `protocol:custodian:delegation_signature_invalid` | BSL delegation signature did not verify.             |
| 101 | `protocol:custodian:identity_cache_attestation_invalid` | Cached handshake attestation did not verify.         |
| 106 | `protocol:custodian:custodian_deactivating` | Custodian is in `deactivating` state; request redirected. |
| 106 | `protocol:custodian:custodian_unavailable` | All Custodians of this type are unreachable.         |
| 105 | `protocol:custodian:registration_expired` | Capability registration TTL elapsed.                 |
| 105 | `protocol:custodian:bsl_delegation_expired` | BSL delegation TTL elapsed.                          |
| 108 | `protocol:custodian:index_quota_exceeded` | Custodian at capacity limit for indexed capabilities. |

### 10.2 Protocol Warnings

| Code | Category                                  | Description                                          |
|------|-------------------------------------------|------------------------------------------------------|
| 105 | `protocol:custodian:registration_nearing_expiry` | Capability registration within 10% of TTL.           |
| 105 | `protocol:custodian:bsl_delegation_nearing_expiry` | BSL delegation within 10% of TTL.                    |
| 108 | `protocol:custodian:custodian_load_high` | Custodian observing > 80% of its capacity limits.    |
| 106 | `protocol:custodian:degraded_p2p_mode` | No active Custodian; mesh in degraded P2P mode.      |
| 106 | `protocol:custodian:no_custodian_available` | No Custodian active for this service; degraded mode. |
| 106 | `protocol:custodian:siea_unavailable_degraded_mode` | SIEA cannot operate in current degraded mode.        |
| 103 | `protocol:custodian:subscriber_rate_limit_reached` | Per-subscriber notification rate limit reached.      |
| 106 | `protocol:custodian:index_lag_observed` | Custodian index lag exceeds `capability_index_freshness_seconds`. |

### 10.3 Policy Errors

| Code | Category                                  | Description                                          |
|------|-------------------------------------------|------------------------------------------------------|
| 206 | `policy:custodian:trust_score_insufficient_for_indexing` | Agent's trust score below `min_trust_score_for_indexing`. |
| 206 | `policy:custodian:trust_score_insufficient_for_delegation` | Issuer's trust score below `min_trust_score_for_bsl_hosting`. |

---

## 11. Normative Parameters

Extends core §10 and the channel normative-parameter sections
(`xift-1.0-spec-channel-5.md` §11, `xift-1.0-spec-channel-6.md`
§9, `xift-1.0-spec-channel-7.md` §11) with Custodian-specific
parameters.

| Parameter                                  | Default | Service            | Purpose                                                |
| ------------------------------------------ | ------- | ------------------ | ------------------------------------------------------ |
| `custodian_warming_max_seconds`            | 60      | All                | Max time for `dormant → warming → active` transition.  |
| `custodian_deactivating_max_seconds`       | 120     | All                | Max time for `active → deactivating → dormant`.     |
| `custodian_failover_timeout_seconds`       | 30      | All                | Time before election re-runs on unreachable Custodian. |
| `custodian_split_brain_resolution_seconds` | 15      | All                | Time for lower-trust Custodian to back down.           |
| `custodian_observation_window_seconds`     | 300     | All                | Window for observed mesh size calculation.             |
| `min_trust_score_for_custodian`            | 700     | All                | Minimum trust score to be elected Custodian.           |
| `min_trust_score_for_indexing`             | 500     | Capability Index   | Min trust score to be indexed.                         |
| `min_trust_score_for_bsl_hosting`          | 700     | Status Aggregation | Min trust score to delegate BSL hosting.               |
| `capability_registration_ttl_seconds`      | 86400   | Capability Index   | Capability document TTL in index.                      |
| `capability_query_latency_p95_ms`          | 500     | Capability Index   | SLO for query latency.                                 |
| `capability_index_freshness_seconds`       | 60      | Capability Index   | Max age of indexed data after delta.                   |
| `bsl_poll_interval_seconds`                | 60      | Status Aggregation | How often Custodian polls issuer BSL.                  |
| `bsl_propagation_target_seconds`           | 30      | Status Aggregation | SLO for revocation propagation.                        |
| `bsl_serve_latency_p95_ms`                 | 100     | Status Aggregation | SLO for BSL serve latency.                             |
| `identity_cache_lookup_latency_p95_ms`     | 50      | Identity Cache     | SLO for cache lookup.                                  |
| `identity_cache_hit_rate_target`           | 0.70    | Identity Cache     | Target hit rate.                                       |
| `siea_global_fanout_per_announcement_max`  | 100     | Fanout Control     | (From `xift-1.0-spec-channel-6.md` §9; restated here.) |

---

## 12. Conformance Test Categories

Extends `xift-1.0-spec-channels-general.md` §13 with
Custodian-specific suites:

| Suite  | Name                                 | Description                                                 |
| ------ | ------------------------------------ | ----------------------------------------------------------- |
| CUS.01 | Custodian state machine              | Verify all transitions in §2 work correctly.                |
| CUS.02 | Activation threshold enforcement     | Custodian activates at 25, deactivates at 15.               |
| CUS.03 | Hysteresis verification              | No flapping between 15 and 25 with oscillating mesh.        |
| CUS.04 | Leader election determinism          | Same inputs produce same elected primary across nodes.      |
| CUS.05 | Split-brain resolution               | Two warming Custodians for same service converge to one.    |
| CUS.06 | Capability registration + Δ-gossip   | Full lifecycle including deltas.                            |
| CUS.07 | BSL delegation and aggregation       | Issuer delegates, Custodian serves, change propagates.      |
| CUS.08 | Identity cache hit/miss/invalidation | Cache behaviour under TTL, key rotation, manual invalidate. |
| CUS.09 | Failover recovery                    | All three services recover within bounded time.             |
| CUS.10 | Degraded P2P mode                    | Mesh operates without active Custodian.                     |
| CUS.11 | Multi-Custodian topology             | Three services on three different agents work correctly.    |
| CUS.12 | SIEA fanout cap enforcement          | Cap respected; deprioritization signaled.                   |
| CUS.13 | Custodian threat resistance          | Compromised Custodian cannot decrypt, cannot forge.         |
| CUS.14 | Custodian deactivating drain         | In-flight requests complete; new requests redirected.       |
| CUS.15 | Mesh threshold transition            | Mesh lifecycle `Dormant ↔ Warmable ↔ Active`; activation at 25, deactivation at 15, P2P hard limit 50. (Formerly C32 in channels-general §13; overlaps CUS.02/CUS.03 — dedup pending.) |

---

## 13. Open Questions

1. **HNSW vs alternatives.** Should the spec mandate HNSW, or
   remain index-algorithm-agnostic? Currently RECOMMENDED but not
   MUST. Empirical benchmarking at 50–100 agent scale should
   inform future revisions.

2. **Δ-gossip propagation topology.** Should deltas propagate
   through Channel 4 (Change Notification) only, or also peer-to-peer
   gossip between Custodians (when multiple exist)? A future
   federation release may require the latter.

3. **Cross-Custodian state sync.** When three Custodians serve
   distinct services, is cross-service state synchronization
   needed? Currently each service operates independently.

4. **Custodian trust score weighting.** Should serving as
   Custodian increase or decrease an agent's trust score? Arguments
   exist both ways (reliability vs concentration risk).

5. **Delegated BSL key rotation.** When an issuer rotates its
   signing key, how does the Custodian handle the transition? A
   re-delegation flow is implicit; should it be explicit?

6. **Custodian observability standards.** Should Custodians
   expose Prometheus-format metrics endpoint? Currently
   `/xift/v1/custodian/state` provides JSON state; metrics format
   left to implementation.

7. **Multi-Custodian role rebalancing.** When mesh size grows from
   50 to 100, should additional Custodians come online
   automatically (e.g., one Custodian per 50 agents)? Currently
   one set of three services covers the whole mesh.

8. **Future-release inter-Custodian federation.** Cross-tenant Custodian
   federation, Custodian-of-Custodians, gossip protocols for
   wide-area replication.

---

## Appendix A — State Machine Diagram (Textual)

```
                    +-------------------+
                    |     dormant       |
                    | (mesh ≤ 50 OR    |
                    |  not elected)     |
                    +---------+---------+
                              |
                  mesh > 50   |   drain complete
                  AND elected |   OR mesh ≤ 40
                              v
                    +---------+---------+
                    |    warming      |
                    | (bootstrapping    |
                    |  indices)         |
                    +---------+---------+
                              |
                              | indices ready
                              v
                    +---------+---------+
                    |     active        |
                    | (serving Channels |<-----+
                    |  5, 6 indirectly) |      | failover detected
                    +---------+---------+      | re-elect required
                              |                |
                  mesh ≤ 40   |                |
                  OR elected  |                |
                  to step down|                |
                              v                |
                    +---------+---------+      |
                    | deactivating   |      |
                    | (draining)        |      |
                    +---------+---------+      |
                              |                |
                              | drain complete |
                              v                |
                    +---------+---------+      |
                    |     dormant       |------+
                    +-------------------+
```

---

## Appendix B — Wire Protocol Examples

### B.1 Custodian Capability Document Excerpt

```json
{
  "did": "did:web:org.example.com:agent:custodian-1",
  "name": "Mesh Custodian (Primary)",
  "version": 3,
  "endpoints": {
    "xift_handoff_v1": "https://custodian.example.com/xift/v1/envelopes",
    "xift_discovery_v1": "https://custodian.example.com/xift/v1/discovery",
    "xift_sdr_v1": "https://custodian.example.com/xift/v1/sdr",
    "xift_custodian_capability_index_v1": "https://custodian.example.com/xift/v1/custodian/capability_index",
    "xift_custodian_status_aggregation_v1": "https://custodian.example.com/xift/v1/custodian/status_aggregation",
    "xift_custodian_identity_cache_v1": "https://custodian.example.com/xift/v1/custodian/identity_cache",
    "xift_custodian_state_v1": "https://custodian.example.com/xift/v1/custodian/state"
  },
  "supported_extensions": [
    "governance", "provenance", "encryption", "revocation", "quality"
  ],
  "custodian_eligible": true,
  "custodian_state": "active",
  "custodian_services_offered": {
    "capability_index": true,
    "status_aggregation": true,
    "identity_cache": true
  },
  "custodian_metadata": {
    "indexed_capabilities_count": 47,
    "aggregated_bsls_count": 12,
    "cached_handshake_pairs": 156,
    "observed_mesh_size": 52,
    "activated_at": "2026-05-21T09:30:00Z"
  },
  "capability_signature": "<base64url-bytes>",
  "signing_key_id": "did:web:org.example.com:agent:custodian-1#key-1"
}
```

### B.2 Capability Registration Flow

```
Agent Alpha                   Custodian-1
   |                               |
   |-- POST /capability_index ---->|
   |   (capability_document,       |
   |    registration_signature)    |
   |                               | verify signatures
   |                               | verify trust score
   |                               | index document
   |                               | compute deltas
   |                               |
   |<-- 201 Created ---------------|
   |   (indexed_at, expires_at,    |
   |    custodian_signature)       |
   |                               |
   |                               |-- Channel 4 broadcast ->
   |                               |   (capability_indexed event)
   |                               |
```

### B.3 SIEA Fanout Decision Flow

```
Announcer                Custodian-1            Top-K Subscribers           Deprioritized
   |                         |                          |                         |
   |-- POST announcement --->|                          |                         |
   |                         | semantic match           |                         |
   |                         | rank by composite_score  |                         |
   |                         | apply fanout cap         |                         |
   |                         |                          |                         |
   |                         |-- match_notification --->|                         |
   |                         |   (top-K)                |                         |
   |                         |                          |                         |
   |                         |-- match_notification --> notification_deprioritized ->|
   |                         |   (deprioritized)        |   notification_deprioritized
   |                         |                          |                         |
```

---

## Appendix C — Glossary (Custodian-Specific)

| Term                          | Meaning                                                          |
|-------------------------------|------------------------------------------------------------------|
| Knowledge                     | The substance XIFT exchanges: facts, patterns, rules, summaries, observations and inferences produced by an agent and consumable by another. |
| Knowledge artifact            | A concrete unit of knowledge wrapped in a `KnowledgeObject` envelope for exchange. |
| KnowledgeObject               | The canonical envelope of XIFT v1.0. (Predecessor name: `MemoryObject`.) |
| Memory (repository)           | An agent's internal repository where knowledge is stored, organized, and decayed. Distinct from the protocol. |
| Memory stratum                | A subdivision of an agent's memory repository following CoALA: working, episodic, semantic, procedural. Declared by the envelope's `memory_scope` field. |
| Experience                    | One kind of knowledge — knowledge acquired during the operation of the agent's Working Self. Typically lands in episodic or working strata. |
| Working Self                  | The operational self of an agent executing tasks. The source of experiences. |
| Custodian                     | Specialized agent role per §1.1.                                |
| Custodian-eligible            | Agent with `custodian_eligible: true` in capability document.   |
| Capability Index Service      | The HNSW-backed semantic discovery index (§4).                  |
| Status Aggregation Service    | The BSL caching and propagation service (§5).                   |
| Identity Cache Service        | The handshake attestation cache (§6).                           |
| Δ-gossip                      | Delta-encoded capability update propagation (§4.5).             |
| Unified topology              | Single Custodian hosting all three services (§3.4).             |
| Distributed topology          | Three Custodians, one per service (§3.4).                       |
| Hybrid topology               | Mixed allocation of services across Custodians (§3.4).          |
| Degraded P2P mode             | Mesh operating without active Custodian (§2.6).                 |
| Observed mesh size            | Locally counted distinct DIDs in observation window.            |
| Hysteresis                    | 50-40 gap preventing activation/deactivation flapping.          |

---

## Appendix D — Change Log

> **Change history:** consolidated in [`spec/CHANGELOG.md`](./CHANGELOG.md) (newest first).

