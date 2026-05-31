# Tasks

Project tasks live here, one Markdown file per task with YAML frontmatter, per the universal
kanban skill (`~/.claude/skills/kanban/`). Path convention: `tasks/{epic}/{id}-{slug}.md`.

No tasks yet — the backlog (e.g. the phases in [../docs/ROADMAP.md](../docs/ROADMAP.md)) will be
created here as task files.

Tools (run from the repo root):

```bash
python3 ~/.claude/skills/kanban/scripts/render_kanban.py
python3 ~/.claude/skills/kanban/scripts/validate_tasks.py
```
