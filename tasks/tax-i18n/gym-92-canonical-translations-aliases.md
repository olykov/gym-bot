---
schema_version: 1
id: GYM-92
title: "Content/DB: canonical EXERCISE translations + aliases seed (RU first) — muscles moved to GYM-109"
slug: gym-92-canonical-translations-aliases
status: done
priority: medium
type: feature
labels: [taxonomy, db, content, i18n]
assignee: null
model: claude-opus-4-8
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-10T04:00:00Z
finish_date: 2026-06-10T04:00:00Z
updated: 2026-06-10T04:00:00Z
epic: tax-i18n
depends_on: [GYM-110]
blocks: []
related: []
commits: [b033952]
tests: ["apps/api/tests/test_gym92_ru_aliases.py"]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-92 — i18n catalog content

## Problem
To let users pick canonical names from a list in their language (and to resolve "Жим лёжа" → Bench Press),
we need translations + aliases for the canonical catalog. Per ADR 0001.

## Scope: content + DB seed (Channel B, ADR 0003). EXERCISES ONLY — muscles localize in GYM-109.
- Prepare RU translations for the 122 canonical exercises (+ common synonyms/abbreviations). EN aliases
  unnecessary (canonical name is already English + searchable via name_key).
- Generation: AI-drafted RU table (`canonical → RU`) → operator review → seed.
- Seed into `exercise_alias.lang='ru'` via migration `0007` (idempotent, `ON CONFLICT DO NOTHING`),
  auto-applied on deploy (GYM-107).
- Enrichment only — does NOT block GYM-93 search (which works over English names).

## Acceptance
- [ ] Canonical exercises/muscles have translations + seeded aliases for the initial language set; seeding
      is idempotent and re-runnable.

## Comments

### 2026-06-10 — RU alias DRAFT produced (`packages/db/seeds/exercise_aliases_ru.tsv`)
- Targets the **curated KEEP set**: the 98 rows with `action==KEEP` in `canonical_curation.tsv`
  (post-curation ADR 0004 / migration 0008). The old draft was stale (pre-curation names) and was
  fully overwritten. Format: `id <TAB> english_canonical <TAB> russian_alias <TAB> source`.
- **wger source attempted (operator preference).** Endpoints used:
  - `GET https://wger.de/api/v2/language/?format=json` → found Russian = language id **5** (en = 2).
  - `GET https://wger.de/api/v2/exercise-translation/?format=json&limit=200` (paginated, 2003 rows) →
    filtered client-side to `language==5`.
  - The `?language=5` query filter on these endpoints is **ignored** by the API; filtering must be done
    client-side on the `language` field.
- **wger coverage = effectively zero for our set.** Only **10** Russian exercise translations exist
  site-wide (Бег, Велотренажор, Гиперэкстензия, Джампинг-Джек, Планка, Повороты головы, Приседание у
  стены, Приседания, Скакалка, Скручивания). None is a confident 1:1 match to our 98 specific
  machine/barbell/cable lifts, so **0 of 98 were taken from wger**.
- **Coverage: 0/98 wger, 98/98 hand-translated** (standard Russian gym terminology). Every KEEP id
  covered exactly once, no missing/extra/dup, all rows have 4 columns, RU column verified for Cyrillic
  (only intentional brand terms kept Latin: Hammer, EZ, JM, V-образная; Smith → «в Смите»).
- wger CC-BY-SA attribution noted in the file header (no wger content was actually used, but the header
  documents the source check + license for the record).
- **Status: `in_progress`** — this is a DRAFT for operator review. Orchestrator seeds via a future
  migration **0009** after sign-off. No commit; .tsv left uncommitted like other seed drafts. Nothing
  on prod touched, no migration built.
- Names worth an operator second look (translation choices, not blockers):
  - `13 Dumbbell Shoulder Press` → "Жим гантелей сидя" (assumes seated; could be "стоя/над головой").
  - `54 Cable Chest Press (Machine)` → "Жим от груди в кроссовере" (cable vs plate-loaded machine wording).
  - `47 Iso-Lateral Front Lat Pulldown` / `5` / `35` → kept "Hammer" brand; alt is "в тренажёре Hammer".
  - `359 Smith Machine JM Press` → "JM-жим в Смите" (JM press has no settled RU term).
  - `15 Upright Row` → "Протяжка" (common gym slang; formal alt: "Тяга штанги к подбородку").

### 2026-06-10T04:00:00Z — done (migration 0009 seeds 98 RU aliases + tested)
Operator signed off on the DRAFT. Built migration
`packages/db/alembic/versions/0009_seed_ru_aliases.py` (revises
`0008_apply_catalog_curation`), GENERATED from the now-committed source
`packages/db/seeds/exercise_aliases_ru.tsv` with values EMBEDDED (TSV not read at
runtime).

- **98 INSERTs** — one per KEEP canonical exercise:
  `INSERT INTO exercise_alias (canonical_id, alias_name, lang) SELECT :cid, :ru,
  'ru' WHERE EXISTS (SELECT 1 FROM exercises WHERE id = :cid) ON CONFLICT
  (canonical_id, name_key) DO NOTHING`. Russian text is a BOUND PARAMETER
  (`:ru`) — never concatenated; `is_global` defaults TRUE, `created_by` NULL
  (global admin-curated catalog), `name_key` is the table's generated column.
- **Sanity passed**: the 98 TSV `canonical_id`s are EXACTLY the 98 KEEP ids from
  0008 (1:1, verified) — every FK resolves post-0008. No DEMOTE/MERGE-source/junk
  ids, no dangling FK. The `WHERE EXISTS` guard additionally makes each row a
  no-op on a fresh/unseeded DB, so the migration never raises a dangling-FK error
  (e.g. the shared conftest DB that bootstraps from `init.sql` with no catalog).
- **downgrade()** is clean and reversible (unlike 0008): `DELETE FROM
  exercise_alias WHERE lang='ru'`.
- **wger dead-end**: wger.de RU exercise coverage is effectively empty (10 RU
  translations site-wide, none a confident match to our 98 machine/barbell/cable
  lifts) → 0/98 from wger, 98/98 hand-translated (standard RU gym terminology).
  CC-BY-SA attribution noted in the seed header for the record.

Green gate (real Postgres 16 via Docker, no skipped integration tests),
`apps/api/tests/test_gym92_ru_aliases.py` — self-contained throwaway DB (own
container, `app_rw` role, init.sql + stamp baseline, seed the 98 KEEP exercises
as FK targets BEFORE upgrade, `alembic upgrade head` runs 0009). Asserts: all 98
`lang='ru'` aliases seeded (count == 98), `name_key == app_name_key(alias_name)`,
every embedded (canonical_id, ru) present verbatim, no dangling canonical FK,
global/admin-owned defaults, ON CONFLICT idempotency (re-run inserts nothing),
downgrade removes exactly the ru rows (reversible), and — END-TO-END through the
real `GET /exercises/search` under `app_rw` + RLS — query `Жим штанги лёжа` with
`lang='ru'` resolves to exercise **id 7 'Barbell Bench Press'** with
`match_reason == 'alias'` (and also without a lang filter).

- E2E RU-search assertion **PASSED**: `test_e2e_ru_query_resolves_via_alias_tier`
  → id 7, name 'Barbell Bench Press', match_reason 'alias'.
- Full suite: **416 passed, 0 skipped, 0 failed** (Docker up).

Branch `i18n/gym-92-ru-seed`, commit `b033952`. NOT merged to main / not applied
to prod (migrations are applied MANUALLY on prod per the RUNBOOK).
