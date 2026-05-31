# XIFT 1.0 — Project Overview

## What is XIFT?

**XIFT** (eXperience Interchange for Federated Trusts) is a
peer-to-peer protocol for the **governed exchange of knowledge**
between AI agents. It fills the gap between vertical tool-use (MCP)
and horizontal task negotiation (A2A) by providing cryptographic
ownership, granular consent, active revocation, and lineage tracking
for every knowledge artifact that crosses an agent boundary.

XIFT is part of the **Memgator** project (open-source, Rust) but is
designed to be **host-agnostic**: any AI agent runtime (Memgator,
OpenClaw, custom shells) can embed the XIFT crates and participate in
an XIFT mesh.

## Key Design Decisions

- **Knowledge, not memory.** XIFT exchanges *knowledge* (facts,
  patterns, rules, summaries, observations, inferences). *Memory* is
  the host's internal repository. *Experience* is one kind of
  knowledge — acquired during the agent's operation.
- **Libraries, not daemon.** The reference implementation is a Cargo
  workspace of embeddable Rust crates (`xift-*`), not a standalone
  process.
- **Host traits.** XIFT defines 10 traits (`IdentityProvider`,
  `TrustScoreProvider`, `DIDResolver`, `HandshakeMethod`,
  `KeyProvider`, `AuditSink`, `TelemetrySink`, `Supervisor`, `Clock`,
  `Configuration`) that the host must implement. The protocol does
  not depend on any specific identity stack, key manager, or storage
  backend.
- **7 channels, 5 extensions.** Channels handle wire flows
  (discovery, handoff, revocation check, notifications, semantic
  search, interest matching, conversational sessions). Extensions
  add opt-in metadata blocks to the envelope (governance, provenance,
  encryption, revocation, quality).

## Document Map

### Normative Specifications (16 files)

| File | Description |
|---|---|
| `xift-1.0-spec-core.md` | Core protocol: envelope schema (`KnowledgeObject`), three-layer model, identity layer, lineage rules, normative parameters, error model, threat model, cryptography. Extensions §4 is an index pointing to the 5 extension docs. |
| `xift-1.0-spec-channels-general.md` | Cross-channel conventions: transport, authentication, back-pressure, identity handshake primitive, conformance test categories C20–C33, billing-related error codes (reserved). |
| `xift-1.0-spec-channel-1.md` | Channel 1: Discovery & Handshake. Capability advertisement (baseline + extended), VCV, governance constraints, identity handshake flow. |
| `xift-1.0-spec-channel-2.md` | Channel 2: Envelope Handoff. Inline and content-ref (dial-back) modes, storage-mediated handoff, egress DLP, billing-aware receipt. |
| `xift-1.0-spec-channel-3.md` | Channel 3: Status Verification (BSL Pull). W3C Bitstring Status List, caching, fail-closed, herd privacy. |
| `xift-1.0-spec-channel-4.md` | Channel 4: Change Notification (SSE Push). Revocation events, capability changes, Custodian state, keepalive, reconnection. |
| `xift-1.0-spec-channel-5.md` | Channel 5: Semantic Discovery Request (SDR). Embedding-based search, composite scoring, preview redaction. |
| `xift-1.0-spec-channel-6.md` | Channel 6: Semantic Interest & Experience Announce (SIEA). Persistent subscriptions, announcements, match notifications, fanout control. |
| `xift-1.0-spec-channel-7.md` | Channel 7: Sequential Conversation Session (SCS). Multi-turn sessions, smart clustering, consensus voting, session journals. |
| `xift-1.0-spec-extension-governance.md` | Extension: `governance`. Consent, classification, PII classification, purpose of use, lineage policy, policy tags. |
| `xift-1.0-spec-extension-provenance.md` | Extension: `provenance`. Derivation lineage, 6 derivation types, anonymization evidence. |
| `xift-1.0-spec-extension-encryption.md` | Extension: `encryption`. HPKE (RFC 9180), mandatory for sensitive/restricted, scheme negotiation. |
| `xift-1.0-spec-extension-revocation.md` | Extension: `revocation`. BSL binding, two-layer revocation (TTL + BSL), fail-closed, herd privacy. |
| `xift-1.0-spec-extension-quality.md` | Extension: `quality`. Metrics, confidence, profile. Silently ignorable by non-supporting receivers. |
| `xift-custodian-1.0.md` | Trust Custodian: Capability Index, BSL Aggregation, Identity Cache. State machine, election, failover, Δ-gossip, threat model. |
| `xift-interop-1.0.md` | Interoperability Profile: A2A adapter, MCP adapter, VCV-based tool discovery. |

### Reference Implementation Architecture (1 file)

| File | Description |
|---|---|
| `xift-reference-implementation-architecture.md` | v0.2. Single Cargo workspace `xift-rs`. Crate tree, host traits, Cedar/Zen integration, observability, Custodian crates, fitness functions FF-01..FF-17. Behavioural Contracts (pre-EARS) per section. |

### Steering Documents for EARS Generation (9 files)

| File | Description |
|---|---|
| `xift-domain-vocabulary.md` | ~80 domain entities with canonical names, Rust shapes, invariants, restrictions, sources. |
| `xift-actor-catalogue.md` | Closed set of legitimate EARS subjects: wire actors, channel handlers, Custodian components, transport layers, policy/crypto, host traits, quality/process. |
| `xift-non-goals.md` | 20 explicit non-goals with boundary tests. |
| `xift-event-vocabulary.md` | ~110 canonical events in 10 clusters with emitters, observers, data fields, triggers. |
| `xift-state-vocabulary.md` | 13 state machines with transitions, per-state invariants, entry/exit actions. |
| `xift-error-taxonomy.md` | 96 error/warning codes consolidated from all specs with trigger conditions, retryability, remedies. |
| `xift-budgets-and-thresholds.md` | ~80 numerical parameters as single source of truth. |
| `xift-conformance-matrix.md` | 73 conformance cases mapped to subjects, triggers, expected outcomes, budgets, fitness functions. |
| `xift-decision-flowcharts.md` | 8 Mermaid decision diagrams for the most complex protocol paths. |

### Glossary (project-level, in memgator-internal)

| File | Description |
|---|---|
| `glossary.md` | Memgator + XIFT glossary. Two sections: Memgator terms and XIFT Protocol terms. |

## Terminology Quick Reference

| Term | Meaning |
|---|---|
| **Knowledge** | The substance XIFT exchanges: facts, patterns, rules, summaries, observations, inferences. |
| **KnowledgeObject** | The canonical envelope. Predecessor name: `MemoryObject`. |
| **Memory** | The host's internal repository (CoALA strata: working, episodic, semantic, procedural). |
| **Experience** | One kind of knowledge — acquired during the agent's Working Self operation. |
| **Host** | The process embedding the XIFT crates (Memgator, OpenClaw, a custom agent shell, a test harness). |
| **Custodian** | Optional agent role offering Capability Index, BSL Aggregation, and Identity Cache services. |
| **Channel** | One of 7 wire-flow protocols (Discovery, Handoff, BSL Pull, SSE Push, SDR, SIEA, SCS). |
| **Extension** | One of 5 opt-in envelope metadata blocks (governance, provenance, encryption, revocation, quality). |

## Version History

| Date | Milestone |
|---|---|
| 2026-05-18 | XIFT research thread originated; initial glossary. |
| 2026-05-20 | Core spec v3.0 (monolithic). |
| 2026-05-21 | Core spec v3.1; channel split; Custodian spec; Interop profile. |
| 2026-05-23 | Per-channel specs; channels-general; billing error codes. |
| 2026-05-24 | Knowledge paradigm shift; extension extraction; host-traits refactor; 9 steering docs; Phase 1/2/3 elimination; status normalisation to v1.0. |
