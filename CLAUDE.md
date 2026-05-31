<!-- Public repo. Contributor-facing. Keep under ~180 lines. -->
# XIFT — Protocol Specifications & Reference Implementation (public)

XIFT is a peer-to-peer protocol for the governed exchange of **knowledge**
between AI agents, part of the open-source Memgator project. This repository
holds the normative specifications, the interoperability contracts
(OpenAPI/AsyncAPI/JSON Schema), and the Rust reference implementation.

Planning, ADRs, research, and steering documents live in the **private**
sibling repo `xift-internal`. See "Two-repo layout" below.

## Two-repo layout

- `xift` (this repo, public): specs, contracts, `rust/` reference impl, examples, tests.
- `xift-internal` (private sibling): ADRs, research, steering docs, `.kiro/` tasks.

When both are needed in one session, launch from one and attach the other:
`CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 claude --add-dir ../xift-internal`.

**Public/private boundary (strict).** Never copy ADR rationale, research prose,
or internal design notes into public files. Public specs may reference an ADR
**by ID only** (e.g. "per ADR-XIFT-ERROR-MODEL-001"), never its content. Do not
commit anything that reveals private deliberation to this repo.

## Knowledge paradigm (vocabulary is load-bearing)

- XIFT exchanges **knowledge** (facts, patterns, rules, summaries, observations,
  inferences). **Memory** is the host's internal repository. **Experience** is
  knowledge acquired during the Working Self's operation.
- The canonical envelope is `KnowledgeObject` (predecessor: `MemoryObject` — the
  first mention in any document must include this predecessor note).
- **Wire field names are frozen** for protocol stability: `memory_scope`,
  `payload_inline`, `payload_hash`, `content_ref`, `content_type`, `envelope_id`.
- CoALA stratum names are preserved verbatim: `working`, `episodic`, `semantic`,
  `procedural`. GDPR vocabulary is preserved verbatim.

## Protocol structure

- **7 channels**: 1 Discovery & Handshake, 2 Envelope Handoff, 3 Status
  Verification / BSL Pull, 4 Change Notification / SSE Push, 5 Semantic Discovery
  Request (SDR), 6 Semantic Interest & Experience Announce (SIEA), 7 Conversational
  Session Synthesis (CSS).
- **5 extensions**: `governance`, `provenance`, `encryption`, `revocation` (core,
  MUST recognise), `quality` (silently ignorable).
- **10 host traits**: `IdentityProvider`, `TrustScoreProvider`, `DIDResolver`,
  `HandshakeMethod`, `KeyProvider`, `AuditSink`, `TelemetrySink`, `Supervisor`,
  `Clock`, `Configuration`.

## Error model (current; see .claude/rules/error-model.md for the full rule)

The numeric `code` is a small immutable per-layer routing set; the
`layer:domain:sub_category` `category` string is the source of domain truth.
No numeric `financial` layer — billing is `policy:financial:*`. Error objects are
flat and signed in full (Ed25519 over JCS / RFC 8785). Authoritative category
registry: `xift-error-taxonomy.md` (see the registry-location decision in
xift-internal if it has not yet been resolved).

## Key numerical defaults (core §10)

Mesh activation 25 agents / deactivation 15 / P2P hard limit 50. Rate limit
60 envelopes/min/DID, burst 10. BSL min length 131072 bits, max staleness 300 s.
Handshake p99 target 200 ms, hard cap 500 ms. Trust score [0, 1000], baseline 500,
Custodian 700. Payload inline max 64 KB. Full catalogue:
`xift-budgets-and-thresholds.md` (xift-internal).

## Document hierarchy (when answering or editing)

1. **Normative specs** are authoritative: core, channels-general, channel-1..7,
   extension docs, custodian, interop.
2. **Steering docs** (in xift-internal) are the translation layer for EARS.
3. **Reference implementation** (`rust/`) is informative; other hosts may differ.
4. **Glossary** defines Memgator- and XIFT-specific terms.

If a steering doc and a spec disagree, **the spec wins**; flag the steering doc
for update (in xift-internal), do not silently diverge.

## Conventions

- **Language**: specs, ADRs, code comments, and commit messages in American
  English. Chat with the maintainer is in classical Spanish (no voseo, no
  regionalisms) — but generated documents stay in English.
- **Surgical edits**: when modifying an existing doc, change only what must
  change; preserve surrounding structure and headings.
- **Change history (per-directory `CHANGELOG.md`)**: content documents do
  **not** carry an inline change-log body. Each content directory keeps one
  newest-first `CHANGELOG.md` (`spec/`, `rust/`, `contracts/`); record the
  change there and bump the doc's frontmatter `status: draft (vX.Y)`. Where a
  retired inline "Appendix — Change Log" heading remains, it is a pointer to the
  directory `CHANGELOG.md`. Git is the authoritative history. (The private
  `xift-internal` repo mirrors this for `steering/`, `proposals/`, `policies/`,
  `docs/`; its `adr/` and `research/` are exempt.)
- **Frontmatter**: new specs/docs follow the existing pattern (title, status,
  date, visibility, authors, related).
- **Diagrams**: Mermaid fenced blocks inside the Markdown.
- **Worker vs runtime agents**: distinguish development tools (Claude Code,
  Kiro, OpenClaw, Perplexity) from XIFT protocol participants and Memgator
  runtime components. A decision for one group rarely applies to the other.
- **Don't invent**: if an architectural decision is not documented, say so and
  offer alternatives rather than fabricating. Propose an ADR (in xift-internal)
  before writing code that encodes a new decision.

## Rust reference implementation

- Workspace crates: `xift-core`, `xift-client`, `xift-server`, `xift-custodian`.
- Build: `cargo build`. Test: `cargo test`. Lint: `cargo clippy -- -D warnings`.
  Format: `cargo fmt`. Run all before proposing a commit.
- The reference impl follows the specs in `spec/`; when impl and spec disagree,
  the spec wins and the impl is the bug.

@README.md
