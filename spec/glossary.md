# Memgator & XIFT Glossary

Definitions of Memgator-specific terms, XIFT-specific terms, and
project-specific uses of generic terms. Universally known terms
(LLM, REST, JSON) are not included unless they have a
Memgator/XIFT-specific meaning.

The glossary is organised in four sections:

1. **Core Concepts** — Knowledge, identity, envelope, three-layer model.
2. **Governance, Lineage & Security** — Consent, revocation, classification, egress, policy.
3. **Mesh, Discovery & Channels** — Custodian, channels, semantic search, sessions, observability.
4. **Memgator-Specific Terms** — Terms specific to the Memgator host implementation.

Memgator-only terms (not part of the XIFT protocol) are marked
**(Memgator)**.

---

## 1. Core Concepts

**XIFT — eXperience Interchange for Federated Trusts.** A peer-to-peer protocol for the governed exchange of knowledge between AI agents. The name retains "experience" because experience exchange was the historical motivating use case; *knowledge* is the more general substrate that the protocol carries, of which experience is one kind. See `xift-1.0-spec-core.md` §0.1, §1.2.

**Knowledge.** The substance XIFT exchanges: facts, patterns, rules, summaries, observations and inferences produced by an agent and consumable by another. Distinct from **Memory** (the host's internal repository) and from **Experience** (one *kind* of knowledge).

**Knowledge Artifact.** A concrete unit of knowledge wrapped in a `KnowledgeObject` envelope for exchange. See `xift-1.0-spec-core.md` Appendix D.

**KnowledgeObject.** The canonical envelope of XIFT v1.0. Carries mandatory blocks (Identity, Operational, Content, Security) plus zero or more extension blocks. Always signed by the issuer; always carries `envelope_id`. Predecessor name: `MemoryObject`. See `xift-1.0-spec-core.md` §3.

**Memory (Repository).** The host's internal repository where knowledge is stored, organised and decayed. Memgator organises memory into CoALA strata; other hosts may use different models. XIFT only sees the `memory_scope` field declared on the envelope. Distinct from the protocol and from any specific XIFT crate.

**Memory Stratum.** A subdivision of the host's memory repository following CoALA: **working** (short-lived single-turn context), **episodic** (time-stamped events and experiences), **semantic** (facts and concepts abstracted from episodes), **procedural** (rules, heuristics, learned procedures). Declared by the envelope's `memory_scope` wire field. See **CoALA**.

**Experience.** One kind of knowledge — knowledge acquired during the operation of the agent's **Working Self**. Typically lands in episodic or working strata; may be distilled to semantic or procedural.

**Working Self.** The operational self of an agent executing tasks. The source of experiences. Not exposed on the XIFT wire; named for the actor in `xift-actor-catalogue.md` §1.

**Three-Layer Model.** The strict separation between the **Transport Layer** (deterministic SDK; handles wire-format, signing, routing), the **Policy Layer** (host's rule engine — Cedar for authorization, Zen for scoring), and the **Payload Layer** (opaque to the protocol; semantics owned by the host). See `xift-1.0-spec-core.md` §2.

**Host.** A process embedding the XIFT crates: an AI agent runtime such as OpenClaw, a memory governance layer such as Memgator, a custom agent shell, or a test harness. The host provides implementations of the traits in `xift-host-traits`. See `xift-reference-implementation-architecture.md` §0.3, §0.7, §3.

**Host Traits.** The 10 traits in `xift-host-traits` that the XIFT crates require from the host: `IdentityProvider`, `TrustScoreProvider`, `DIDResolver`, `HandshakeMethod`, `KeyProvider`, `AuditSink`, `TelemetrySink`, `Supervisor`, `Clock`, `Configuration`. See `xift-reference-implementation-architecture.md` §3.

**HostBindings.** The aggregate type defined in `xift-host-traits` that bundles the host trait implementations and is passed to each channel handler at construction time. See `xift-reference-implementation-architecture.md` §3.5.

**DID — Decentralized Identifier.** W3C-standard identifier for an agent. In Memgator, issued by Agent Mesh. In XIFT, consumed via the `IdentityProvider` and `DIDResolver` host traits. Tagged on every knowledge artifact. Three DIDs in distinct roles: `agent_did` (emitting agent), `recipient_did` (authorised receiver), `owner_did` (data subject, in `governance` extension). A fourth, `derivation_agent_did`, appears in `provenance`. See `xift-1.0-spec-core.md` §8.2.

**Trust Score.** Integer 0–1000 consumed by XIFT from the host's `TrustScoreProvider`. Threshold semantics: 500 baseline (default, tunable), 600 indexing, 700 sensitive/Custodian. See `xift-budgets-and-thresholds.md` §5.

**CoALA.** Cognitive Architectures for Language Agents — the framework whose memory taxonomy (working / episodic / semantic / procedural) Memgator adopts and XIFT references via the `memory_scope` wire field.

**Envelope Status.** The lifecycle state of a `KnowledgeObject` on the wire. Four values: `proposed`, `shipped`, `blocked`, `failed`. See `xift-1.0-spec-core.md` §3.3.2.

**Next Action.** Non-binding hint from issuer to receiver on how to process the payload: `store`, `promote`, `distill`, `discard`. See `xift-1.0-spec-core.md` §3.3.2.

**Issuer.** Wire-level actor: the agent creating and signing a `KnowledgeObject`. See `xift-1.0-spec-core.md` Appendix D; `xift-actor-catalogue.md` §1 (as `Sender`).

**Receiver.** Wire-level actor: the agent identified by `recipient_did` that accepts or rejects inbound envelopes after policy evaluation. See `xift-1.0-spec-core.md` Appendix D; `xift-actor-catalogue.md` §1.

**JCS — JSON Canonicalization Scheme.** RFC 8785 canonicalization applied to the envelope before signing. Ensures deterministic serialization for signature verification. See `xift-1.0-spec-core.md` §3.1, §8.3.

**ADR — Architecture Decision Record.** A markdown document recording a single architectural decision, its context, rationale, alternatives, and consequences. Immutable after acceptance; superseded by new ADRs.

**EARS — Easy Approach to Requirements Syntax.** The structured requirements format used across the XIFT steering documents. Subjects resolve in `xift-actor-catalogue.md`, states in `xift-state-vocabulary.md`, events in `xift-event-vocabulary.md`, and error codes in `xift-error-taxonomy.md`.

**Fitness Function.** Automated test that enforces an architectural characteristic. Examples: hot-path latency p95 < 0.8 ms (FF-03), no vendor SDK in domain (FF-04), audit coverage ≥ 99% (FF-09). See `xift-reference-implementation-architecture.md` §9.2.

---

## 2. Governance, Lineage & Security

**Grant (XIFT Grant).** Verifiable Credential issued by an agent to authorise a specific consumer (or scope) to access a specific subset of its published knowledge. Carries TTL, scope, status list reference, consumer DID, and redaction hash. Two-layer revocation: passive (TTL expiry) and active (Bitstring Status List). See `xift-1.0-spec-extension-revocation.md`.

**BSL — Bitstring Status List.** W3C v1.0 Recommendation (May 2025) used by XIFT for immediate revocation. Each issuer maintains a compressed bitstring where every grant has a position; bit = 1 means revoked. Privacy-preserving (herd privacy via minimum 131,072-bit length), CDN-distributable, O(1) verification. See `xift-1.0-spec-extension-revocation.md` §1.

**Two-Layer Revocation.** The combination of passive revocation (TTL expiry via `consent_until`) and active revocation (BSL bit flip). Both layers are enforced; either one alone is sufficient to revoke. See `xift-1.0-spec-extension-governance.md` §3.7 and `xift-1.0-spec-extension-revocation.md` §1.

**Fail-Closed.** Design principle (core §1.1, Principle 5): any verification, authorization or identity failure results in denial, never permissive fallback. Applied across all channels, especially Channel 3 BSL checks. See `xift-1.0-spec-channels-general.md` Appendix D.

**Herd Privacy.** BSL property: the receiver hides which grant it is querying because the full bitstring is fetched, not a specific bit. Preserved by the minimum 131,072-bit length requirement. See `xift-1.0-spec-channel-3.md` §7.

**Classification.** Five-level sensitivity lattice declared on the envelope by the issuer, ordered from least to most restrictive: `public` < `internal` < `confidential` < `sensitive` < `restricted`. Domain-agnostic information security levels. When `≥ sensitive`, encryption is MANDATORY (`protocol:encryption:mandatory_encryption_missing`, 105). See `xift-1.0-spec-extension-governance.md` §3.3.

**PII Classification.** Four-level identifiability state, orthogonal to classification: `personal-identifiable`, `pseudonymized`, `anonymized`, `non-personal`. When absent, defaults to `personal-identifiable` (fail-safe). See `xift-1.0-spec-extension-governance.md` §3.4.

**Purpose of Use.** Declared reason the recipient is authorised to use the artifact: `service-delivery`, `operations`, `research`, `audit`, `training`, `debugging`, `marketing`. Cryptographically bound by the envelope signature. See `xift-1.0-spec-extension-governance.md` §3.5.

**Agent Role.** OPTIONAL field in the `governance` extension enabling RBAC-style policy shortcuts. Not a canonical taxonomy; values are agreed between participants or within a trust domain. Cryptographically bound by the envelope signature. See `xift-1.0-spec-extension-governance.md` §3.2; core §4.3.

**Lineage Policy.** Declares revocation cascade behaviour: `lax` (derivatives are sovereign; parent revocation does not cascade) or `strict` (derivatives inherit revocation). PII data MUST use `strict`; downgrading to `lax` with PII yields `protocol:lineage:lineage_policy_inconsistent` (105). See `xift-1.0-spec-extension-governance.md` §3.8.

**Lineage Tag.** Metadata in the `provenance` extension tracking derivation: `parent_ids`, `derivation_type`, `derivation_agent_did`, `derivation_timestamp`, `stratum_in`, `stratum_out`, `derivation_method_hash`. Preserved for audit after lifecycle operations but does not enforce revocation cascade under the lax rule. See `xift-1.0-spec-extension-provenance.md` §2–§3.

**Derivation Type.** Six values classifying what operation produced a derivative: `redaction`, `transformation`, `distillation`, `augmentation`, `synthesis`, `extraction`. See `xift-1.0-spec-extension-provenance.md` §3.1.

**Anonymization Evidence.** Sub-object in the `provenance` extension, REQUIRED when transitioning `pii_classification` from `personal-identifiable`/`pseudonymized` to `anonymized`. Contains `method`, `method_parameters`, `evaluator_did`, OPTIONAL `evaluation_timestamp`, and Ed25519 `evaluation_signature` over the JCS-canonical attestation form. The signature provides non-repudiable attestation against the evaluator's DID; a bare hash would be insufficient. See `xift-1.0-spec-extension-provenance.md` §3.2; core §9.4.

**Egress Validation (Egress DLP).** Normative requirement (core §8.4) where the sender MUST validate the recipient's authorisation, classification bounds, extension support and consent before emitting an envelope. Failure returns `protocol:egress:egress_validation_failed` (105). One of the pillars of the XIFT protocol. See `xift-1.0-spec-core.md` §8.4; `xift-1.0-spec-channels-general.md` §1.5.

**Auxiliary LLM.** A language model invoked exclusively to arbitrate ambiguities in the policy layer (errors in the 5xxx range) when deterministic rules (Cedar/Zen) produce inconclusive results. Distinct from the agent's primary LLM. Usage is host-defined and OPTIONAL.

**Cedar.** AWS-developed policy language and engine for authorization. Used by the host's policy layer for binary authorization decisions. In Memgator, integrated via AGT Agent OS. In XIFT, consumed via policy dispatch. See `xift-reference-implementation-architecture.md` §2.

**Zen (Zen Engine).** GoRules' embedded decision engine. Handles business-logic scoring (JDM tables). Distinct from Cedar, which handles authorization. See `xift-reference-implementation-architecture.md` §2.

**JDM — Just-in-time Decision Model.** GoRules' rule format used by Zen Engine. Authoring is tenant-editable.

**HPKE — Hybrid Public Key Encryption.** RFC 9180. The end-to-end encryption scheme used by the `encryption` extension to protect payload confidentiality. XIFT v1.0 uses X25519-SHA256-AES256GCM as the default cipher suite. Mandatory when `classification ≥ sensitive`. See `xift-1.0-spec-extension-encryption.md` §1, §3.

**Step-up Authentication.** Re-authentication with higher assurance (e.g. hardware token, MFA) triggered when an agent requests access to knowledge with `classification = restricted`. Signalled via `policy:consent:additional_assurance_required` (207, warning). See `xift-1.0-spec-channels-general.md` §2.4; core §8.6.

**Consent VC.** Verifiable Credential signed by the data subject (or their delegate) authorising a specific exchange. Bound to `data_subject_did`, purpose, scope and validity period. Referenced by `consent_vc_ref` and `consent_vc_hash` in the `governance` extension. See `xift-1.0-spec-extension-governance.md` §3.6.

**Policy Tags.** Free-form array of strings in the `governance` extension consumed by the receiver's policy engine. Emerging conventions: `no-share-outside-trust`, `audit-required`, `redact-on-promotion`, `model-training-prohibited`. Maximum `policy_tags_count_max` per envelope (default 16, core §10). See `xift-1.0-spec-extension-governance.md` §3.9.

**Redaction Hash.** SHA-256 over the canonical redaction-policy document applied to the artifact. Binds the artifact to the redaction state at issue time. See `xift-1.0-spec-core.md` §9.

**ML-DSA-65.** NIST-standardised post-quantum signature algorithm. Tracked in core §15.1; NOT part of XIFT v1.0. Relevance deferred to a future release.

---

## 3. Mesh, Discovery & Channels

### 3.1 Channels

**Channel.** One of seven wire-flow protocols in XIFT. Each is specified in its own `xift-1.0-spec-channel-N.md` document.

**Channel 1 — Discovery & Handshake.** Publication, retrieval, and versioning of capability advertisements; mutual identity handshake producing a session token. See `xift-1.0-spec-channel-1.md`.

**Channel 2 — Envelope Handoff.** Direct delivery of a signed KnowledgeObject (inline or via content-ref dial-back). The most-used channel. See `xift-1.0-spec-channel-2.md`.

**Channel 3 — Status Verification (BSL Pull).** Synchronous revocation check: a receiver pulls a BSL to verify that an envelope's grant has not been revoked. Fail-closed. See `xift-1.0-spec-channel-3.md`.

**Channel 4 — Change Notification (Revocation Push).** Asynchronous push of state changes (revocations, capability changes, Custodian state transitions) via Server-Sent Events. Complements Channel 3. See `xift-1.0-spec-channel-4.md`.

**Channel 5 — Semantic Discovery Request/Response (SDR).** Embedding-based semantic search for agents or artifacts matching a query. Returns ranked candidates with composite scores. See `xift-1.0-spec-channel-5.md`.

**Channel 6 — Semantic Interest & Experience Announce (SIEA).** Persistent subscriptions (interests) and announcements (new knowledge available). Custodian matches and routes notifications. See `xift-1.0-spec-channel-6.md`.

**Channel 7 — Sequential Conversation Session (SCS).** Multi-turn, bidirectional sessions between agents for collaborative refinement. Supports smart clustering, k-rounds, consensus voting, and session journals. See `xift-1.0-spec-channel-7.md`.

### 3.2 Extensions

**Extension.** An opt-in metadata block added to the KnowledgeObject envelope. XIFT v1.0 defines six, each in its own `xift-1.0-spec-extension-{name}.md` document.

**Extension: `governance`.** Consent, classification, PII classification, purpose of use, lineage policy, policy tags, agent role. Core extension (MUST recognise). See `xift-1.0-spec-extension-governance.md`.

**Extension: `provenance`.** Derivation lineage, 6 derivation types, anonymization evidence. Core extension. See `xift-1.0-spec-extension-provenance.md`.

**Extension: `encryption`.** End-to-end encryption via HPKE (RFC 9180). Mandatory when `classification ≥ sensitive`. Core extension. See `xift-1.0-spec-extension-encryption.md`.

**Extension: `revocation`.** Active revocation binding via W3C BSL. Two-layer revocation (TTL + BSL), fail-closed, herd privacy. Core extension. Requires `governance`. See `xift-1.0-spec-extension-revocation.md`.

**Extension: `quality`.** Metrics, confidence, and profile for a knowledge artifact. Silently ignorable by non-supporting receivers (no `protocol:extension:unknown_extension`). See `xift-1.0-spec-extension-quality.md`.

**Extension: `ontology`.** Governed vocabulary exchange: a hash-pinned vocabulary **descriptor** (the sender's own vocabulary) plus reciprocal **alignment cells** negotiated on Channel 7 (SCS). The vocabulary-alignment substrate of the semantic channels (5/6/7); silently ignorable; metadata-only (never interprets the payload). See `xift-1.0-spec-extension-ontology.md`.

**OntologyDescriptor.** The `ontology` extension block (Mechanism B): a dereferenceable JSON-LD 1.1 `@context` pinned by a `sha256:` hash, with an OPTIONAL reduced SKOS projection (a partial taxonomy, never the full graph) and OPTIONAL SHACL shapes. Describes only the sender's own vocabulary.

**Alignment cell.** A flat, SSSOM-inspired correspondence (`subject_id`, `predicate_id` ∈ SKOS mapping relations, `object_id`, `alignment_score` ∈ [0,1], `score_function`, `method`, `calibrated`). Produced only by the Channel-7 SCS loop and carried in the signed synopsis; advisory by default. See `xift-1.0-spec-extension-ontology.md` §3.2.

### 3.3 Discovery Concepts

**Capability Advertisement.** A signed document declaring an agent's XIFT participation: endpoints, supported extensions, encryption schemes, DID methods, channel capabilities, governance constraints, resource costs, VCV. Published on Channel 1. See `xift-1.0-spec-channel-1.md` §3, §4.

**VCV — Versioned Capability Vector.** Structured object within the capability advertisement that includes the agent's competence embedding, a Bloom filter, and a spec embedding. Enables pre-filtering before expensive HNSW search. See `xift-1.0-spec-channel-1.md` §4.3.

**Bloom Filter (in VCV).** Probabilistic data structure in the VCV that allows sub-millisecond pre-filtering of discrete capability tags (e.g. `tool:sql`, `domain:fintech`) before vector-based semantic search. See `xift-1.0-spec-channel-1.md` §4.3 and `xift-reference-implementation-architecture.md` §7.4.

**HNSW — Hierarchical Navigable Small World.** Approximate nearest-neighbour index algorithm recommended for the Custodian's Capability Index. Provides sub-linear semantic retrieval in meshes with many agents. See `xift-reference-implementation-architecture.md` §7.1.

**Composite Score.** Four-dimensional match score used in SDR (Channel 5) and SIEA (Channel 6): semantic alignment, policy compatibility, resource fit, and spec similarity. Computed by the Zen Engine via a JDM table. See `xift-1.0-spec-channel-5.md` §7.

**XiftSemanticQuery.** The request message on Channel 5 SDR: carries query text, query embedding, Bloom filter, governance constraints, cost budget, and a signed challenge. See `xift-1.0-spec-channel-5.md` §3.

**XiftSemanticResponse.** The response message on Channel 5 SDR: carries ranked match candidates with composite score breakdowns, per-candidate DIDs, and optional `scs_endpoint` for follow-on sessions. See `xift-1.0-spec-channel-5.md`.

**Subscription (SIEA).** A persistent declaration of interest by a subscriber on Channel 6. Carries interest text, interest embedding, governance constraints, and a delivery endpoint. TTL-bounded (max 30 days). See `xift-1.0-spec-channel-6.md` §3.

**Announcement (SIEA).** A declaration by an announcer that a knowledge artifact is available. Carries an abstract (PII-free), an abstract embedding, governance metadata, and a handoff endpoint. TTL-bounded (max 24 hours). See `xift-1.0-spec-channel-6.md` §4.

**Match Notification.** A notification pushed by the Custodian (or peer) to a subscriber when a subscription's constraints match an announcement. Carries composite score and breakdown. See `xift-1.0-spec-channel-6.md` §5.

### 3.4 Trust Custodian

**Trust Custodian.** Optional agent role in XIFT offering up to three services: **Capability Index** (HNSW-backed queryable index of signed capability documents), **BSL Aggregation** (LRU cache + scheduled polling of issuer BSL URLs), and **Identity Cache** (handshake attestation cache). Activation is mesh-size-driven (see **Custodian State Machine**). Cannot forge artifacts (all artifacts are signed by their issuers). See `xift-custodian-1.0.md`.

**Custodian State Machine.** ⚠️ **Spec conflict**: the core spec (`xift-1.0-spec-core.md` §10) defines thresholds at `mesh_custodian_activation_threshold = 25` and `mesh_custodian_deactivation_threshold = 15`; the custodian spec (`xift-custodian-1.0.md` §2) and channels-general (`xift-1.0-spec-channels-general.md` §7.3) use thresholds of 50 and 40 respectively. Per the document hierarchy, the core spec is authoritative; the custodian and channels-general specs require update. Additionally, the custodian spec defines four states (`dormant`, `awakening`, `active`, `decommissioning`) while the state vocabulary (`xift-state-vocabulary.md` §1) defines three states (`Dormant`, `Warmable`, `Active`) with the core-spec-aligned thresholds. This conflict should be resolved in a future revision. Using the state vocabulary and core spec values: **Dormant** (≤ 15 agents; no services), **Warmable** (16–24; pre-warming indices, not serving queries), **Active** (≥ 25; serving all declared services). Hard P2P limit at 50 agents (above which Custodian-mediated topology becomes MANDATORY for SIEA). See `xift-state-vocabulary.md` §1; `xift-custodian-1.0.md` §2.

**Delegation Contract.** Signed, time-bounded agreement by which an agent delegates specific services (status list hosting, directory, relay, cache) to a Trust Custodian. The Custodian cannot exceed the scope of the contract. See `xift-custodian-1.0.md`.

**Multi-Custodian Topology.** To prevent relay centralisation, the three Custodian services (Capability Index, BSL Aggregation, Identity Cache) MAY be hosted by different agents. See `xift-1.0-spec-channels-general.md` §7.4; `xift-custodian-1.0.md` §5.

**Fanout Control.** The Custodian enforces `siea_global_fanout_per_announcement_max`, limiting how many subscribers receive notifications for any single announcement on Channel 6. Over-cap notifications are deprioritised, not queued. See `xift-1.0-spec-channels-general.md` §7.5.

**WebSocket Escalation.** OPTIONAL transport upgrade for Channel 4: when a publisher serves more than 300 concurrent SSE subscribers, it MAY offer WebSocket (`wss://`) as an alternative notification transport. Declared via `channel_4_transport: ["sse", "ws"]` in the capability advertisement. SSE remains the default and MUST always be available. Uses sub-protocol `xift-notify-v1`, the same JSON event schema as SSE, and WebSocket Ping/Pong for liveness. See `xift-1.0-spec-channels-general.md` §1.3.1.

**Subscriber Capacity Governance.** Mechanism by which a Custodian declares and enforces its maximum concurrent subscriber count on Channel 4. The Custodian advertises `channel_4_subscriber_capacity` in its capability document; at capacity it rejects new connections with HTTP 503 + `protocol:channel4:notification_connection_refused` (108), emits `protocol:channel4:subscriber_capacity_nearing` (108, warning) at 80%, and optionally evicts the lowest-trust-score subscriber (sending `stream_terminated` with reason `protocol:channel4:notification_stream_terminated`, 106) to make room for higher-trust-score agents. Overflow subscribers fall back to Channel 3 polling. See `xift-1.0-spec-channels-general.md` §7.6.

### 3.5 Channel 7 — SCS Concepts

**Smart Clustering.** OPTIONAL structured refinement pattern in SCS sessions. When enabled, the session follows k-rounds of draft/critique/revision cycles before consensus. See `xift-1.0-spec-channel-7.md` §6.

**K-Rounds.** The refinement rounds in a smart-clustering SCS session: each round includes `draft`, `critique`, and `revision` messages. Capped by `scs_max_rounds_per_session` (default 10). See `xift-1.0-spec-channel-7.md` §6.

**Consensus Voting.** Vote mechanism in SCS sessions. Votes carry `value` (`approve`, `reject`, `abstain`), an optional `weight` (default 1.0), and a `reason`. Consensus is reached when the weighted-approve ratio meets `consensus_threshold`. See `xift-1.0-spec-channel-7.md` §7.

**Session Journal.** Ordered log of all messages with their signatures maintained during a SCS session. Consumed by the host at session close for consolidation into memory. Format is implementation-defined. See `xift-1.0-spec-channel-7.md` §8.

**Synopsis.** End-of-session consolidated summary produced by the initiator of a SCS session. Emitted as a `message_type = synopsis` message. This is an XIFT-defined message type, distinct from the implementation-defined journal. See `xift-1.0-spec-channel-7.md` §5.

### 3.6 Transport Concepts

**Session Token.** Opaque token produced by `HandshakeMethod` after a mutual identity handshake. Encodes both DIDs, an expiration, and a freshness guarantee. Maximum lifetime `identity_handshake_cache_ttl_seconds` (default 900 s). See `xift-1.0-spec-channels-general.md` §2.3.

**Signature Challenge.** One-off signed nonce authenticating a single request, included in the `Authorization` header as `Signature <base64url(sig)>`. Used for requests without a prior session. See `xift-1.0-spec-channels-general.md` §1.4.

**Inline Mode.** Payload delivery mode where the payload is base64-encoded inside the envelope's `payload_inline` field, ≤ `payload_inline_size_max` (default 64 KB). See `xift-1.0-spec-channel-2.md` §1.

**Reference Mode.** Payload delivery mode where the payload resides at a `content_ref` URI and is fetched via the dial-back flow or storage-mediated handoff. See `xift-1.0-spec-channel-2.md` §1, §4.

**Dial-Back.** Channel 2 flow where the receiver fetches payload from the sender's `content_ref` URL after verifying a signed challenge. The challenge includes a nonce (≥ 128 bits), the recipient's DID, the artifact ID, and a timestamp within 60 seconds. URL TTL ≤ 5 minutes. See `xift-1.0-spec-channel-2.md` §4.

**Back-Pressure Signal.** A signal emitted by any layer or sink when its bounded queue is at capacity. Surfaces as HTTP 429, `protocol:rate:rate_limit_exceeded` (103, with severity reflecting whether the request was rejected or flagged), or the `AuditSinkBackPressureSignalled` event (the explicit event raised once the audit sink saturates and the channel must reject inbound work). See `xift-1.0-spec-channels-general.md` §1.6; core §11.

**Keepalive.** SSE comment frame asserting connection liveness on Channel 4. Publisher SHOULD emit within 25 seconds of silence; subscriber considers the stream dead after 90 seconds without any emission. See `xift-1.0-spec-channel-4.md` §9; `xift-state-vocabulary.md` §11.

**Replay Buffer.** Publisher-side memory of recent SSE events for reconnection when a subscriber reconnects with `Last-Event-ID`. Default buffer duration: `notification_replay_buffer_seconds` (300 s). See `xift-1.0-spec-channel-4.md` §7.

### 3.7 Observability

**Audit Stream.** The no-loss observability channel that records every authorisation, lifecycle, and trust decision. Carried by the `AuditSink` host trait. Distinct from telemetry. See `xift-reference-implementation-architecture.md` §6.4.

**Telemetry Stream.** The sampleable, OTel-shaped observability channel. Carried by the `TelemetrySink` host trait. Distinct from audit. Hot-path spans sampled at 1% baseline; 100% on errors. See `xift-reference-implementation-architecture.md` §6.3.

**OpenTelemetry / OTel.** Standard observability framework. XIFT's telemetry stream is OpenTelemetry-shaped.

### 3.8 Interoperability

**A2A — Agent2Agent Protocol.** Linux Foundation protocol for horizontal agent-to-agent task negotiation. XIFT is orthogonal to A2A and does not subsume it. The A2A Adapter translates between XIFT envelopes and A2A `DataPart` payloads while preserving XIFT signatures. See `xift-interop-1.0.md` §3, §5.

**MCP — Model Context Protocol.** Anthropic protocol for vertical agent-to-tool interaction. XIFT is orthogonal to MCP. The MCP Adapter publishes MCP tool capabilities through XIFT's discovery mechanism. See `xift-interop-1.0.md` §4, §6.

**A2A Adapter.** Translation layer between XIFT envelopes and A2A messages. Wraps a `KnowledgeObject` as an A2A `DataPart` with XIFT metadata in extension fields, preserving the envelope's canonical signature end-to-end. See `xift-interop-1.0.md` §5.

**MCP Adapter.** Translation layer that publishes MCP tool capabilities through XIFT's discovery mechanism (Channel 1 VCV) and wraps MCP tool outputs as governed `KnowledgeObject` envelopes. See `xift-interop-1.0.md` §6.

### 3.9 Billing (Reserved — Phase 3)

**Payment Required (`policy:financial:payment_required`).** Reserved policy condition for billing-enabled envelopes. The provider sends a payment offer (in the error `context`) before delivery. Part of the `policy:financial:*` namespace. Not implemented in XIFT v1.0. See `xift-1.0-spec-channels-general.md` §11 and `xift-non-goals.md` §9.

**Settlement Confirmation.** An enhancement to the Channel 2 receipt (§7) that includes `payment_proof_ref`, `settled_amount`, `settled_currency`, and `settlement_timestamp`. The signed receipt becomes a settlement confirmation anchored as a VC for audit. Reserved for a future release. See `xift-1.0-spec-channel-2.md` §7.

---

## 4. Memgator-Specific Terms

Terms below are specific to the Memgator host implementation and
are NOT part of the XIFT protocol.

**ACL — Anticorruption Layer.** **(Memgator)** A translation layer between Memgator's domain types and an external vendor SDK. Lives in `infrastructure/`. Required for every vendor dependency. See `20260516-anticorruption-layers-required.md`.

**Agent Mesh.** **(Memgator)** AGT subsystem providing zero-trust agent identity (DIDs, signing, Trust Score). In the XIFT context, Agent Mesh is one possible implementation of the `IdentityProvider`, `TrustScoreProvider`, `DIDResolver` and `HandshakeMethod` host traits.

**Agent OS.** **(Memgator)** AGT subsystem providing the security plane (Cedar policy engine, PII redaction, prompt-injection detection).

**Agent SRE.** **(Memgator)** AGT subsystem providing operational reliability (circuit breakers, supervision, observability pipeline).

**AGT — Agent Governance Toolkit.** **(Memgator)** Microsoft's open-source toolkit for AI agent governance. Memgator integrates AGT as an embedded library (not a sidecar). Composed of Agent OS, Agent Mesh, and Agent SRE. XIFT does not depend on AGT; it is the host's choice.

**Backlog (HITL Backlog).** **(Memgator)** Queue of decisions routed to human reviewers (e.g. low-confidence promotions, low Trust Score writes). API in `memgator-core`; review UI in `memgator-premium`.

**Connascence.** **(Memgator)** Page-Jones's taxonomy of coupling. See `references/responsibility-driven-design.md`.

**Consolidation.** **(Memgator)** Lifecycle operation that fuses near-duplicate episodic records and groups thematically related ones. See `references/domain.md`.

**Decay (Intelligent Decay).** **(Memgator)** Lifecycle operation that applies the U(M) formula and routes records below threshold ε to active forgetting.

**Distillation.** **(Memgator)** Lifecycle operation that uses schema-first LLM extraction to produce candidates for promotion from one stratum to a higher one.

**Evaluator (Promotion Evaluator).** **(Memgator)** Hot-path component in Quantum A. Decides the destiny of an authorized, scored record (store / promote / purge / quarantine / escalate).

**HITL — Human-In-The-Loop.** **(Memgator)** Workflow involving human review for cases that automation cannot or should not decide.

**Hot-Path.** **(Memgator)** The synchronous Interceptor → Evaluator pipeline that runs on every memory read/write. Constrained by a strict latency budget. See `20260516-hot-path-latency-budget.md`.

**Identity Layer (Memory Identity Layer).** **(Memgator)** Hot-path component in Quantum A that resolves DIDs and Trust Scores. Outside the hot-path latency budget; has its own sub-budget.

**Interceptor (Memory Interceptor).** **(Memgator)** Hot-path component in Quantum A. Synchronous middleware that captures every memory operation and orchestrates Cedar, Zen, identity, and telemetry.

**Quantum (Architectural Quantum).** **(Memgator)** Independently deployable unit with high cohesion and its own static coupling boundary. Memgator has two: A (hot-path) and B (supervisor). See `20260516-architectural-quanta.md`.

**Quarantine.** **(Memgator)** Decision category. Record is accepted but isolated, not visible to reads until reviewed.

**Saliency.** **(Memgator)** Importance score assigned to a memory at creation. Component S_i of the U(M) formula.

**Supervisor (Consolidation Supervisor).** **(Memgator)** Quantum B's owner. Orchestrates the Consolidator, Distiller, Decay Monitor, and Conflict Adjudicator workers.

**U(M) — Utility Formula.** **(Memgator)** `U(M_i) = α · R_i + β · S_i + γ · V_i`. Determines whether a record survives intelligent decay.

---

## Change Log

> **Change history:** consolidated in [`spec/CHANGELOG.md`](./CHANGELOG.md) (newest first).

