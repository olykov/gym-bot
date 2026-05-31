---
schema_version: 1
id: GYM-16
title: "Phase 9: Kubernetes"
slug: gym-16-kubernetes
status: backlog
priority: low
type: refactor
labels: [phase-9, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: null
finish_date: null
updated: 2026-05-31T16:00:00Z
epic: roadmap
depends_on: [GYM-9]
blocks: []
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-16 — Phase 9: Kubernetes

## Problem
Single-host Compose deploy cannot scale services independently.

## Plan
Helm charts in infra/k8s; managed Postgres/Redis; ingress+TLS; HPA on stateless services; drop pinned names/ports.

## Comments

### 2026-05-31T16:00:00Z — task created
When load demands it.
