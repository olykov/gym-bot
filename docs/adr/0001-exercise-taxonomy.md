# ADR 0001 — Exercise & muscle taxonomy: canonical reference model

- Status: accepted (planning)
- Date: 2026-06-08
- Deciders: oleksii (operator)
- Context tasks: epics tax-foundation / tax-linking / tax-moves / tax-i18n / tax-ai

## Context
Users can add their own muscles/exercises alongside a shared default catalog. We want users to feel
full ownership (rename/delete/move freely) WITHOUT losing the canonical identity that future cross-user
features (ratings, achievements-vs-others, competitions, AI muscle balance) depend on. We also need to
stop literal duplicates and, eventually, recognise that "Жим лёжа" == "Bench Press".

## Decision
1. **Reference + overrides (NOT a naive per-user fork).** Keep a canonical exercise/muscle catalog with
   stable `canonical_id`s. A user "owns" a per-user row that REFERENCES the canonical and carries their
   overrides (display_name, hidden, sort, and — later — muscle placement). Renaming a canonical = setting
   a personal alias while the `canonical_id` link persists. Custom user-invented exercises have
   `canonical_id = NULL` until linked. (Rejected: copying the whole catalog per user at registration —
   it destroys canonical identity, freezes the default library, and makes the matching problem mandatory
   for everyone instead of optional for the long tail.)
2. **Two separate layers.** (a) Lexical dedup via a normalized `name_key` + UNIQUE index — catches
   "Bench Press"/"bench-press"/"bench_press"/"BENCH  PRESS". (b) Semantic matching (synonyms/translations)
   via an alias table → fuzzy → embeddings → LLM. Normalization can NOT catch synonyms; they are distinct
   problems with distinct tools.
3. **Add resolves-to-existing, never blind-creates a dup.** On add: normalize → if a visible item matches
   the key, use it; if it was HIDDEN, **silently unhide** it (no prompt); else create a new custom. Adding
   a name that duplicates one you already have (visible) → reject ("you already have this"). Same dedup on
   rename (effective key in the visible set).
4. **Manual Link/Unlink first; AI suggests-not-binds, last.** A custom exercise links to a canonical only
   by user choice (pick from a list, scoped to the SAME muscle, no free-add). Linked exercises are
   highlighted. AI (fuzzy/embedding) only ever SUGGESTS a link for user confirmation — never binds silently
   (a wrong silent bind pollutes shared leaderboards). AI matching is the LAST phase.
5. **i18n catalog + pick-from-list.** We prepare canonical exercises/muscles translated into many languages
   + per-language aliases. The add flow becomes a search-and-pick dropdown over canonical+aliases; free-text
   "create as-is" is offered only as the last resort. This trains users onto canonical names and closes
   most dedup/matching at the source.
6. **Merge is a first-class operation.** Canonical entries will need merging/splitting over time; build a
   merge (repoint all user rows + training A→B, keep alias) early — it is painful to retrofit.
7. **Placement is overridable.** Users may disagree with canonical muscle placement (e.g. Brachioradialis
   Barbell Curl in Biceps vs Forearms) and may misplace their own (Squat under Chest). Moving OWN exercises
   between muscles ships now; canonical-placement override policy is a separate decision (tax-moves).

## Consequences
- Personal tracking works fully even for unmatched custom exercises; canonical link is optional metadata
  needed only for cross-user features.
- Shared surfaces (leaderboards) display the CANONICAL name, not a user's private alias.
- More schema (canonical_id, name_key, alias table, merge) but identity is preserved for the whole roadmap.

## Rejected
- **Naive full per-user fork** of the catalog at registration — simple ownership, but loses canonical
  identity, freezes the library, and makes matching mandatory for all. See discussion 2026-06-07/08.
