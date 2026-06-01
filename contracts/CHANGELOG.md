# Contracts — Change Log

Consolidated change history for the JSON Schemas and contract documents in
`contracts/` (and `contracts/schemas/`). **Newest first.**

- One row per schema/contract revision. The authoritative history is git
  (`git log --follow -- contracts/<file>`); this file is the curated digest.
- Schemas carry their version in `$id` (`/schemas/v1.0/…`); a backward-
  incompatible change MUST bump that path.

| Date       | Schema / Contract                                | Notes |
|------------|--------------------------------------------------|-------|
| 2026-06-01 | schemas/memory-object.json                       | **Authored** the KnowledgeObject envelope schema (was an empty stub). Flat top-level mandatory blocks per core §3.3 (Identity/Operational/Content/Security) with frozen wire names (`envelope_id`, `memory_scope`, `payload_inline`/`content_ref`, `payload_hash`, `content_type`, …); `oneOf` enforces exactly one of `payload_inline`/`content_ref` (and `payload_hash` required with `content_ref`); `additionalProperties:false` with the six extension blocks as `$ref`s to their `$id` (`extension-*.schema.json`); `dependentSchemas` encodes revocation⇒governance (core §3.3.5). `$defs` for ULID/DID/`sha256:` hash/date-time. Validated against draft 2020-12 with the extension registry. |
| 2026-05-31 | schemas/extensions/ontology.schema.json          | **New** — schema for the sixth extension `ontology` (ADR-XIFT-ONTOLOGY-001). Validates the silently-ignorable vocabulary **descriptor** block (`context_iri`, `context_hash` `sha256:` pin, `format` enum, optional reduced `skos_projection` bounded at 256 concepts, optional `shacl_shapes`) and provides `$defs/alignment_cell` (SSSOM-inspired) for reuse by the Channel-7 SCS synopsis. Mirrors the `quality` schema conventions (`additionalProperties:false`, `$defs`, JCS float note). Code-enforced invariants flagged via `x-xift-note` (`score_function` ↔ `method` consistency; projection privacy). |
