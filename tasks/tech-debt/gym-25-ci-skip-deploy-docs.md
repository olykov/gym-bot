---
schema_version: 1
id: GYM-25
title: "CI: skip build/deploy for docs/tasks-only changes"
slug: gym-25-ci-skip-deploy-docs
status: done
priority: high
type: chore
labels: [tech-debt, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T09:50:00Z
start_date: 2026-06-01T09:50:00Z
finish_date: 2026-06-01T09:52:00Z
updated: 2026-06-01T09:52:00Z
epic: tech-debt
depends_on: []
blocks: []
related: [GYM-24]
commits: ["b9534ff"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-25 — CI: skip build/deploy for docs/tasks-only changes

## Problem
Every push to main triggered a full "Build and Deploy" (3 image builds + redeploy), even for commits
that only touch task files or docs. With the kanban workflow committing tasks frequently, this churned
deploys (and recreated containers) for no reason.

## Solution
Added `paths-ignore` to the workflow's `push` trigger so a push whose changed files are ALL within
`tasks/**`, `.claude/**`, `docs/**`, or `**.md` does not run the pipeline. Mixed pushes (code + docs)
still run.

## Comments

### 2026-06-01T09:52:00Z — done
Done by the orchestrator (small infra change). Committed b9534ff. This is the last deploy triggered by
a task/docs change — subsequent task-only commits skip the pipeline. Note: this commit itself touched
.github/workflows/ci.yaml (not ignored), so it deploys once.
