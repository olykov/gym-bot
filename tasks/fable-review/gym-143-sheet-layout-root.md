---
schema_version: 1
id: GYM-143
title: "Bottom-sheet layout system (root-cause): content never hidden behind sticky footer, no overflow, dynamic height"
slug: gym-143-sheet-layout-root
status: backlog
priority: critical
type: refactor
labels: [frontend, design, ux, sheets, root-cause]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:00:00Z
start_date: null
finish_date: null
updated: 2026-06-12T09:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-140]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-143 — Bottom-sheet layout system (root-cause fix)

## Problem
RECURRING across sheets — elements don't fit, hide, or overflow; no robust dynamic sizing. The earlier
fixes (footer offset by `--nav-h` in GYM-140, flex centering) treated SYMPTOMS; the underlying
content-vs-sticky-footer model is wrong. Operator on-device evidence (screenshots 2026-06-12):
- **SetEditor**: the sticky SAVE button OVERLAPS the last field (REPS stepper) — REPS is clipped/hidden
  behind SAVE. The scroll content area does not reserve the footer's height, so the footer covers content.
- **MoveSetPanel**: the DAY date input OVERFLOWS the right screen edge (horizontal overflow, not
  width-constrained to the container); a squished/clipped element sits between EXERCISE and MOVE SET;
  dead space below MOVE SET.

## Solution — fix the model at the root (shared `BottomSheet` + `SheetSaveButton`)
- The scrollable content area MUST reserve bottom space = `sticky-footer height + --nav-h + safe-area`, so
  the LAST field always scrolls clear of the footer (never hidden behind SAVE/MOVE SET).
- Inputs/fields width-constrained to the sheet container — NO horizontal overflow (the DAY date input).
- Sheet height adapts to content: short content → compact; tall content → internal scroll. No clipped or
  squished rows, no dead space, no fields under the footer.
- ONE consistent model applied to ALL sheets: SetEditor, MoveSetPanel, SetLogger, the record picker sheets.
  Keep SAVE/MOVE SET above the bottom nav (don't regress GYM-140's nav clearance).
- MUST go through the `frontend-design` plugin + obey docs/frontend-spec.md. Tokens only.

## Acceptance
- [ ] SetEditor: WEIGHT + REPS both fully visible; SAVE never overlaps a field; works at small + tall viewports.
- [ ] MoveSetPanel: DAY input fits the container (no overflow); all fields visible; MOVE SET above nav; no dead space.
- [ ] Record SetLogger SAVE + fields unaffected/correct.
- [ ] Verified via headless SCREENSHOTS at 2+ viewport heights (orchestrator re-verifies).

## Comments

### 2026-06-12T09:00:00Z — created
Operator escalation: stop patching, fix the sheet height/footer model at the root. Awaiting operator approval to launch.
