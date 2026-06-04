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

This repository is **public** and holds the normative specifications,
the interoperability contracts, and the Rust reference implementation.
Planning artifacts — ADRs, research, steering documents, and Kiro
tasks — live in the **private** sibling repository `xift-internal`
(see [Two-repo layout](#two-repo-layout)).

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
- **7 channels, 6 extensions.** Channels handle wire flows
  (discovery, handoff, revocation check, notifications, semantic
  search, interest matching, conversational sessions). Extensions
  add opt-in metadata blocks to the envelope. Four are **core
  extensions** every conformant implementation MUST recognise
  (`governance`, `provenance`, `encryption`, `revocation`); two are
  **silently ignorable** (`quality`, `ontology`).

## Repository layout

| Path | Contents |
|---|---|
| `spec/` | Normative specifications (core, channels, extensions, custodian, interop, error registry, threat model, glossary). |
| `contracts/` | Interoperability contracts: OpenAPI (`openapi/`), AsyncAPI (`asyncapi/`), and JSON Schema (`schemas/`, including per-extension schemas). |
| `rust/` | Cargo workspace for the Rust reference implementation (`xift-*` crates). Currently scaffolding — crate skeletons are in place, implementation pending. |
| `tests/` | Conformance fixtures (`compliance/conformance.yaml`) and integration test scaffolding. |
| `examples/` | Runnable usage examples (minimal publisher/consumer, OpenClaw↔Claude handoff). |
| `docs/` | Reader-facing guides (getting started, implementing XIFT, threat-model deep dive). |
| `policies/` | Cedar and JDM (Zen) policy skeletons referenced by the governance extension. |
| `tools/` | Repository tooling — see `tools/README.md`. |

## Two-repo layout

- `xift` (this repo, public): specs, contracts, `rust/` reference impl, examples, tests.
- `xift-internal` (private sibling): ADRs, research, steering docs, `.kiro/` tasks.

**Public/private boundary (strict).** Public files reference an ADR by
**ID only** (e.g. "per ADR-XIFT-ERROR-MODEL-001"), never its rationale.
ADR prose, research notes, and internal deliberation never land here.

## Document map

All paths are under `spec/`.

### Core (1 file)

| File | Description |
|---|---|
| `xift-1_0-spec-core.md` | Core protocol: envelope schema (`KnowledgeObject`), three-layer model, identity layer, lineage rules, normative parameters, error model, threat model, cryptography. §4 indexes the extensions. |

### Channels (8 files, in `spec/channels/`)

| File | Description |
|---|---|
| `xift-1_0-spec-channels-general.md` | Cross-channel conventions: transport, authentication, back-pressure, identity handshake primitive, conformance test categories (CORE/C1–C7/CX/CUS semantic IDs), reserved billing-related error codes. |
| `xift-1_0-spec-channel-1.md` | Channel 1 — Discovery & Handshake. Capability advertisement (baseline + extended), VCV, governance constraints, identity handshake flow. |
| `xift-1_0-spec-channel-2.md` | Channel 2 — Envelope Handoff. Inline and content-ref (dial-back) modes, storage-mediated handoff, egress DLP, billing-aware receipt. |
| `xift-1_0-spec-channel-3.md` | Channel 3 — Status Verification (BSL Pull). W3C Bitstring Status List, caching, fail-closed, herd privacy. |
| `xift-1_0-spec-channel-4.md` | Channel 4 — Change Notification (SSE Push). Revocation events, capability changes, Custodian state, keepalive, reconnection. |
| `xift-1_0-spec-channel-5.md` | Channel 5 — Semantic Discovery Request (SDR). Embedding-based search, composite scoring, preview redaction. |
| `xift-1_0-spec-channel-6.md` | Channel 6 — Semantic Interest & Experience Announce (SIEA). Persistent subscriptions, announcements, match notifications, fanout control. |
| `xift-1_0-spec-channel-7.md` | Channel 7 — Sequential Conversation Session (SCS). Multi-turn sessions, smart clustering, consensus voting, session journals. |

### Extensions (6 files, in `spec/extensions/`)

| File | Tier | Description |
|---|---|---|
| `xift-1_0-spec-extension-governance.md` | core | Consent, classification, PII classification, purpose of use, lineage policy, policy tags. |
| `xift-1_0-spec-extension-provenance.md` | core | Derivation lineage, derivation types, anonymization evidence. |
| `xift-1_0-spec-extension-encryption.md` | core | HPKE (RFC 9180), mandatory for sensitive/restricted, scheme negotiation. |
| `xift-1_0-spec-extension-revocation.md` | core | BSL binding, two-layer revocation (TTL + BSL), fail-closed, herd privacy. |
| `xift-1_0-spec-extension-quality.md` | ignorable | Metrics, confidence, profile. Silently ignorable by non-supporting receivers. |
| `xift-1_0-spec-extension-ontology.md` | ignorable | Governed vocabulary descriptor and reciprocal alignment; SHOULD accompany Channel 6. Silently ignorable. |

### Custodian, interop, and cross-cutting (5 files, in `spec/`)

| File | Description |
|---|---|
| `xift-1_0-custodian.md` | Trust Custodian: Capability Index, BSL Aggregation, Identity Cache. State machine, election, failover, Δ-gossip, threat model. |
| `xift-1_0-interop.md` | Interoperability Profile: A2A adapter, MCP adapter, VCV-based tool discovery. |
| `xift-error-taxonomy.md` | Authoritative category registry: per code `layer`, `severity`, `category`, `retryable`, `emitter`, `observer`, `trigger`, `remedy`, `source`, `status`. Cited normatively by the channel specs. |
| `threat-model.md` | Consolidated threat model across channels and extensions. |
| `glossary.md` | Memgator + XIFT glossary (two sections: Memgator terms and XIFT Protocol terms). |

### Contracts (`contracts/`)

| Path | Description |
|---|---|
| `openapi/xift-api.yaml` | OpenAPI description of the synchronous (request/response) surface. |
| `asyncapi/xift-events.async.yaml` | AsyncAPI description of the event/notification surface. |
| `schemas/` | JSON Schemas for the envelope, handshake, capability advertisement, grant/delegation, status list, and semantic query/response. |
| `schemas/extensions/` | One JSON Schema per extension (`governance`, `provenance`, `encryption`, `revocation`, `quality`, `ontology`). |

### Reference implementation (`rust/`)

A single Cargo workspace. Crate skeletons currently in place
(implementation pending):

| Crate dir | Role |
|---|---|
| `xift-core` | Envelope, crypto, error model, shared types. |
| `xift-client` | Initiating/consuming side of the channels. |
| `xift-server` | Serving/publishing side of the channels. |
| `xift-custodian` | Trust Custodian services. |
| `xift-adapter-mcp` | MCP interoperability adapter. |
| `xift-adapter-a2a` | A2A interoperability adapter. |

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
| **Extension** | One of 6 opt-in envelope metadata blocks (governance, provenance, encryption, revocation, quality, ontology). |

## Error model

The numeric `code` is a small immutable per-layer routing set; the
`layer:domain:sub_category` `category` string is the source of domain
truth. There is no numeric `financial` layer — billing is
`policy:financial:*`. Error objects are flat and signed in full
(Ed25519 over JCS / RFC 8785). The authoritative category registry is
`spec/xift-error-taxonomy.md`. See ADR-XIFT-ERROR-MODEL-001,
-SIGNING-001, and -MIGRATION-001 (in `xift-internal`).

## Status

All v1.0 specifications are `draft`. The contracts track the specs;
the Rust workspace is scaffolding. Authoritative change history is git;
each content directory keeps a newest-first `CHANGELOG.md`
(`spec/`, `contracts/`, `rust/`).
