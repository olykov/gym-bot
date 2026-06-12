---
schema_version: 1
id: GYM-137
title: "Bot: show delta vs last session in the set-saved confirmation message"
slug: gym-137-bot-save-delta
status: review
priority: low
type: feature
labels: [bot, progression]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T10:50:00Z
start_date: 2026-06-12T18:10:00Z
finish_date: null
updated: 2026-06-12T18:10:00Z
epic: progression
depends_on: []
blocks: []
related: [GYM-71, GYM-130]
commits: []
tests: []
design_reports: ["docs/review/03-progressive-overload-concept.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-137 — Bot parity: delta in save confirmation

## Problem
Concept doc 03 §5. The bot stays a second logging client; it should echo the same
"fight yourself" signal cheaply — no ghost tables, just one line.

## Solution
- After a successful set save in the bot, append the delta to the confirmation:
  `Записал: 102.5×8 (▲ +2.5 кг к прошлой сессии)` / `(= как в прошлой сессии)`.
- Data: the bot calls the Core API — reuse `GET /analytics/log-context` (service-token +
  X-Telegram-Id path) for `last_session_sets`; same weight-then-reps delta rule as GYM-130.
- Localized per the bot's existing language handling; no new bot keyboards/steps.

## Acceptance criteria
- [ ] Confirmation shows the correct delta (or nothing when no prior session) — manual
      smoke per CLAUDE.md testing reality (bot has no test suite).
      (code in review; pure delta helper verified by direct execution; manual smoke pending
      for operator — steps below)

## Comments

### 2026-06-12T10:50:00Z — task created

### 2026-06-12T18:10:00Z — implemented (agent wave 7b)
Files:
- `packages/api-contract/clients/python/gym_api_client/client.py` — added `get_log_context`
  (hand-maintained wrapper, mirrors `get_completed_sets`; service-token + `X-Act-As-User`
  flow identical to every other analytics call — no new client pattern).
- `apps/bot/modules/delta.py` (new) — pure helpers `compute_delta_text` /
  `delta_note_for_set` mirroring the LOCKED GYM-130 rule from apps/web `derive.computeDelta`:
  weight compared first, reps only break a weight tie; no matching set N in
  `last_session_sets` → empty string (nothing fabricated).
- `apps/bot/modules/confirmation.py` (new) — `fetch_save_delta_note` (calls
  `GET /analytics/log-context` via the shared `api` client, date = UTC today; ANY exception →
  `logger.warning` + empty note, the save confirmation is never blocked) and
  `build_save_confirmation` (table + optional delta line). `format_result_message` and
  `normalize_weight_format` MOVED here from handlers.py unchanged ("don't grow handlers.py —
  split when you touch it", per CLAUDE.md).
- `apps/bot/modules/handlers.py` — `process_reps` success branch now calls
  `build_save_confirmation`; imports the moved helpers from modules.confirmation.
  Net effect: handlers.py shrank 679 → 646 lines.

Language note: the bot's UI is **English-only** (verified across handlers.py — "Select a body
part", "Error saving training…"), so the delta strings are English, mirroring the web app's
en i18n keys (`▲ +{amount}kg` / `▼ −{amount}kg` / rep(s); ▲▼ and U+2212 minus match web):
`(▲ +2.5kg vs last session)` / `(▼ −2.5kg vs last session)` / `(▲ +2 reps vs last session)` /
`(= same as last session)`; no line when last session has no set with that number.

Verification (agent sandbox):
- py_compile green on delta.py / confirmation.py / handlers.py / client.py; the full bot
  import graph (`modules/__init__` → handlers → confirmation → api/delta) loads without
  circular imports (checked with real deps: aiogram, prettytable, httpx, gym_api_client).
- Pure helper executed directly with real `gym_api_client.models.LogSet` objects: weight-up
  beats reps-down, weight-down, reps tiebreak (plural + singular "rep"), equal, missing set N
  → "" and trailing-zero trimming all assert-verified.
- Bot has NO test suite (per CLAUDE.md) — none invented.

Manual smoke (operator):
1. Log a set for an exercise trained on a previous day; confirm the table is followed by
   `(▲/▼/= … vs last session)` matching the same set number of the prior session.
2. Log a set number that did not exist in the prior session → no delta line.
3. First-ever exercise → no delta line.
4. Stop the API mid-flow / force log-context failure → confirmation still arrives without
   the delta; `log-context unavailable` warning in bot logs.

Suggested commit: `Show last-session delta in bot save confirmation`
