# `tools/` — repository tooling

## `validate_error_model.py`

Error-model / category-registry linter. Checks that every error
`category` (`layer:domain:sub_category`) and numeric `code` across the
specs, schemas, and the registry stay mutually consistent: category
grammar, per-layer numeric bands, category↔code pairing, orphan and
multi-domain detection, and cross-checks against `xift-error-taxonomy.md`
and the per-extension JSON Schemas.

This file is the **canonical** copy of the linter. The governing
decisions are cited by ID (ADR-XIFT-ERROR-MODEL-001 / -SIGNING-001 /
-MIGRATION-001).

Python 3 standard library only (`jsonschema` is an optional extra used by
the schema sub-check). Each check is tagged `[subset]` (registry-
independent) or `[registry]` (full mode). **Exit code** = number of hard
violations.

| Argument | Effect |
|---|---|
| `--registry PATH` | Full mode: path to `xift-error-taxonomy.md`. |
| `--no-registry` | Subset mode: registry-independent checks only. Mutually exclusive with `--registry`. |
| `--docs GLOB [GLOB ...]` | **Required.** Doc globs to scan (recursive `**` supported). |
| `--schemas DIR` | Extension JSON-schema directory (full mode only). |
| `--warn-only CHECK[,CHECK...]` | Comma list of checks downgraded to advisory. Default: `severity,availability`. |
| `--report` | Print a per-check summary even when clean. |

Full mode against this repo:

```sh
python3 tools/validate_error_model.py \
  --registry spec/xift-error-taxonomy.md \
  --docs 'spec/**/*.md' \
  --schemas contracts/schemas/extensions --report
```
