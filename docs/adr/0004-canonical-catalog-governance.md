# ADR 0004 — Canonical catalog governance: curated public set, demote-to-personal, free-exercise-db anchor

- Status: accepted (operator approved 2026-06-10)
- Date: 2026-06-10
- Relates to: ADR 0001 (reference + overrides), ADR 0003 (i18n: exercises are Channel B / DB aliases)
- Epic/tasks: catalog-curation (GYM-110 apply curation), blocks GYM-92 (RU seed runs on the clean set)

## Context
The "global" exercise catalog (122 rows) is really **one operator's** idiosyncratic set, accreted over a
couple of years: inconsistent naming, niche/personal machines, duplicates, and names whose meaning is
non-obvious. Usage check on prod: only **4 users** have ever logged training, and every exercise in the
cleanup set is **single-user (the operator)**. Before this becomes a genuinely public canonical catalog,
it must be curated. Translating (GYM-92) before curating would waste effort and bake wrong names.

## Decision
The canonical (public, `is_global=true`) catalog is a **curated set with standard names**, anchored to an
authoritative open dataset. Three operations, applied by a single tested data migration:

- **KEEP (rename)** — stays public; renamed to a standard canonical name. Authoritative names are
  cross-referenced against **free-exercise-db** (yuhonas, public domain) — also pulling equipment +
  primary muscle. The exercise **id is unchanged**, so all training history stays attached.
- **DEMOTE** — niche/personal/ambiguous exercises move to the **operator's personal list**:
  `is_global=false`, `created_by=<operator users.id>` (telegram olykov / 2107709598). Id unchanged →
  history intact; RLS then shows it only to the operator.
- **MERGE (A→B)** — for duplicates: **repoint** A's `training` rows to B (`UPDATE training SET
  exercise_id=B WHERE exercise_id=A`), then **delete** A. This is GYM-88-class work; single-user data, low
  risk, but done under tests. Merge map lives in the worksheet.

Source of truth for the decisions: `packages/db/seeds/canonical_curation.tsv` (operator-reviewed worksheet).
Current tally (v3): **~97 KEEP / ~19 DEMOTE / 5 MERGE** (+ a Bulgarian rename-swap so the dumbbell variant
becomes canonical without moving 58 sets).

After curation, **GYM-92** seeds RU aliases on the clean canonical set — RU sourced from **wger**
(open-source, community Russian translations), per ADR 0003 Channel B.

## Consequences
- One careful migration mutates prod catalog data (renames + ownership flips + repoint+delete). Idempotent
  where possible; tested against a real DB; auto-applies via the on-deploy migration step (GYM-107).
- Training history is preserved for every exercise (id-stable for KEEP/DEMOTE; repointed for MERGE).
- The catalog shifts from "one person's list" to an industry-standard set; demoted items remain fully usable
  by the operator, just not public.
- `muscle_alias` remains unnecessary (ADR 0003): muscles localize via the frontend catalog.
