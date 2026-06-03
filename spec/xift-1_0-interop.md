---
title: XIFT 1.0 — Interoperability Profile
status: draft (v1.1 — core companion)
date: 2026-05-21
visibility: public
authors:
  - Memgator architecture working group
related:
  - xift-1.0-spec-core.md (core spec)
  - xift-1.0-spec-channels-general.md (cross-channel conventions)
  - xift-custodian-1.0.md (Trust Custodian)
---

# XIFT 1.0 — Interoperability Profile

## 0. Document Status

This document is the **Interoperability Profile** for XIFT v1.0. It
specifies how XIFT coexists with A2A (Agent2Agent Protocol, Linux
Foundation) and MCP (Model Context Protocol, Anthropic) as
complementary standards, not as protocols XIFT replaces or
subsumes.

The Interop Profile sits at the XIFT v1.0 core because the
adapter contracts are constrained by the core envelope and identity
model. The semantic capabilities that connect XIFT discovery with
MCP tool catalogues require VCV (`xift-1.0-spec-channel-1.md`
§4.3), so §3.2 onward depends on the channel specifications.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Positioning Statement

### 1.1 Three Protocols, Three Concerns

XIFT, A2A, and MCP solve different problems in the inter-agent
ecosystem. They are complementary, not competitive.

| Protocol | Layer                              | Primary Concern                                                |
|----------|------------------------------------|----------------------------------------------------------------|
| MCP      | Vertical: agent ↔ tool             | How an agent discovers and invokes tools/resources.            |
| A2A      | Horizontal: agent ↔ agent (task)   | How agents negotiate tasks and exchange results.               |
| **XIFT** | Horizontal: agent ↔ agent (knowledge) | How agents exchange governed knowledge artifacts with consent. |

The relationship is best described as **wrapping with governance**:
XIFT does not replace what MCP or A2A do; it adds governance,
classification, consent, and lineage to information that flows
through them, when the use case calls for it.

### 1.2 What This Profile Provides

This document specifies:

- How XIFT and A2A coexist in flows that combine task negotiation
  with governed knowledge exchange (§3).
- How XIFT and MCP coexist in flows where tool outputs become
  knowledge artifacts subject to consent and classification (§4).
- The **A2A Adapter** translating between XIFT envelopes and A2A
  `DataPart` payloads (§5).
- The **MCP Adapter** for publishing MCP tool capabilities through
  XIFT's discovery mechanism (§6).
- How an agent simultaneously implements all three protocols
  without conflict (§7).

### 1.3 What This Profile Does NOT Do

- Does NOT redefine A2A or MCP. References to those protocols are
  to their authoritative specifications.
- Does NOT mandate that XIFT agents implement A2A or MCP. Adapters
  are OPTIONAL; agents may speak only XIFT.
- Does NOT extend A2A or MCP. XIFT consumes their public surfaces
  as published; it does not propose extensions to either.
- Does NOT establish a transport contract between the three
  protocols. Each runs on its own endpoints; the adapters operate
  at the application layer.

---

## 2. Design Principles for Interop

### 2.1 Principle: XIFT Wraps, Does Not Subsume

When XIFT and A2A or MCP coexist, XIFT operates **above** them in
the governance sense: it carries metadata about the artifacts that
travel through A2A or MCP, but does not interfere with their wire
formats. An A2A `Task` remains an A2A `Task`. An MCP `Resource`
remains an MCP `Resource`. XIFT adds context, not replacement.

### 2.2 Principle: Identity is Common Substrate

The three protocols converge on DIDs as identity. An agent's DID is
the same across XIFT, A2A and MCP. This means:

- Trust scores assigned via the identity provider apply uniformly.
- A capability advertisement (`xift-1.0-spec-channel-1.md` §4) can
  reference MCP endpoints and A2A endpoints alongside XIFT
  endpoints.
- Authentication established for one protocol can inform
  authentication for the others, subject to receiver policy.

### 2.3 Principle: Adapters Preserve Signatures

When an XIFT envelope crosses an adapter to ride inside an A2A
message or an MCP resource, the XIFT envelope's canonical signature
(JCS + Ed25519) remains intact and verifiable end-to-end. The
adapter is a transformation envelope, not a re-signing layer.

### 2.4 Principle: Governance Travels with Artifacts

If a knowledge artifact moves through A2A's task-result mechanism, its
XIFT governance metadata (classification, consent, lineage) travels
with it. An A2A receiver that does not understand XIFT may ignore
the metadata, but a receiver that does understand XIFT MUST honor
it. The adapter ensures both behaviors are supported.

Reference adapters for external sensitivity-labelling systems
(Microsoft Purview, Google Sensitive Data Protection, AWS Macie)
populate **both** representations of governance §3.3/§3.10: the
mapped ordinal `classification` (authoritative for policy) and the
verbatim `native_labels` record (for round-trip fidelity). Because a
label record carries a stable opaque `id` (Purview label GUID, Google
`infoType.name`) and its `tenant_ref` (Purview `SiteId`, GCP project),
the adapter can reconstruct the source label on export even when the
display `name` is unavailable cross-tenant. The adapter owns the
consistency rule: the mapped `classification` MUST be at least as
restrictive as the level the native scheme implies.

### 2.5 Principle: No Forced Adapter Adoption

XIFT agents that only need pair-wise governed knowledge exchange do
not need to implement either adapter. The adapters exist for
agents that participate in heterogeneous ecosystems where some
peers speak A2A or MCP natively.

---

## 3. XIFT × A2A Coexistence

### 3.1 The Coexistence Pattern

A2A handles task negotiation: an agent submits a task, another agent
processes it, returns artifacts. XIFT handles governed knowledge
exchange: agents discover relevant experiences, share them under
consent, and refine them collaboratively.

In a typical multi-agent workflow these two activities are
interleaved:

1. Agent A initiates a task via A2A.
2. Agent B (the worker) needs prior experiences to inform its work.
3. Agent B uses XIFT's SDR (Channel 5) to discover candidates.
4. Agent B retrieves selected experiences via XIFT's Handoff
   (Channel 2).
5. Agent B optionally refines with the experience owner via XIFT's
   SCS (Channel 7).
6. Agent B returns the task result to Agent A via A2A.
7. The result, if it constitutes a new knowledge artifact, is wrapped
   in an XIFT envelope (potentially using the A2A Adapter, §5) and
   stored or announced.

### 3.2 Joint Discovery: A2A Agent Cards Reference XIFT Endpoints

A2A agents publish their identity and capabilities via
`/.well-known/agent-card.json`. An XIFT-capable agent MAY include
its XIFT endpoint URLs in its A2A Agent Card so that other A2A
agents can discover XIFT participation:

```json
{
  "name": "Strategy Analyst",
  "description": "...",
  "url": "https://api.example.com/a2a/v1",
  "version": "1.0.0",
  "capabilities": { "...A2A capabilities..." },
  "skills": [ "...A2A skills..." ],
  "extensions": {
    "xift": {
      "version": "1.0",
      "endpoints": {
        "discovery": "https://api.example.com/xift/v1/discovery",
        "handoff": "https://api.example.com/xift/v1/envelopes",
        "sdr": "https://api.example.com/xift/v1/sdr",
        "siea": "https://api.example.com/xift/v1/siea",
        "scs": "https://api.example.com/xift/v1/scs"
      },
      "supported_extensions": [
        "governance", "provenance", "encryption", "revocation", "quality"
      ]
    }
  }
}
```

This is **non-normative** from A2A's perspective (A2A allows
arbitrary keys in `extensions`) and **informational** from XIFT's
perspective (XIFT's authoritative capability document is published
separately per `xift-1.0-spec-channel-1.md` §4.1).

The XIFT capability document remains the source of truth for XIFT
participation; the A2A Agent Card extension is a discoverability
hint for the A2A-first ecosystem.

### 3.3 Cross-Protocol Flow: Task With Governed Knowledge Retrieval

Reference flow combining A2A task lifecycle with XIFT knowledge
exchange:

```
Agent A                    Agent B                XIFT Network
   |                          |                        |
   |---A2A task/submit------->|                        |
   |   (task_id, params)      |                        |
   |                          |                        |
   |                          |---XIFT SDR query------>|
   |                          |   (relevant exp?)       |
   |                          |<--matches (Custodian)---|
   |                          |                        |
   |                          |---XIFT Handoff fetch-->|
   |                          |<--KnowledgeObject------|
   |                          |                        |
   |                          | (process task using    |
   |                          |  retrieved knowledge)  |
   |                          |                        |
   |<--A2A task/result--------|                        |
   |   (artifact)             |                        |
```

In this flow:

- A2A controls the **task contract** (what to do, when it's done).
- XIFT controls the **knowledge governance** (what experiences inform
  the work, under what consent).
- The two protocols never share wire bytes; they cooperate at the
  agent's internal logic.

### 3.4 Cross-Protocol Flow: SIEA-Triggered Task Initiation

A2A workflows can also be triggered by XIFT events:

```
Agent A                  Custodian             Agent B (A2A worker)
   |                         |                          |
   |--XIFT SIEA subscribe--->|                          |
   |   (interest: fraud)     |                          |
   |                         |<--XIFT announce----------|
   |                         |   (new fraud pattern)    |
   |                         |---match notification---->|
   |<--match notification----|                          |
   |                                                    |
   |---A2A task/submit--------------------------------->|
   |   (analyze pattern X)                              |
   |<--A2A task/result----------------------------------|
   |   (analysis result wrapped in XIFT envelope        |
   |    via A2A Adapter §5)                             |
```

This pattern is useful when a long-running A2A worker reacts to
ambient knowledge events surfaced by XIFT subscriptions.

### 3.5 What XIFT Does NOT Do in A2A Coexistence

- XIFT MUST NOT modify A2A's `Message` or `Task` envelope structure.
  All XIFT-specific data crosses the boundary through the A2A
  Adapter (§5), riding inside `DataPart`, never as new top-level
  fields.
- XIFT MUST NOT require A2A peers to implement XIFT. An A2A worker
  that does not speak XIFT receives ordinary A2A messages.
- XIFT MUST NOT impose its governance on A2A messages that are not
  carrying XIFT-wrapped content. An A2A `Task` with ordinary
  `TextPart` is outside XIFT's scope.

---

## 4. XIFT × MCP Coexistence

### 4.1 The Coexistence Pattern

MCP handles vertical tool access: an agent connects to tools (file
systems, databases, APIs) via MCP servers. XIFT handles horizontal
knowledge exchange: agents share experiences with each other.

The two coexist most naturally when **tool outputs become knowledge
artifacts**:

1. Agent A invokes a tool via MCP (e.g., a database query).
2. The tool returns a result.
3. Agent A wraps the result in an XIFT envelope with appropriate
   classification, consent, and lineage (the tool invocation
   becomes `provenance.derivation_type: extraction`).
4. Agent A may announce the artifact via SIEA, or hold it for
   internal use.

The MCP tool itself does not need to know about XIFT. The agent is
the integration point.

### 4.2 Publishing MCP Capabilities via XIFT VCV

The most strategically important interop pattern: **an XIFT-capable
agent publishes its MCP tool inventory through its XIFT capability
document**, so that other agents can discover what tools and
resources each peer has access to.

This is achieved through the VCV (`xift-1.0-spec-channel-1.md`
§4.3) in three layers:

#### 4.2.1 Bloom Filter for Discrete Capability Tags

The `bloom_filter` field of the VCV is the primary discovery
mechanism for MCP tools. An agent populates the bloom filter with
tags identifying its MCP capabilities:

| Tag pattern             | Example tags                                                |
|-------------------------|-------------------------------------------------------------|
| `tool:<name>`           | `tool:sql`, `tool:filesystem`, `tool:web-fetch`             |
| `mcp:<server-name>`     | `mcp:github`, `mcp:slack`, `mcp:google-drive`               |
| `resource:<type>`       | `resource:repository`, `resource:database`, `resource:gdoc` |
| `domain:<vertical>`     | `domain:legal`, `domain:medical`, `domain:financial`        |
| `mcp-prompt:<name>`     | `mcp-prompt:summarize`, `mcp-prompt:extract`                |

The bloom filter enables sub-millisecond pre-filtering: a querier
looking for "agents with SQL access" can eliminate non-matches
before any vector computation. This is the **fast path** for
capability discovery.

#### 4.2.2 Dense Embedding for Functional Discovery

The `embedding` field of the VCV encodes the **semantic meaning** of
the agent's combined competencies — knowledge (what it knows) and
tools (what it can do). This is generated by encoding a natural-
language description of the agent's profile, which SHOULD include
references to its MCP capabilities:

```
"This agent is a financial analyst with read access to PostgreSQL
databases of customer transactions, write access to a knowledge
graph in Neo4j, and the ability to invoke fraud-detection ML
models via the company's MLOps platform. It specializes in
small-business onboarding."
```

The embedding of this description allows SDR queries like "agents
who can detect anomalies in transaction data" to find this agent
even if the querier does not know the precise tool names.

The fast bloom-filter path and the slow embedding path complement
each other: discrete-tag queries hit the bloom filter, fuzzy
semantic queries hit the embedding, and most real-world queries
benefit from both.

#### 4.2.3 Optional `mcp_servers` Field for Detail

When detailed MCP capability inspection is needed beyond
bloom-filter membership, an agent MAY include an optional
`mcp_servers` array in its capability document:

```json
{
  "did": "did:web:org.example.com:agent:analyst",
  "capability_vector": {
    "embedding": "<base64-bytes>",
    "bloom_filter": "<base64-bytes>",
    "...": "..."
  },
  "mcp_servers": [
    {
      "name": "postgres-customers",
      "version": "1.2.0",
      "transport": "stdio",
      "access_mode": "read",
      "tags": ["tool:sql", "domain:financial"]
    },
    {
      "name": "neo4j-knowledge-graph",
      "version": "0.9.1",
      "transport": "http",
      "access_mode": "read-write",
      "tags": ["tool:graph-db", "domain:financial"]
    }
  ],
  "...": "..."
}
```

`mcp_servers` is OPTIONAL. The bloom filter and embedding are
sufficient for routing decisions; `mcp_servers` provides additional
context when an agent wants to inspect another's specific tooling
before initiating a task.

### 4.3 MCP Tool Outputs as XIFT Knowledge Artifacts

When an MCP tool produces output that becomes a knowledge artifact,
the agent wraps it in an XIFT envelope:

- `agent_did` = the agent invoking the tool.
- `memory_scope` = `episodic` for raw tool outputs, `semantic` for
  derived knowledge.
- `provenance.derivation_type` = `extraction` (per
  `xift-1.0-spec-extension-provenance.md` §3.1).
- `provenance.parent_ids` = empty (tool output is not derived from
  another XIFT artifact, although there is upstream lineage outside
  XIFT's purview).
- `provenance.derivation_method_hash` = optional hash of the
  MCP tool invocation (server name, version, parameters).
- `provenance.tool_invocation` (XIFT-Interop OPTIONAL field) =
  structured reference to the MCP invocation:

```json
{
  "provenance": {
    "derivation_type": "extraction",
    "parent_ids": [],
    "stratum_in": null,
    "stratum_out": "episodic",
    "derivation_agent_did": "did:web:org.example.com:agent:analyst",
    "derivation_timestamp": "2026-05-21T10:00:00Z",
    "tool_invocation": {
      "mcp_server": "postgres-customers",
      "tool_name": "query",
      "parameters_hash": "sha256:abc...",
      "invocation_timestamp": "2026-05-21T09:59:55Z"
    }
  }
}
```

The `tool_invocation` sub-object is non-normative for XIFT core
(receivers that don't recognize it MUST ignore it) but conventional
within the Interop Profile.

### 4.4 What XIFT Does NOT Do in MCP Coexistence

- XIFT MUST NOT proxy MCP traffic. An agent's MCP connections
  remain agent-to-MCP-server, not routed through XIFT.
- XIFT MUST NOT impose governance on MCP tool invocations directly.
  The governance applies to the *artifacts* produced from those
  invocations once they enter XIFT's envelope.
- XIFT MUST NOT require MCP servers to be XIFT-aware. The agent
  invoking the MCP server is the integration point.

---

## 5. The A2A Adapter

### 5.1 Purpose

The A2A Adapter is a documented transformation between an XIFT
KnowledgeObject envelope (predecessor name: `MemoryObject`) and an
A2A `Message`/`DataPart` payload. It enables XIFT-wrapped artifacts
to travel through A2A flows without either side losing fidelity.

### 5.2 Outbound: XIFT → A2A

When an XIFT-capable agent sends a knowledge artifact to an A2A peer
as part of a task result:

1. The agent constructs the XIFT envelope normally (core §3.1).
2. The envelope is canonicalized (JCS) and signed (Ed25519).
3. The signed envelope is base64-encoded and placed inside an A2A
   `DataPart`:

```json
{
  "kind": "message",
  "role": "agent",
  "messageId": "msg-01HXX...",
  "taskId": "task-01HYY...",
  "parts": [
    {
      "kind": "data",
      "data": {
        "mimeType": "application/xift-envelope+json",
        "encoding": "base64",
        "content": "<base64-encoded JCS-canonical XIFT envelope>"
      }
    }
  ],
  "metadata": {
    "xift_envelope_id": "01HXX5VQ7K9M3J8N2P4R6T8WAY",
    "xift_protocol_version": "1.0",
    "xift_extensions": ["governance", "provenance"]
  }
}
```

The `metadata` block exposes selected XIFT fields at the A2A level
so that A2A receivers can route or filter without parsing the
embedded envelope. The original signed envelope is the authoritative
source.

### 5.3 Inbound: A2A → XIFT

When an XIFT-capable agent receives an A2A message containing a
`DataPart` with `mimeType: application/xift-envelope+json`:

1. The agent extracts the base64-encoded content.
2. The agent decodes and parses as JSON.
3. The agent verifies the canonical signature (Ed25519 over JCS).
4. If the signature is valid, the agent processes the envelope as
   if it had arrived via XIFT's Handoff channel.
5. If the signature is invalid, the agent rejects the artifact and
   MAY respond via A2A with an error message.

### 5.4 A2A Receivers Without XIFT Support

An A2A peer that does not implement the Adapter receives the
`DataPart` as opaque base64 data. It may:

- Pass the data through (e.g., to a downstream tool).
- Ignore the data and rely on the A2A `metadata` hints for routing.
- Reject the message if its policy requires understanding all
  content (this is the A2A peer's decision, not XIFT's).

XIFT senders MUST NOT assume an A2A peer will process the embedded
envelope. The Adapter is **transport encapsulation**, not a
guarantee of receiver compliance.

### 5.5 Signature Preservation

The XIFT envelope's `canonical_signature` MUST remain unchanged by
the Adapter. Specifically:

- The adapter MUST NOT re-canonicalize the envelope.
- The adapter MUST NOT modify any envelope field, including
  whitespace.
- The base64 encoding is byte-faithful to the canonical JCS form.
- A receiver decoding the envelope on the other side MUST be able
  to verify the signature without knowing the envelope passed
  through A2A.

This preserves end-to-end cryptographic integrity even when
intermediate A2A hops are untrusted.

### 5.6 Limitations of the A2A Adapter

- XIFT extensions like `revocation` (BSL polling) still require
  XIFT-native channels. The Adapter carries the envelope; it does
  not carry the surrounding XIFT infrastructure.
- An A2A `Message` may be larger than `policy_block_size_max`
  (core §10) when carrying a full XIFT envelope. Implementations
  SHOULD use `content_ref` for large payloads, with the A2A
  message carrying only envelope metadata and the reference.
- The Adapter does NOT provide A2A-level encryption beyond what
  A2A's TLS provides. XIFT's `encryption` extension still produces
  HPKE-encrypted payloads inside the envelope; this remains intact
  through the Adapter.

---

## 6. The MCP Adapter

### 6.1 Purpose

The MCP Adapter is a documented pattern by which an XIFT-capable
agent surfaces its MCP capabilities through XIFT's discovery
mechanism, and reciprocally consumes MCP capability advertisements
from peers that publish them via XIFT VCV.

Unlike the A2A Adapter, the MCP Adapter is **not a wire-format
transformation**. MCP traffic does not pass through XIFT. The
Adapter is a **capability-publishing convention** plus a **tool
invocation provenance convention**.

### 6.2 Tool Capability Publishing

Per §4.2, the agent populates its XIFT capability document with:

- Bloom filter tags for each MCP tool/resource/server.
- Dense embedding encoding a natural-language description of
  combined knowledge and tool capabilities.
- Optional `mcp_servers` array with structured tool inventory.

This publication enables semantic discovery (SDR) to surface agents
based on their tool capabilities, not just on the knowledge they hold
in memory.

### 6.3 Tool Invocation as Provenance

When the agent's actions are driven by an MCP tool invocation, the
resulting knowledge artifact carries `provenance.tool_invocation` per
§4.3. This creates auditable lineage: "this knowledge artifact was
generated by querying tool X with parameters Y at time T".

### 6.4 Discovery-to-Tool Flow

A common pattern enabled by the MCP Adapter:

```
Querier Agent                  Custodian                   Provider Agent
   |                              |                            |
   |--SDR query: "SQL on----------|                            |
   |   customer data"             |                            |
   |                              |                            |
   |                              | bloom filter: tool:sql     |
   |                              | + domain:financial         |
   |                              | + embedding match           |
   |                              |                            |
   |<-Provider Agent matches------|                            |
   |   (capability: tool:sql)     |                            |
   |                              |                            |
   |---A2A task: "query           |                            |
   |   customer X transactions"------------------------------->|
   |                              |                            |
   |                              |              (MCP call to  |
   |                              |               postgres-    |
   |                              |               customers)   |
   |                              |                            |
   |<--A2A task result (wrapped in XIFT envelope via §5)-------|
   |   (provenance.tool_invocation: postgres-customers)        |
```

Three protocols, three layers of work, no protocol bleed.

### 6.5 MCP Resource Subscriptions and XIFT

MCP supports resource subscriptions (notification when a resource
changes). When a subscribed resource changes and the change is
semantically meaningful, the agent MAY publish an XIFT SIEA
announcement to surface the change to interested peers:

1. MCP resource update notification arrives.
2. Agent's logic decides whether to publish.
3. If yes, the agent constructs an XIFT envelope with
   `derivation_type: extraction` describing the change.
4. The agent announces via SIEA.
5. Subscribers receive matches via their delivery endpoints.

This pattern enables ambient awareness across an agent mesh based
on changes to underlying tool data, mediated by XIFT's governance.

### 6.6 What the MCP Adapter Does NOT Do

- Does NOT proxy MCP protocol traffic.
- Does NOT impose XIFT signatures on MCP messages.
- Does NOT require the MCP server to know about XIFT.
- Does NOT require the agent to expose its MCP credentials to
  other agents via XIFT.

---

## 7. Triple-Protocol Agent

### 7.1 Coexistence Architecture

An agent that implements all three protocols runs three independent
listener stacks:

```
                +---------------------------+
                |       Agent Logic         |
                |   (LLM, memory, etc.)     |
                +---+-----------+-----------+
                    |           |           |
        +-----------+--+   +----+----+   +--+-----------+
        | XIFT Listener|   | A2A Lstn|   | MCP Clients  |
        | (xift-server)|   | (a2a-svr)|   | (mcp-clients)|
        +--------------+   +---------+   +--------------+
              |                 |               |
        XIFT endpoints     A2A endpoints   MCP servers
```

The three stacks share:

- The agent's DID and signing keys.
- The agent's policy engine (Cedar/Zen in reference
  implementation).
- The agent's memory backend (Memgator in reference
  implementation).

They do NOT share:

- Wire formats. Each protocol speaks its own.
- Endpoint configuration. Each has its own URL paths and ports.
- Capability documents. XIFT's authoritative capability document
  may reference A2A and MCP endpoints, but each protocol publishes
  its own discovery surface.

### 7.2 Routing Decisions Inside the Agent

The agent's internal logic decides which protocol to use for each
interaction:

| Goal                                                | Protocol                              |
|-----------------------------------------------------|---------------------------------------|
| Discover what experiences other agents have         | XIFT SDR (Channel 5)                  |
| Subscribe to relevant new experiences as they emerge| XIFT SIEA (Channel 6)                 |
| Retrieve a specific knowledge artifact              | XIFT Handoff (Channel 2)              |
| Refine a knowledge artifact in multi-turn conversation | XIFT SCS (Channel 7)              |
| Delegate a unit of work to another agent            | A2A task                              |
| Receive structured task results                     | A2A task/result (optionally Adapter)  |
| Invoke a tool                                       | MCP                                   |
| Subscribe to changes in a tool's resources          | MCP resource subscription             |

This is a routing table inside the agent's logic, not a protocol
specification. Implementations are free to choose differently as
their workflows dictate.

### 7.3 Capability Cross-Publishing

A triple-protocol agent publishes its capabilities through three
discovery surfaces:

- **XIFT capability document** (authoritative for XIFT
  participation). Includes references to A2A and MCP endpoints if
  exposed.
- **A2A Agent Card** at `/.well-known/agent-card.json`. Includes
  an `extensions.xift` block per §3.2 referencing XIFT endpoints.
- **MCP server manifest** (per MCP server hosted by the agent).
  This is purely MCP-internal; the XIFT capability document's
  bloom filter surfaces these MCP capabilities for XIFT-mediated
  discovery.

The three surfaces SHOULD be consistent. Inconsistency is not a
protocol error but a deployment concern: an agent advertising
`tool:sql` via XIFT bloom filter but not exposing a corresponding
MCP server is a configuration bug.

---

## 8. Anti-Patterns and Boundaries

### 8.1 Anti-Pattern: Adapter as Replacement

**Wrong:** Treating the A2A Adapter as a "way to do XIFT over A2A
without implementing XIFT".

**Why wrong:** The Adapter is encapsulation, not substitution.
Sending an XIFT envelope through an A2A message does not give the
sender access to XIFT's discovery, revocation, or SCS mechanisms.
Those require XIFT-native channels.

**Right:** Use the Adapter only when an XIFT artifact needs to
travel through an A2A flow for task-coordination reasons.

### 8.2 Anti-Pattern: Tool Output Without Provenance

**Wrong:** Wrapping an MCP tool output in an XIFT envelope without
populating `provenance.tool_invocation` or equivalent lineage.

**Why wrong:** Defeats the audit purpose. A receiver cannot
distinguish an artifact derived from a trusted tool from one
fabricated by the agent.

**Right:** Always include lineage when wrapping tool outputs, even
if it's just an opaque `derivation_method_hash`.

### 8.3 Anti-Pattern: MCP Credentials in XIFT Capability

**Wrong:** Exposing MCP server credentials (API keys, tokens) in
the `mcp_servers` field of the XIFT capability document.

**Why wrong:** XIFT capability documents are signed but generally
visible to many peers and Custodians. Embedding credentials creates
secret-leakage risk.

**Right:** The `mcp_servers` field describes what the agent has
access to, not how. Authentication remains private to the agent.

### 8.4 Anti-Pattern: A2A as XIFT Transport

**Wrong:** Routing all XIFT traffic through A2A messages "for
unified transport".

**Why wrong:** Loses XIFT's specialized capabilities (SDR
discovery, SIEA subscriptions, BSL revocation, smart clustering)
which have no A2A equivalent. Introduces overhead and indirection.

**Right:** Use each protocol where it fits. The Adapter is for
specific cross-protocol moments, not for general transport.

### 8.5 Anti-Pattern: Different DIDs Across Protocols

**Wrong:** Using `did:agent-a2a` for A2A, `did:agent-mcp` for MCP,
and `did:agent-xift` for XIFT — same agent, three identities.

**Why wrong:** Breaks identity-substrate principle (§2.2). Trust
scores diverge, audit trails fragment, attackers can play one
protocol's identity off against another.

**Right:** One DID per agent, used uniformly across all three
protocols.

---

## 9. Conformance for Interop

The Interop Profile is **OPTIONAL**: an XIFT implementation that
does not interact with A2A or MCP peers is conformant without
implementing any of this. For implementations that DO claim Interop
conformance, the following tests apply:

| Suite  | Name                                          | Description                                         |
|--------|-----------------------------------------------|-----------------------------------------------------|
| IOP.01 | A2A Adapter round-trip                        | XIFT envelope wrapped in A2A DataPart, decoded, signature verifies. |
| IOP.02 | A2A Adapter signature preservation            | A2A intermediate cannot tamper without detection.   |
| IOP.03 | A2A Agent Card xift extension parsing         | XIFT-aware peer discovers XIFT endpoints via A2A card. |
| IOP.04 | MCP capability publication via bloom filter   | Querier can discover MCP-tool-capable agents via SDR. |
| IOP.05 | MCP tool invocation provenance                | Artifact carries valid `tool_invocation` block.     |
| IOP.06 | MCP resource subscription → SIEA              | Resource change triggers SIEA announcement.         |
| IOP.07 | Triple-protocol identity consistency          | Same DID resolves consistently across XIFT, A2A, MCP. |
| IOP.08 | Adapter does NOT subsume                      | XIFT-only operations (SDR, BSL) still require XIFT channels. |

---

## 10. Open Questions

1. **A2A extension governance.** The A2A community is formalizing
   an extensions registry (a2a-protocol.org `/topics/extensions/`).
   Should XIFT register an official A2A extension identifier (e.g.,
   `xift-1.0`) for the Agent Card extension block in §3.2?

2. **MCP capability standardization.** The bloom filter tag patterns
   in §4.2.1 are conventional. Should XIFT publish a recommended
   (non-normative) tag taxonomy for MCP capabilities?

3. **Tool invocation provenance richness.** The current
   `tool_invocation` block is minimal. Should it carry more (e.g.,
   parameter schema hash, output schema, retry count)?

4. **Cross-protocol revocation.** When an XIFT envelope is revoked
   via BSL, but a copy of it traveled through A2A to a non-XIFT
   peer, that copy is unrevocable in practice. Should the Adapter
   document a best-practice for marking A2A-encapsulated XIFT
   envelopes with a hint to re-check XIFT BSL?

5. **MCP authorization composition.** MCP has its own authorization
   model (per server). When an XIFT-governed knowledge artifact is
   used to inform an MCP tool invocation, do the two authorization
   regimes compose, and if so, how? Likely receiver-policy concern,
   not protocol.

6. **PAX integration.** PAX (the 5-field minimalist handoff
   format) could be a third adapter target. Deferred to a future
   release.

---

## Appendix A — Comparison: When to Use Which Protocol

| Use Case                                                | Protocol(s)               |
|---------------------------------------------------------|---------------------------|
| Discover what tools an agent has                        | XIFT VCV bloom filter (MCP-aware) |
| Discover what experiences an agent has                  | XIFT SDR                  |
| Invoke a tool on a peer agent                           | A2A task (peer invokes its own MCP server) |
| Invoke a tool directly                                  | MCP                       |
| Subscribe to "new fraud patterns" across mesh           | XIFT SIEA                 |
| Subscribe to "this database table changes"              | MCP resource subscription |
| Send a knowledge artifact to one peer with consent      | XIFT Handoff              |
| Send a task result to a peer                            | A2A task/result           |
| Send a task result that IS a governed knowledge artifact| A2A task/result + Adapter |
| Refine an artifact over multi-turn dialog               | XIFT SCS                  |
| Have a conversation about a task                        | A2A multi-turn task       |
| Revoke a previously shared artifact                     | XIFT BSL (no A2A/MCP eq.) |

---

## Appendix B — Reference Implementation Notes

The Memgator reference implementation includes:

- An `a2a-adapter` module providing the §5 wire transformation.
- An `mcp-adapter` module providing the §4.2 capability publication
  helpers and the §4.3 provenance annotation helpers.
- An MCP server inventory poller that auto-populates the XIFT
  capability document's bloom filter and `mcp_servers` array based
  on configured MCP servers.
- An A2A Agent Card publisher that includes the §3.2 xift
  extension block.

These are implementation conveniences. Other XIFT implementations
may approach interop differently.

---

## Appendix C — Glossary (Interop-Specific)

| Term                  | Meaning                                                          |
|-----------------------|------------------------------------------------------------------|
| Knowledge             | The substance XIFT exchanges: facts, patterns, rules, summaries, observations and inferences produced by an agent and consumable by another. |
| Knowledge artifact    | A concrete unit of knowledge wrapped in a `KnowledgeObject` envelope for exchange. |
| KnowledgeObject       | The canonical envelope of XIFT v1.0. (Predecessor name: `MemoryObject`.) |
| Memory (repository)   | An agent's internal repository where knowledge is stored, organized, and decayed. Distinct from the protocol. |
| Memory stratum        | A subdivision of an agent's memory repository following CoALA: working, episodic, semantic, procedural. Declared by the envelope's `memory_scope` field. |
| Experience            | One kind of knowledge — knowledge acquired during the operation of the agent's Working Self. Typically lands in episodic or working strata. |
| Working Self          | The operational self of an agent executing tasks. The source of experiences. |
| Adapter               | Documented transformation/convention, not a protocol layer.      |
| A2A Adapter           | XIFT envelope ↔ A2A DataPart transformation per §5.              |
| MCP Adapter           | Capability-publishing and provenance-annotation convention per §6. |
| Triple-protocol agent | An agent implementing XIFT, A2A, and MCP simultaneously (§7).    |
| Wraps, not subsumes   | XIFT adds governance; does not replace adjacent protocols (§2.1). |
| Capability cross-publishing | An agent's capabilities visible through three discovery surfaces (§7.3). |

---

## Appendix D — Change Log

> **Change history:** consolidated in [`spec/CHANGELOG.md`](./CHANGELOG.md) (newest first).

