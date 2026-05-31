# Contracts — Change Log

Consolidated change history for the JSON Schemas and contract documents in
`contracts/` (and `contracts/schemas/`). **Newest first.**

- One row per schema/contract revision. The authoritative history is git
  (`git log --follow -- contracts/<file>`); this file is the curated digest.
- Schemas carry their version in `$id` (`/schemas/v1.0/…`); a backward-
  incompatible change MUST bump that path.

| Date       | Schema / Contract                                | Notes |
|------------|--------------------------------------------------|-------|
| 2026-05-31 | schemas/extensions/ontology.schema.json          | **New** — schema for the sixth extension `ontology` (ADR-XIFT-ONTOLOGY-001). Validates the silently-ignorable vocabulary **descriptor** block (`context_iri`, `context_hash` `sha256:` pin, `format` enum, optional reduced `skos_projection` bounded at 256 concepts, optional `shacl_shapes`) and provides `$defs/alignment_cell` (SSSOM-inspired) for reuse by the Channel-7 SCS synopsis. Mirrors the `quality` schema conventions (`additionalProperties:false`, `$defs`, JCS float note). Code-enforced invariants flagged via `x-xift-note` (`score_function` ↔ `method` consistency; projection privacy). |
