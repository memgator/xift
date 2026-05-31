#!/usr/bin/env python3
"""validate_error_model.py — XIFT error-model / category registry linter.

Freezes the consistency checks that were previously run by hand whenever the
category registry (``xift/spec/xift-error-taxonomy.md``) or a spec/steering doc
changed. See ADR-XIFT-ERROR-MODEL-001 / -SIGNING-001 / -MIGRATION-001 and
``.claude/rules/error-model.md``.

Two modes:

  * ``--registry PATH``   full mode — every check, including the ones that need
                          the registry as source of truth (public gate + local).
  * ``--no-registry``     subset mode — only registry-independent checks
                          (private ``xift-internal`` gate; no sibling checkout).

Each check is tagged ``[subset]`` (runs in both modes) or ``[registry]`` (full
mode only). Exit code = number of hard violations (0 = clean). Standard library
only; ``jsonschema`` is an optional extra used by the schema sub-check.

CLI:

  validate_error_model.py
      [--registry <taxonomy.md> | --no-registry]
      --docs 'GLOB' ['GLOB' ...]
      [--schemas <extensions dir>] [--warn-only CHECK[,CHECK...]] [--report]
"""

from __future__ import annotations

import argparse
import glob as globmod
import json
import os
import re
import sys
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# Configuration (reviewed allow-lists, canonical sets, bands).                 #
# --------------------------------------------------------------------------- #

# Numeric band per layer (core §12.1). A code outside its layer's band is a
# cross-layer mistake regardless of the registry.
LAYER_BANDS = {
    "protocol": (100, 199),
    "policy": (200, 299),
    "model": (300, 399),
    "custom": (900, 999),
}

# Canonical operational codes actually defined in v1.0 (registry §0). A registry
# row whose code is outside this set is malformed.
CANONICAL_CODES = {
    "protocol": set(range(101, 113)),  # 101–112
    "policy": set(range(201, 208)),    # 201–207
    "model": set(range(301, 304)),     # 301–303
    "custom": set(range(901, 1000)),   # 901–999
}
OK_CODE = 0

# Category grammar: layer:domain:sub_category, snake_case, no leading digits.
_CAT_BODY = r"(?:protocol|policy|model|custom):[a-z][a-z0-9_]*:[a-z][a-z0-9_]*"
CATEGORY_RE = re.compile(r"\A" + _CAT_BODY + r"\Z")

# Pair shapes (category + code on the same line):
#   prose:  `layer:domain:sub` (NNN)
#   table:  | NNN | `layer:domain:sub` | …
PROSE_PAIR_RE = re.compile(r"`(" + _CAT_BODY + r")`\s*\((\d{3})\)")
TABLE_PAIR_RE = re.compile(r"^\s*\|\s*(\d{1,3})\s*\|\s*`(" + _CAT_BODY + r")`")
# Any backticked full category occurrence (for grammar / orphan / multi-domain).
CATEGORY_TOKEN_RE = re.compile(r"`(" + _CAT_BODY + r")`")
# A backticked token that *looks* like a category (right layer prefix + 2 colons)
# but may be malformed — used by the grammar check.
LOOSE_CAT_RE = re.compile(r"`((?:protocol|policy|model|custom):[^`]+)`")
# Bare category occurrence anywhere in a string (no backticks) — used to scan
# embedded categories inside JSON-schema note values.
BARE_CAT_RE = re.compile(r"\b(" + _CAT_BODY + r")\b")

# Legacy 4-digit codes (the pre-migration scheme). Rather than flag every bare
# 1000–9999 (which collides with budgets, IDs, years, and algorithm names such
# as "Poly1305"), match a 4-digit number only where an error *code* would sit:
#   * after error|code|status|reject…   ("error 1009")
#   * parenthesised on its own          ("(1009)" — the code-annotation form)
#   * as a leading table cell           ("| 1009 | `cat` |")
LEGACY_CONTEXT_RES = (
    re.compile(r"(?i)\b(?:error|code|status|rejects?|rejected|reject with)\s+#?([1-9]\d{3})\b"),
    re.compile(r"\(([1-9]\d{3})\)"),
    re.compile(r"^\s*\|\s*([1-9]\d{3})\s*\|"),
)
# Bare 4-digit numbers that are legitimately not error codes.
LEGACY_ALLOWED_LITERALS = {1000, 1024, 2048, 3600}
# Files that legitimately document the legacy scheme (skipped by the legacy scan).
LEGACY_EXEMPT_FILES = {
    "xift-error-migration-map.md",
    "ADR-XIFT-ERROR-MODEL-001.md",
    "ADR-XIFT-ERROR-MIGRATION-001.md",
}
# Per-line marker that opts a line out of the legacy scan.
MIGRATION_MARKER = "MIGRATION NOTE"

# Categories that may be cited without a registry row (by-design gaps):
#   * model:*  — the model layer is intentionally uncatalogued (LLM-adjudicated).
#   * custom:* — the custom layer is per-deployment and carries no registry
#     codes (registry §0/§13); only illustrative examples appear in docs.
#   * protocol:custodian:preattestation_* — defined only by a `status: proposed`
#     ADR (ADR-CUSTODIAN-SCALE-001); register on acceptance.
ORPHAN_ALLOW_PREFIXES = (
    "model:",
    "custom:",
    "protocol:custodian:preattestation_",
)

# sub_category mnemonics that legitimately appear under more than one domain.
MULTI_DOMAIN_ALLOW = {"session_token_invalid"}

# Layer-placement principle (registry §13): availability / capacity / reachability
# of a protocol component (channel, extension, field, custodian) is `protocol`;
# `policy` is reserved for governance / authorization / trust / consent / budget.
# A `policy:*` category whose sub_category carries availability semantics is a
# likely mis-layering — flagged advisory (heuristic; never a hard violation).
AVAILABILITY_HINTS = (
    "unavailable", "unreachable", "degraded", "quota_exceeded", "_capacity",
    "capacity_", "_lost", "terminated", "stale", "rate_limit", "direct_fetch",
)
# Genuine policy categories that contain a hint word but are correctly policy.
#   * consensus_unreachable — "unreachable" refers to a session consensus
#     outcome, not to a protocol component being unreachable.
AVAILABILITY_HINT_ALLOW = {"policy:channel7:consensus_unreachable"}

# --------------------------------------------------------------------------- #
# Findings.                                                                    #
# --------------------------------------------------------------------------- #


@dataclass
class Finding:
    check: str
    hard: bool
    file: str
    line: int
    msg: str


@dataclass
class RegistryRow:
    category: str
    code: int
    layer: str
    severity: str
    domain: str
    sub: str
    line: int


@dataclass
class Registry:
    rows: dict = field(default_factory=dict)       # category -> RegistryRow
    allowed_domains: set = field(default_factory=set)


# --------------------------------------------------------------------------- #
# Markdown table parsing.                                                      #
# --------------------------------------------------------------------------- #


def _split_row(line: str) -> list:
    """Split a markdown table row into trimmed cell strings."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_separator(line: str) -> bool:
    return bool(re.match(r"^\s*\|[\s:\-|]+\|\s*$", line))


def iter_registry_tables(lines):
    """Yield (header_cells, [(lineno, cells), ...]) for each markdown table that
    has both a Code and a Category column."""
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.lstrip().startswith("|") and i + 1 < n and _is_separator(lines[i + 1]):
            header = [h.lower() for h in _split_row(line)]
            body = []
            j = i + 2
            while j < n and lines[j].lstrip().startswith("|") and not _is_separator(lines[j]):
                body.append((j + 1, _split_row(lines[j])))
                j += 1
            if "code" in header and "category" in header:
                yield header, body
            i = j
        else:
            i += 1


# --------------------------------------------------------------------------- #
# Registry loading + self-consistency (check 1).                              #
# --------------------------------------------------------------------------- #


def derive_allowed_domains(text: str) -> set:
    """Domain allow-list derived from the registry itself: the §0 segment
    paragraph, the channelN tokens, and every `domain=...` section header."""
    domains = set()
    # channelN tokens anywhere.
    domains.update(re.findall(r"channel[1-7]", text))
    # `domain=...` header annotations (incl. `domain=a|b`).
    for grp in re.findall(r"domain=([a-z0-9_|]+)", text):
        domains.update(grp.split("|"))
    # The "Category `domain` segments:" paragraph.
    m = re.search(r"Category `domain` segments:(.+?)\n\s*\n", text, re.S)
    if m:
        domains.update(re.findall(r"`([a-z][a-z0-9_]*)`", m.group(1)))
    return domains


def load_registry(path: str) -> tuple:
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()
    reg = Registry(allowed_domains=derive_allowed_domains(text))
    findings = []
    seen_codes = {}  # category -> set(codes)

    for header, body in iter_registry_tables(lines):
        idx = {name: header.index(name) for name in ("code", "category", "layer", "severity")
               if name in header}
        for lineno, cells in body:
            if max(idx.values(), default=-1) >= len(cells):
                continue
            raw_code = cells[idx["code"]].strip("` ")
            raw_cat = cells[idx["category"]].strip().strip("`").strip()
            if not raw_cat:
                continue
            # Grammar.
            if not CATEGORY_RE.match(raw_cat):
                findings.append(Finding("registry", True, path, lineno,
                                        f"category '{raw_cat}' violates grammar"))
                continue
            layer, domain, sub = raw_cat.split(":")
            # Code.
            try:
                code = int(raw_code)
            except ValueError:
                findings.append(Finding("registry", True, path, lineno,
                                        f"{raw_cat}: non-numeric code '{raw_code}'"))
                continue
            # Layer cell vs category prefix.
            if "layer" in idx:
                cell_layer = cells[idx["layer"]].strip()
                if cell_layer and cell_layer != layer:
                    findings.append(Finding("registry", True, path, lineno,
                                            f"{raw_cat}: layer column '{cell_layer}' "
                                            f"!= category layer '{layer}'"))
            # Canonical code for layer.
            if code != OK_CODE and code not in CANONICAL_CODES.get(layer, set()):
                findings.append(Finding("registry", True, path, lineno,
                                        f"{raw_cat}: code {code} not canonical for "
                                        f"layer '{layer}'"))
            # Severity.
            sev = cells[idx["severity"]].strip().lower() if "severity" in idx else ""
            if sev not in ("error", "warning"):
                findings.append(Finding("registry", True, path, lineno,
                                        f"{raw_cat}: severity '{sev}' not error|warning"))
            # Domain in allow-list.
            if domain not in reg.allowed_domains:
                findings.append(Finding("registry", True, path, lineno,
                                        f"{raw_cat}: domain '{domain}' not declared "
                                        f"in §0 / domain= headers"))
            # Duplicate category / multi-code.
            seen_codes.setdefault(raw_cat, set()).add(code)
            if raw_cat in reg.rows:
                prev = reg.rows[raw_cat]
                if prev.code != code:
                    findings.append(Finding("registry", True, path, lineno,
                                            f"{raw_cat}: bound to codes {prev.code} "
                                            f"and {code}"))
                else:
                    findings.append(Finding("registry", True, path, lineno,
                                            f"{raw_cat}: duplicate registry row "
                                            f"(also line {prev.line})"))
            else:
                reg.rows[raw_cat] = RegistryRow(raw_cat, code, layer, sev, domain, sub, lineno)

    return reg, findings


# --------------------------------------------------------------------------- #
# Document scanning.                                                           #
# --------------------------------------------------------------------------- #


def legacy_scan(path, lineno, line, findings):
    """[subset] Check 2 — no legacy 4-digit codes in code-positions."""
    if MIGRATION_MARKER in line:
        return
    for rx in LEGACY_CONTEXT_RES:
        for m in rx.finditer(line):
            num = int(m.group(1))
            if num in LEGACY_ALLOWED_LITERALS:
                continue
            if 1900 <= num <= 2099:  # years (e.g. a parenthesised "(2026)")
                continue
            pre = line[:m.start(1)]
            if re.search(r"(?i)rfc[\s\-]*$", pre):  # RFC 8785 etc.
                continue
            findings.append(Finding("legacy", True, path, lineno,
                                    f"legacy 4-digit code {num} "
                                    f"(use a namespaced category)"))


def scan_file(path, registry, mode, multi_domain, warn_only, findings):
    """Run the per-file checks. `multi_domain` accumulates sub -> {(domain, file, line)}."""
    fname = os.path.basename(path)
    legacy_exempt = fname in LEGACY_EXEMPT_FILES or any(
        fname.startswith(stem.rsplit(".", 1)[0]) for stem in LEGACY_EXEMPT_FILES)

    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError as exc:
        findings.append(Finding("io", True, path, 0, f"cannot read: {exc}"))
        return

    skip_level = None  # heading depth of an active "Change Log" section
    for lineno, line in enumerate(lines, 1):
        # Change Log sections narrate past states and legitimately cite retired
        # or renamed categories and legacy codes — skip them for all checks.
        hm = re.match(r"^(#+)\s+(.*)$", line)
        if hm:
            level = len(hm.group(1))
            if skip_level is not None and level <= skip_level:
                skip_level = None
            if re.search(r"(?i)change\s*log", hm.group(2)):
                skip_level = level
        if skip_level is not None:
            continue

        # Check 2 — legacy codes.
        if not legacy_exempt:
            legacy_scan(path, lineno, line, findings)

        # Collect (category, code) pairs on this line.
        pairs = [(c, int(code)) for (c, code) in PROSE_PAIR_RE.findall(line)]
        for code, c in TABLE_PAIR_RE.findall(line):
            pairs.append((c, int(code)))

        for cat, code in pairs:
            layer = cat.split(":")[0]
            lo, hi = LAYER_BANDS[layer]
            # Check 3a — band-by-layer [subset].
            if not (lo <= code <= hi or code == OK_CODE):
                findings.append(Finding("band", True, path, lineno,
                                        f"{cat} annotated ({code}); code outside "
                                        f"'{layer}' band {lo}–{hi}"))
                continue
            # Check 3b — exact code [registry].
            if registry is not None and cat in registry.rows:
                want = registry.rows[cat].code
                if want != code:
                    findings.append(Finding("exact", True, path, lineno,
                                            f"{cat} annotated ({code}); registry says "
                                            f"{want}"))
            # Check 4 — severity heuristic [registry, advisory]. Only the
            # high-signal direction: a registry warning described as a hard
            # rejection. (The reverse — an error line that merely mentions a
            # "warning" — is almost always a legitimate cross-reference and was
            # too noisy to keep.)
            if registry is not None and cat in registry.rows:
                if (registry.rows[cat].severity == "warning"
                        and re.search(r"\bMUST\s+(reject|refuse)\b", line)):
                    findings.append(Finding(
                        "severity", "severity" not in warn_only, path, lineno,
                        f"{cat}: registry=warning but line says MUST reject/refuse"))

        # Grammar [subset] — backticked tokens that look like categories but
        # fail. Skip namespace references (wildcard `*`, enumeration `a|b`,
        # ellipsis `…`/`...`) and multi-word backtick labels that merely embed a
        # category (e.g. a Mermaid node label "`cat (101)`") — both are
        # documentation notation, not concrete citations.
        for cand in LOOSE_CAT_RE.findall(line):
            if any(ch in cand for ch in "*|…") or "..." in cand:
                continue
            if any(ch.isspace() for ch in cand):
                continue
            if cand.count(":") == 2 and not CATEGORY_RE.match(cand):
                findings.append(Finding("grammar", True, path, lineno,
                                        f"malformed category '{cand}'"))

        # Orphan [registry] + multi-domain [subset] over every category token.
        for cat in CATEGORY_TOKEN_RE.findall(line):
            layer, domain, sub = cat.split(":")
            multi_domain.setdefault(sub, set()).add((domain, path, lineno))
            if registry is not None and cat not in registry.rows:
                if not any(cat.startswith(p) for p in ORPHAN_ALLOW_PREFIXES):
                    findings.append(Finding("orphan", True, path, lineno,
                                            f"{cat} not in registry"))


def check_availability(registry, reg_path, warn_only, findings):
    """Check 8 [registry, advisory] — a policy category with availability
    semantics is a likely mis-layering (registry §13 principle)."""
    for cat, row in registry.rows.items():
        if row.layer != "policy" or cat in AVAILABILITY_HINT_ALLOW:
            continue
        if any(h in row.sub for h in AVAILABILITY_HINTS):
            findings.append(Finding(
                "availability", "availability" not in warn_only, reg_path,
                row.line, f"{cat}: availability/capacity semantics under `policy` "
                f"— protocol layer expected (registry §13)"))


def check_multi_domain(multi_domain, findings):
    """Check 6 [subset] — same sub_category under more than one domain."""
    for sub, occ in multi_domain.items():
        domains = {d for (d, _f, _l) in occ}
        if len(domains) > 1 and sub not in MULTI_DOMAIN_ALLOW:
            d, f, ln = sorted(occ)[0]
            findings.append(Finding("multidomain", True, f, ln,
                                    f"sub_category '{sub}' under domains "
                                    f"{sorted(domains)}"))


# --------------------------------------------------------------------------- #
# JSON Schema sanity (check 7).                                               #
# --------------------------------------------------------------------------- #


def _iter_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_strings(v)


def check_schemas(schemas_dir, registry, findings):
    """[registry, optional] meta-validate the extension schemas and confirm any
    embedded category string is registered."""
    paths = sorted(globmod.glob(os.path.join(schemas_dir, "*.schema.json")))
    if not paths:
        findings.append(Finding("schema", False, schemas_dir, 0,
                                "no *.schema.json found"))
        return
    for p in paths:
        try:
            doc = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError) as exc:
            findings.append(Finding("schema", True, p, 0, f"invalid JSON: {exc}"))
            continue
        sch = doc.get("$schema", "")
        if "2020-12" not in sch:
            findings.append(Finding("schema", True, p, 0,
                                    f"$schema is '{sch}', expected draft 2020-12"))
        for s in _iter_strings(doc):
            for m in BARE_CAT_RE.finditer(s):
                cat = m.group(1)
                if registry is not None and cat not in registry.rows:
                    if not any(cat.startswith(pre) for pre in ORPHAN_ALLOW_PREFIXES):
                        findings.append(Finding("schema", True, p, 0,
                                                f"embedded category {cat} not in "
                                                f"registry"))


# --------------------------------------------------------------------------- #
# Driver.                                                                      #
# --------------------------------------------------------------------------- #


def expand_globs(patterns, exclude):
    seen = []
    excl = {os.path.abspath(e) for e in exclude if e}
    for pat in patterns:
        for path in sorted(globmod.glob(pat, recursive=True)):
            ap = os.path.abspath(path)
            if os.path.isfile(path) and ap not in excl and ap not in {os.path.abspath(s) for s in seen}:
                seen.append(path)
    return seen


CHECK_LABELS = {
    "registry": "1. registry self-consistency [registry]",
    "legacy": "2. no legacy 4-digit codes   [subset]",
    "band": "3a. band-by-layer            [subset]",
    "exact": "3b. exact code↔category      [registry]",
    "severity": "4. severity heuristic        [registry, advisory]",
    "orphan": "5. orphan categories         [registry]",
    "multidomain": "6. multi-domain sub_category [subset]",
    "grammar": "g. category grammar          [subset]",
    "schema": "7. JSON Schema sanity        [registry]",
    "availability": "8. availability vs layer     [registry, advisory]",
    "io": "io. file access",
}


def main(argv=None):
    ap = argparse.ArgumentParser(description="XIFT error-model / registry linter.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--registry", help="path to xift-error-taxonomy.md (full mode)")
    g.add_argument("--no-registry", action="store_true",
                   help="subset mode: registry-independent checks only")
    ap.add_argument("--docs", nargs="+", required=True, metavar="GLOB",
                    help="doc globs to scan (recursive ** supported)")
    ap.add_argument("--schemas", help="extension JSON-schema dir (full mode only)")
    ap.add_argument("--warn-only", default="severity,availability",
                    help="comma list of checks downgraded to advisory "
                         "(default: severity,availability)")
    ap.add_argument("--report", action="store_true",
                    help="print a per-check summary even when clean")
    args = ap.parse_args(argv)

    warn_only = {c.strip() for c in args.warn_only.split(",") if c.strip()}
    findings = []
    registry = None

    if args.registry:
        registry, reg_findings = load_registry(args.registry)
        findings.extend(reg_findings)
    elif not args.no_registry:
        ap.error("one of --registry or --no-registry is required")

    docs = expand_globs(args.docs, exclude=[args.registry])
    if not docs:
        print("warning: no documents matched --docs globs", file=sys.stderr)

    multi_domain = {}
    for path in docs:
        scan_file(path, registry, "full" if registry else "subset",
                  multi_domain, warn_only, findings)
    check_multi_domain(multi_domain, findings)
    if registry is not None:
        check_availability(registry, args.registry, warn_only, findings)

    if args.schemas:
        if registry is None:
            print("note: --schemas needs --registry; skipping schema check",
                  file=sys.stderr)
        else:
            check_schemas(args.schemas, registry, findings)

    # Report.
    hard = [f for f in findings if f.hard]
    advisory = [f for f in findings if not f.hard]

    by_file = {}
    for f in findings:
        by_file.setdefault(f.file, []).append(f)
    for fpath in sorted(by_file):
        for f in sorted(by_file[fpath], key=lambda x: (x.line, x.check)):
            tag = "ERROR " if f.hard else "warn  "
            print(f"{tag}{f.file}:{f.line}: [{f.check}] {f.msg}")

    if args.report:
        print("\n--- summary ---")
        mode = "full (--registry)" if registry else "subset (--no-registry)"
        print(f"mode: {mode}")
        if registry is not None:
            print(f"registry rows: {len(registry.rows)}; "
                  f"allowed domains: {len(registry.allowed_domains)}")
        print(f"documents scanned: {len(docs)}")
        counts = {}
        for f in findings:
            counts.setdefault(f.check, [0, 0])
            counts[f.check][0 if f.hard else 1] += 1
        for check, label in CHECK_LABELS.items():
            skipped = registry is None and check in ("exact", "orphan", "severity",
                                                     "schema", "registry", "availability")
            h, a = counts.get(check, [0, 0])
            state = "skipped" if skipped and (h + a) == 0 else f"{h} hard, {a} advisory"
            print(f"  {label}: {state}")
        print(f"TOTAL: {len(hard)} hard, {len(advisory)} advisory")

    if hard:
        print(f"\n{len(hard)} hard violation(s).", file=sys.stderr)
    return min(len(hard), 250)


if __name__ == "__main__":
    sys.exit(main())
