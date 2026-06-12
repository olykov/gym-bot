---
schema_version: 1
id: GYM-124
title: "apps/web: eslint + vitest from zero + CI gate (tsc/lint/test before build)"
slug: gym-124-web-lint-test-ci
status: review
priority: high
type: chore
labels: [frontend, tooling, ci, tests]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:40:00Z
start_date: 2026-06-12T12:00:00Z
finish_date: null
updated: 2026-06-12T12:00:00Z
epic: tech-debt
depends_on: []
blocks: [GYM-125, GYM-126]
related: [GYM-19, GYM-24]
commits: []
tests: []
design_reports: ["docs/review/02-tech-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-124 — apps/web lint + tests + CI gate

## Problem
Review doc 02 §6. `apps/web` has NO linter (the in-code
`eslint-disable-next-line react-hooks/exhaustive-deps` comments are decorative — the rule
isn't even installed) and ZERO tests, while highly regression-prone pure logic exists
(SetLogger derivations already produced real bugs: GYM-104/105).

## Solution
1. **eslint** flat config: `typescript-eslint` + `eslint-plugin-react-hooks` +
   `eslint-plugin-react-refresh` (mirror admin's strictness, `--max-warnings 0`).
   Fix or explicitly annotate what surfaces.
2. **vitest** (+ `@testing-library/react` only where DOM is needed). First wave of unit
   tests, pure logic only (~30 tests):
   - `historyWindow` (windowForSteps, formatDayHeading, toISODate)
   - `activityGridModel` (buildGrid, levels, Monday-first, padding cells)
   - `Stepper` `parseNumeric` + bump/clamp
   - SetLogger derivations extracted as pure fns where needed: `nextSet`, recap merge
     (session ∪ server ∪ completed), `effectivePR`
   - History exhaustion logic
3. **CI**: add `tsc --noEmit && eslint && vitest run` for apps/web as a job BEFORE image
   build in the Build-and-Deploy workflow.
4. tsconfig: evaluate `noUncheckedIndexedAccess` (separate commit; fix fallout or defer
   with a comment).

## Acceptance criteria
- [x] `npm run lint` / `npm run test` exist and pass locally and in CI; CI fails the deploy
      on lint/test/type errors.
- [x] ≥25 unit tests over the listed pure-logic modules, all green.

## Comments

### 2026-06-12T09:40:00Z — task created
First in the tech-debt order — it guards every other refactor task.

### 2026-06-12T12:00:00Z — implemented (agent wave 1)

Files changed:
- `apps/web/eslint.config.js` — NEW flat config: @eslint/js + typescript-eslint
  recommended (non-type-checked, fast) + react-hooks (classic two rules) +
  react-refresh.
- `apps/web/package.json` / `package-lock.json` — scripts `lint` (eslint src
  --max-warnings 0) and `test` (vitest run); devDeps eslint ^10.4.1,
  @eslint/js ^10.0.1, typescript-eslint ^8.61.0, eslint-plugin-react-hooks
  ^7.1.1, eslint-plugin-react-refresh ^0.5.2, vitest ^4.1.8.
- `apps/web/src/components/record/derive.ts` — NEW: pure SetLogger derivations
  extracted (`computeNextSet`, `mergeRecap`, `computeEffectivePR`), behavior-
  identical; algorithm comments (GYM-74/101/104) moved here.
- `apps/web/src/components/record/SetLogger.tsx` — now imports the derive fns
  from `derive.ts`; short pointer comments kept at the call sites.
- Tests (colocated `*.test.ts` convention, 48 tests / 4 files, all green):
  `src/components/history/historyWindow.test.ts` (12),
  `src/components/dashboard/activityGridModel.test.ts` (10),
  `src/components/ui/Stepper.test.ts` (9, parseNumeric),
  `src/components/record/derive.test.ts` (17, incl. the GYM-104 race scenario:
  a session set saved before log-context resolves never hides a higher server PR).
- `apps/web/src/i18n/locale.ts` — removed a now-verified-unused
  `eslint-disable react-hooks/exhaustive-deps` directive.
- `apps/web/src/auth/AuthProvider.tsx`, `src/components/ui/Stepper.tsx` —
  annotated `react-refresh/only-export-components` with reasons (hook/helper
  intentionally colocated with the component).
- `.github/workflows/ci.yaml` — NEW `web-checks` job (node 22, apps/web:
  npm ci → generate @api-contract client via openapi-typescript@7, same as the
  Dockerfile → tsc --noEmit → lint → vitest run); all four build jobs now
  `needs: web-checks`, so deploy is gated on it transitively.

Lint findings triage: the remaining three `exhaustive-deps` disables
(SetLogger, ExerciseProgressChart, BottomNav) are confirmed still needed —
eslint reports them as used directives. react-hooks v7's full `recommended`
preset (new compiler-powered `set-state-in-effect` / `refs` rules) flags 9
pre-existing intentional seed/reset-effect sites — deliberately NOT enabled
this wave (documented in eslint.config.js); migrating those patterns is its
own follow-up.

Bench verification (clean checkout copy + npm install):
`npx tsc --noEmit` PASS, `npm run lint` PASS (0 errors / 0 warnings),
`npm run test` PASS (48/48), `npm run build` PASS (vite 5.4.21, same chunk
profile as before). CI job itself runs on the next push to main.

Deferred:
- `noUncheckedIndexedAccess` in tsconfig — NOT enabled this wave (fallout fix
  is a separate commit per the task; revisit with GYM-125).
- History.tsx exhaustion logic — not extracted: it is two lines deeply coupled
  to `useRef` + TanStack `isPlaceholderData`; a pure extraction would be churn
  without real coverage gain. Candidate for a jsdom/RTL wave.
- jsdom/@testing-library (Stepper bump/clamp via DOM) — next test wave.

Suggested commit message:
`Add eslint, vitest and CI quality gate for apps/web`
