---
title: XIFT 1.0 — Extension `ontology`
status: draft (v1.0)
date: 2026-05-31
visibility: public
authors:
  - Memgator architecture working group
related:
  - xift-1.0-spec-core.md (core spec; §3.2 extensions, §3.3.3 hash-pin form)
  - xift-1.0-spec-channels-general.md (cross-channel conventions)
  - xift-1.0-spec-extension-quality.md (silently-ignorable contract; confidence shape)
  - xift-1.0-spec-extension-provenance.md (alignment lineage)
  - xift-1.0-spec-extension-encryption.md
  - xift-1.0-spec-channel-1.md (capability advertisement)
  - xift-1.0-spec-channel-5.md (Semantic Discovery)
  - xift-1.0-spec-channel-6.md (SIEA)
  - xift-1.0-spec-channel-7.md (Synchronous Conversational Synthesis)
  - xift-error-taxonomy.md (category registry — `*:ontology:*`)
  - ADR-XIFT-ONTOLOGY-001
---

# XIFT 1.0 — Extension: `ontology`

This document specifies the `ontology` envelope extension. Common
envelope conventions (canonical form, mandatory blocks, signature
mechanics, identity layer, error model) are specified in
`xift-1.0-spec-core.md`. The decision of record is
**ADR-XIFT-ONTOLOGY-001**.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are per
RFC 2119 and RFC 8174.

---

## 1. Purpose and Scope

XIFT exchanges **knowledge** as payloads that are opaque to the
protocol (core §2). Two agents from different hosts routinely describe
the same domain with divergent vocabularies; a `KnowledgeObject`
(predecessor: `MemoryObject`) can pass every wire and policy check and
still be *misinterpreted* at the payload layer because the receiver's
concepts do not line up with the sender's. The `ontology` extension
closes this gap: it lets agents **declare, negotiate, and reconcile the
vocabularies they use** while preserving payload opacity.

`ontology` is the **vocabulary-alignment substrate of the semantic
channels** (5 SDR, 6 SIEA, 7 SCS). It is realised through three
mechanisms with three distinct homes:

- **Mechanism A — Capability negotiation.** Channel-1 advertises which
  ontology formats and alignment methods an agent supports (§3.4); a
  lightweight per-exchange flag on Channels 5/6/7 signals willingness to
  coordinate.
- **Mechanism B — Static descriptor.** The `ontology` extension block
  carries a hash-pinned vocabulary **descriptor** describing **only the
  sender's own vocabulary** (§2, §3.1).
- **Mechanism C — Reciprocal alignment loop.** Channel 7 (SCS) negotiates
  bilateral **alignment cells** (§3.2) and consolidates them in the
  signed `synopsis` (§3.5).

The causal arrow runs **5/6 → 7**: Channels 5 and 6 attach the sender's
one-sided descriptor so their matching is vocabulary-aware from first
contact; the reciprocal cells are produced *afterward* on Channel 7,
between two peers that discovery/announcement has already paired (§10).

The extension carries **metadata about vocabulary** and **alignment
declarations** only. It never requires XIFT to interpret the knowledge
payload itself (§11).

`ontology` is NOT one of the four mandatory-recognition **core
extensions** (`governance`, `provenance`, `encryption`, `revocation`).
It is the **sixth declared extension** and is **silently ignorable**: a
receiver that does not declare it MUST NOT reject an envelope that
carries it, and MUST NOT emit `protocol:extension:unknown_extension`
(105). It is the same soft-acceptance contract as `quality` (§4).

> **Encryption scope.** Per `xift-1.0-spec-extension-encryption.md` §1,
> when `governance.classification` is `sensitive` or higher the
> `ontology` block is within the encryption scope (carried inside the
> ciphertext), identical to `quality`. A receiver that does not decrypt
> therefore cannot read it — consistent with the silently-ignorable
> model.

---

## 2. Block Structure

The `ontology` extension block (Mechanism B) carries the sender's
vocabulary **descriptor**. It does NOT carry alignment cells; those are
produced by the SCS loop (§3.2, §3.5).

```json
{
  "ontology": {
    "context_iri": "https://vocab.example.com/agent/v3/context.jsonld",
    "context_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    "format": "json-ld",
    "skos_projection": {
      "concepts": [
        { "id": "ex:FraudSignal", "pref_label": "fraud signal",
          "broader": ["ex:RiskSignal"] }
      ]
    },
    "shacl_shapes": null
  }
}
```

---

## 3. Fields

### 3.1 Descriptor Fields (Mechanism B)

| Field             | Type    | Required | Description                                                                                                                            |
|-------------------|---------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| `context_iri`     | IRI     | yes      | Dereferenceable JSON-LD 1.1 `@context` for the sender's vocabulary.                                                                     |
| `context_hash`    | string  | yes      | `sha256:<64hex>` hash-pin of the `@context` body, in the **prefixed lowercase-hex** form of core §3.3.3. Provides semantic stability.   |
| `format`          | enum    | yes      | Serialization of the declared vocabulary. Closed set: `json-ld`, `skos`, `shacl`. MUST be one the emitter also advertised (§3.4).       |
| `skos_projection` | object  | no       | OPTIONAL **reduced** SKOS view — a *partial* taxonomy, never the full graph (§3.1.1). Bounded by `ontology_projection_max_concepts`.    |
| `shacl_shapes`    | object  | no       | OPTIONAL SHACL shapes constraining the vocabulary. MAY be `null`.                                                                       |

The descriptor describes **only the sender's own vocabulary**.

#### 3.1.1 Reduced SKOS Projection

The `skos_projection`, when present, is a **partial** view, favoured for
two reasons: **privacy** (it does not leak the full taxonomy) and
**alignment quality** (a compact, scoped projection is a measurably
better input to the model tier than a raw ontology dump — ADR-XIFT-
ONTOLOGY-001 §2.2). The full source graph MUST NOT be recoverable from
the projection. It is bounded by `ontology_projection_max_concepts`
(§6); when carried inside an SCS message it is additionally bounded by
`scs_max_message_size_kb`.

### 3.2 Alignment Cell (Mechanism C)

An alignment cell is a single, flat, SSSOM-inspired correspondence
record, **produced only by the SCS reciprocal loop** (§3.5) — never at
discovery/announce time.

| Field                   | Type   | Required | Meaning                                                                            |
|-------------------------|--------|----------|------------------------------------------------------------------------------------|
| `subject_id`            | IRI    | yes      | Concept in the asserting agent's vocabulary.                                       |
| `predicate_id`          | enum   | yes      | SKOS mapping relation (closed set, §3.2.1).                                        |
| `object_id`             | IRI    | yes      | Corresponding concept in the counterparty's vocabulary.                           |
| `alignment_score`       | number | yes      | Calibrated belief in the correspondence, ∈ [0, 1] (§3.3).                          |
| `score_function`        | enum   | yes      | The eligible scoring function that produced `alignment_score` (§3.3.1).           |
| `method`                | enum   | yes      | Tier that derived the cell: `lexical`, `embedding`, `llm-assisted`, `manual`.     |
| `calibrated`            | bool   | yes      | Whether `alignment_score` is calibrated (reuses the `quality.confidence` shape).  |
| `mapping_justification` | string | no       | Why the mapping holds (transparency; provenance of the match).                    |

#### 3.2.1 `predicate_id` — SKOS Mapping Relations

`predicate_id` is drawn from the closed SKOS mapping vocabulary:
`skos:exactMatch`, `skos:closeMatch`, `skos:broadMatch`,
`skos:narrowMatch`, `skos:relatedMatch`. These cover equivalence (≡)
and broader/narrower subsumption (⊑ / ⊒) without EDOAL's expressive
complexity. A correspondence the deterministic tier cannot resolve with
confidence is delegated to the model tier (§8), never forced.

### 3.3 `alignment_score` Semantics

- `alignment_score` ∈ [0, 1] is a **subjective, calibrated belief**
  about correspondence — never ground truth (§11).
- It is **advisory by default**: a low or borderline value surfaces as a
  **warning** (`model:ontology:alignment_score_low`, 303 — §7), not a
  rejection, mirroring the `quality` soft-acceptance model.
- A **hard reject** occurs ONLY when a deployment configures
  `ontology_alignment_min_score` (§6, default disabled): a required cell
  below the threshold then yields an `error`-severity model-layer
  condition.
- Its confidence descriptor **reuses the `quality.confidence` shape**
  (`method`, `calibrated`) rather than inventing a parallel structure.

The canonical *governance* consumer of the score is **memory-promotion
gating** (§10.3): a receiver uses `alignment_score` to decide whether
knowledge received under a mapped vocabulary may be promoted into
long-term memory (CoALA `semantic` / `procedural` strata) or held
provisionally. The score gates *promotion*; it never adjudicates factual
truth (§11).

#### 3.3.1 `score_function` — Eligible Scoring Functions

`alignment_score` is produced by an explicitly declared **eligible
scoring function**, selected by the host per deployment or per exchange,
rather than a single fixed formula. `score_function` is a closed
enumeration:

| Value              | Tier          | Derivation                                                              |
|--------------------|---------------|-------------------------------------------------------------------------|
| `lexical_jaccard`  | deterministic | Lexical overlap of `pref_label`/synonyms (Jaccard).                     |
| `embedding_cosine` | deterministic | Cosine similarity over per-concept embeddings.                          |
| `hybrid_weighted`  | deterministic | Host-weighted blend of `lexical_jaccard` and `embedding_cosine`.        |
| `llm_calibrated`   | model         | Selective-oracle model-tier judgement on borderline cells (§8); calibrated. |

A conformant emitter MUST set `score_function` on every cell, and the
value MUST be consistent with `method` (a `model`-tier `score_function`
implies `method = llm-assisted`). The set is closed; an additional
function is admitted only via the review trigger in ADR-XIFT-ONTOLOGY-001
§8.

### 3.4 Capability Advertisement Fields (Mechanism A)

A peer advertises ontology support in its Channel-1 extended capability
advertisement (`xift-1.0-spec-channel-1.md` §4):

| Field                        | Type             | Description                                                                             |
|------------------------------|------------------|-----------------------------------------------------------------------------------------|
| `supported_ontology_formats` | array of enum    | Subset of `json-ld`, `skos`, `shacl`. Empty/absent → the agent advertises no support.   |
| `alignment_methods`          | array of enum    | Subset of `lexical+embedding`, `llm-assisted`, `hybrid`.                                |
| `vocabulary_iris`            | array of IRI     | OPTIONAL known vocabulary/profile IRIs the agent already uses.                          |

Absence of these fields means the agent advertises no ontology support;
peers fall back to raw-embedding matching.

### 3.5 SCS Message Types (Mechanism C)

The reciprocal alignment loop lives **exclusively** in Channel 7 (SCS).
It adds three `message_type` values and **reuses existing SCS machinery
unchanged** — k-rounds, the session journal, and the signed `synopsis`
(consensus, voting weights and round limits exactly as in
ADR-XIFT-SCS-CONSENSUS-WEIGHTS-002; this extension adds no consensus
semantics):

| `message_type`        | Role                                                                                  |
|-----------------------|---------------------------------------------------------------------------------------|
| `ontology_probe`      | A participant requests alignment for a set of concepts (carries a scoped projection). |
| `ontology_assertion`  | A participant asserts candidate alignment cells (§3.2) for the probed concepts.       |
| `ontology_ack`        | A participant accepts/rejects asserted cells; consolidated cells land in the synopsis.|

The signed `synopsis` carries the **consolidated alignment cells** for
the session. The model tier is **never consensus-bearing** (§8).

---

## 4. Receiver Behaviour

A receiver MUST declare `ontology` in its `supported_extensions`
(`xift-1.0-spec-channel-1.md` §3, §4) to **parse** the extension block.
If not declared:

- The receiver MUST NOT reject the envelope solely because it contains
  `ontology`. This extension is always **silently ignorable** — it does
  not produce `protocol:extension:unknown_extension` (105).
- The receiver MAY treat the envelope as if the extension were absent.

If declared:

- A party that dereferences a declared `context_iri` MUST verify the
  fetched body against the `context_hash` pin **before use**; a mismatch
  is `protocol:ontology:context_hash_mismatch` (102, §7).
- An SCS participant MUST recognise `ontology_probe`,
  `ontology_assertion`, and `ontology_ack`, and MUST treat a low
  `alignment_score` as a **warning** unless `ontology_alignment_min_score`
  is configured.

**Per-channel sender inclusion** of the descriptor (Mechanism B):

| Channel | Inclusion | Effect of absence                                                                              |
|---------|-----------|------------------------------------------------------------------------------------------------|
| 5 — SDR | Optional  | Alignment is resolved downstream by SCS dialogue; no penalty.                                  |
| 6 — SIEA| **SHOULD**| Matched on raw embeddings and given a **degraded composite score** (`siea_unaligned_match_penalty`, channel-6), never a rejection. |
| 7 — SCS | Per-session opt-in | The loop is not run.                                                                  |

---

## 5. Egress DLP and Encryption Scope

Per core §8.4 (Egress Validation):

- The descriptor is subject to egress DLP: a sender MUST NOT publish a
  `skos_projection` from which the full taxonomy is recoverable (§3.1.1),
  and MUST NOT exceed `ontology_projection_max_concepts`.
- When `governance.classification` is `sensitive` or higher, the
  `ontology` block MUST be carried **inside the ciphertext** (encryption
  scope), identical to `quality`.
- A `context_iri` that points at an internal-only resource SHOULD NOT be
  emitted on a cross-organization exchange; use a dereferenceable public
  IRI with a stable hash-pin.

---

## 6. Extension Parameters

| Parameter                          | Default | Layer     | Purpose                                                                                       |
|------------------------------------|---------|-----------|-----------------------------------------------------------------------------------------------|
| `ontology_alignment_min_score`     | `null`  | Policy    | Hard-reject floor for a required cell's `alignment_score`. `null` = disabled (advisory only). Per-deployment default with an optional per-session override (cf. SCS `voting_policy`). |
| `ontology_projection_max_concepts` | 256     | Discovery | Maximum concepts in a `skos_projection`.                                                       |
| `ontology_match_budget_ms`         | 50      | Policy    | Soft latency ceiling for the **deterministic** alignment tier on the synchronous path (Channel 5). The model tier never runs on the hot path (§8).            |
| `ontology_cell_max_age_seconds`    | 86400   | Policy    | A consumer (Channel 5/6) MUST treat a cached alignment cell older than this as stale. Independent of — and in addition to — invalidation on `context_hash` change or a counterparty capability-version bump. |

The Channel-6 budget `siea_unaligned_match_penalty` (default 0.5) is
defined in `xift-1.0-spec-channel-6.md`. The core parameters of
`xift-1.0-spec-core.md` §10 apply.

---

## 7. Error Codes

Per ADR-XIFT-ERROR-MODEL-001, `ontology` introduces **no new numeric
codes**; it adds only `category` strings over existing per-layer codes.
It is the **first concrete consumer of the `model` layer (300–399)**.

| Code | Category                                  | Layer    | Severity | Trigger                                                                               |
|------|-------------------------------------------|----------|----------|---------------------------------------------------------------------------------------|
| 102  | `protocol:ontology:context_hash_mismatch` | protocol | error    | Fetched `@context` body does not match the declared `context_hash` pin (integrity).   |
| 302  | `model:ontology:unmapped_concept`         | model    | error    | A required concept has no acceptable correspondence in the counterparty's vocabulary. |
| 301  | `model:ontology:context_unresolvable`     | model    | error    | The auxiliary model cannot resolve the asserted correspondence (ambiguous context).   |
| 303  | `model:ontology:alignment_score_low`      | model    | warning  | A cell's `alignment_score` is below confidence (advisory default).                    |

The hash-pin failure routes on **`102`** (`invalid_argument`) for
registry consistency — every hash-mismatch in XIFT routes there. The
full rows (retryability, emitter, observer, remedy) are in
`xift-error-taxonomy.md` §10quater. A receiver that gates on
`alignment_score` with `ontology_alignment_min_score` configured raises
a `302`/`301` `error`-severity condition; otherwise a low score is the
`303` warning.

---

## 8. Frugal Tiering (Selective Oracle)

Alignment computation is **tiered** to keep cost bounded:

1. **Deterministic tier (always first):** lexical matching and embedding
   similarity over the declared vocabularies (`lexical_jaccard`,
   `embedding_cosine`, `hybrid_weighted` — §3.3.1). Resolves the bulk of
   cells and is the only tier that runs within `ontology_match_budget_ms`
   on the synchronous path.
2. **Model tier (selective):** the host's auxiliary LLM
   (`llm_calibrated`) is invoked ONLY on cells the deterministic tier
   flags as borderline.

Neither tier forces XIFT to interpret the knowledge payload — both
operate on vocabulary metadata only. The model tier is inherently
non-deterministic (LLM sampling); because it cannot be made
bit-reproducible across peers, its output is **advisory and never
consensus-bearing** (ADR-XIFT-ONTOLOGY-001 §2.6).

---

## 9. Conformance Tests

The `ontology` extension contributes the following cases to the
conformance suite (prefix `ONT`):

| Case   | Subject                                                                                                       |
|--------|---------------------------------------------------------------------------------------------------------------|
| ONT-01 | Envelope with an `ontology` block and a receiver NOT declaring `ontology` is accepted (no 105).               |
| ONT-02 | Channel-1 advertisement exposes `supported_ontology_formats` and `alignment_methods`; a peer reads them.      |
| ONT-03 | `@context` whose fetched body does not match the `context_hash` pin is rejected (`protocol:ontology:context_hash_mismatch`, 102). |
| ONT-04 | An SCS session runs `ontology_probe` → `ontology_assertion` → `ontology_ack`; the signed synopsis carries the consolidated cells. |
| ONT-05 | A cell with low `alignment_score` and no configured threshold yields a warning (`model:ontology:alignment_score_low`, 303), not a rejection. |
| ONT-06 | With `ontology_alignment_min_score` configured, a required cell below threshold yields an error at the model layer. |
| ONT-07 | A required concept with no acceptable correspondence yields `model:ontology:unmapped_concept` (302).          |
| ONT-08 | The reduced SKOS projection is a partial view; the full source graph is NOT recoverable (privacy).            |
| ONT-09 | When `classification >= sensitive`, the `ontology` block is carried inside the ciphertext (encryption scope), like `quality`. |
| ONT-10 | Frugal tiering: a borderline cell escalates to the model tier; a confidently-matched cell does not.           |
| ONT-11 | Channel 5 (SDR): a query attaching the requester's descriptor makes the `semantic_alignment` dimension vocabulary-aware; an unresolved alignment escalates to SCS. The descriptor is optional. |
| ONT-12 | Channel 6 (SIEA): an announcement WITH a descriptor is matched vocabulary-aware; an otherwise-identical one WITHOUT receives a degraded composite score (`siea_unaligned_match_penalty`), never a rejection. |
| ONT-13 | Channel 7 (SCS): the loop produces cells in the signed synopsis; a subsequent Channel 5/6 exchange MAY reuse cached cells, invalidated on `context_hash` change or age (`ontology_cell_max_age_seconds`). |

---

## 10. Interaction with Other Mechanisms

### 10.1 Channel 5 (SDR) and Channel 6 (SIEA)

The descriptor seeds vocabulary-aware matching. On Channel 5 it is
optional and folds into the `semantic_alignment` score dimension
(channel-5 §7). On Channel 6 it SHOULD be present; an announcement
without one is matched on raw embeddings and receives the
`siea_unaligned_match_penalty`. Cells produced by a prior SCS session
MAY be cached host-internally and reused to sharpen later 5/6 matching,
subject to the freshness rules of §6.

### 10.2 Channel 7 (SCS)

The reciprocal loop (§3.5) is the only place bilateral cells are
produced. It reuses SCS round/journal/synopsis machinery unchanged.

### 10.3 `provenance` and `quality`

The cell's `method` and `mapping_justification` are corroborated by — not
a substitute for — the `provenance` extension: an agent SHOULD record
the derivation of an alignment in `provenance.derivation_method_hash`,
so a mapping's lineage is auditable independently of the cell's
self-description. `alignment_score` plays the same governance role for
knowledge-promotion gating that `quality` plays for artifact promotion,
and pairs naturally with `quality.metrics.downstream_promotion_count`
(§3.3).

---

## 11. Hard Boundary (Non-Goal)

`ontology` provides **mutual interpretability only**. It is **NOT** a
knowledge-reconciliation engine; it does not adjudicate which *fact* is
true (XIFT non-goals §15). An alignment cell states a *belief about
correspondence between vocabulary terms*, never a verdict on factual
truth. `ontology` MUST NOT influence payload interpretation.

---

## 12. Open Questions

1. **Consumed-cell freshness on 5/6.** Beyond `context_hash` change and
   `ontology_cell_max_age_seconds`, should a capability-version bump on
   either peer also invalidate a cached cell?
2. **Cross-vocabulary score composition.** Exactly how `alignment_score`
   folds into the channel-5 §7 `semantic_alignment` composite (weight,
   floor) — a channel-5 scoring detail.
3. **`siea_unaligned_match_penalty` magnitude.** The Channel-6 penalty
   (default 0.5) for a descriptor-less announcement — finalised in
   `xift-1.0-spec-channel-6.md`.
4. **Vocabulary/profile IRI registry.** Deferred for v1.0;
   per-advertisement declaration (§3.4) suffices.
