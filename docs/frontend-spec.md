# Frontend Spec — `apps/web` (Gym Telegram Mini App)

> Canonical, binding spec for the client web app. Every frontend agent and PR MUST follow it.
> It exists so the UI is **stable, consistent, mobile-first, and on-brand** — not a patchwork of
> different widths, paddings, and ad-hoc components. Distinctive aesthetics live in the *details*;
> the *structure* is disciplined and identical on every screen.

## 0. What this app is
- `apps/web` is **the client Telegram Mini App**, served on the **current domain**
  (`gymbot.olykov.com`). It opens **inside Telegram, on a phone, in ~99.9% of sessions.**
- It progressively replaces `apps/admin` as the Mini App. The **admin panel relocating** to its own
  domain (or being embedded later) is **backlog — explicitly out of scope here. Do not plan for it.**
- **Mobile-first is the law.** Desktop must *work*, but is a secondary concern: on desktop the app
  is the same mobile column centered on a neutral backdrop.

## 1. Tech stack — the ALLOWED list (do not add libraries outside this without a task)
- **React 18 + TypeScript + Vite** (mirror `apps/admin`).
- **Tailwind CSS** (mirror `apps/admin`) — utility-first; design tokens via CSS variables.
- **Routing:** `react-router-dom`.
- **Server state / caching:** TanStack Query (`@tanstack/react-query`) — every API read goes through
  it (loading/error/cache states); never fetch-on-every-mount.
- **Charts:** Apache **ECharts** via `echarts-for-react` (the old site's choice; responsive only).
- **Telegram Mini App SDK:** `@twa-dev/sdk` (or official `telegram-web-app.js`) — initData, theme,
  viewport, BackButton, MainButton, haptics, safe areas.
- **API access:** the **generated TypeScript client** in
  `packages/api-contract/clients/typescript/`. No `fetch` sprawl, no `axios`, no other HTTP lib.
- **FORBIDDEN:** ❌ any direct DB access (the `site_old` anti-pattern), ❌ embedding secrets,
  ❌ heavy client-side aggregation, ❌ other UI kits (MUI/Chakra/Bootstrap/shadcn/etc.) — Tailwind +
  custom components only, ❌ generic AI fonts (Inter/Roboto/Arial/system) — see §5.

## 2. The App Shell — the consistency contract (non-negotiable)
Every page renders inside ONE shared `<AppShell>`. No page builds its own chrome.

```
┌───────────────────────────┐  ← env(safe-area-inset-top)
│  Fixed Header (always)     │   title/context + optional 1 action
├───────────────────────────┤
│                            │
│   Scrollable content       │   ← ONLY this area scrolls
│   inside ONE container     │
│   (single max-width)       │
│                            │
├───────────────────────────┤
│  Fixed Bottom Nav (always) │   3–5 tabs, native mobile pattern
└───────────────────────────┘  ← env(safe-area-inset-bottom)
```

- **Fixed header** — top, visible on every page, never scrolls away. Respects `safe-area-inset-top`.
- **Fixed bottom navigation (tab bar)** — primary nav, **always visible, never disappears**, on
  every page, on mobile AND desktop. This **replaces the old burger menu** (bottom tab bar is the
  mobile-native pattern). Respects `safe-area-inset-bottom`. v1 tabs: **Dashboard · Progress**
  (later: Distribution · Profile).
- **One content container** — a single `max-width` (≈ **480px**), centered, with **one** horizontal
  padding value and **one** vertical rhythm. EVERY page uses it. No page goes full-bleed except a
  deliberate edge-to-edge element *inside* the container (e.g. a chart).
- **Scroll model** — header + bottom-nav are `position: fixed`; the content area scrolls between
  them. Account for both heights with padding so content is never hidden under the fixed bars.
- **One divider style**, one card style, one list-row style — defined as components, reused. No
  ad-hoc borders/spacings per page.

## 3. Design tokens (CSS variables → Tailwind theme)
- **Telegram theme is the source of truth for color.** On load and on `themeChanged`, map
  `WebApp.themeParams` → CSS variables:
  `--bg`, `--text`, `--hint`, `--link`, `--button`, `--button-text`, `--secondary-bg`.
  Support **light AND dark automatically** (Telegram controls which). Provide a sane fallback palette
  for when the app is opened outside Telegram.
- **Spacing scale (only these):** 4, 8, 12, 16, 24, 32. No magic numbers.
- **Radii / shadows / typography scale:** tokens only.
- **Safe areas:** use `env(safe-area-inset-*)` for the fixed header/footer.

## 4. Telegram Mini App integration (mandatory)
- On load: `WebApp.ready()` → `WebApp.expand()`; read `initData` / `initDataUnsafe`.
- **Auth:** POST `initData` → Core API Mini App auth (`verify_telegram_webapp_auth` path) → JWT held
  in memory/session; the generated client sends it. Reuse the `apps/admin` pattern. RLS then scopes
  all data to the caller automatically (fail-closed).
- **Theme:** subscribe to `themeChanged`; apply `themeParams` to the CSS vars.
- **Viewport:** handle `viewportChanged` / `viewportStableHeight` so the fixed shell stays correct.
- **BackButton** for in-app back where natural; **haptics** on key actions.

## 5. Aesthetic mandate — the `frontend-design` plugin (100% mandatory)
- The **`frontend-design` skill MUST be invoked** (Skill tool) at the start of every UI design task
  — building a screen, a component, the token system, or restyling. It guides distinctive
  typography, cohesive color, purposeful motion, and the polish that avoids generic AI aesthetics.
- **Reconciliation (critical):** `frontend-design` pushes *bold, distinctive* craft; THIS spec
  demands *structural consistency*. Both hold at once:
  - **Distinctive in the details** — typography (a characterful display font + refined body font,
    never Inter/Roboto/system), color accents from a committed palette, micro-motion, texture/depth.
  - **Disciplined in the structure** — the fixed shell, the single container, the spacing scale, the
    bottom-nav, mobile-first. Never break the shell for a "creative" layout.
- Pick ONE coherent aesthetic direction for the whole app and apply it everywhere. No per-page drift.

## 6. Mobile-first rules
- Design at **360–430px** width first. Touch targets **≥ 44px**. No hover-only affordances.
- Primary actions reachable in the bottom third. Charts responsive to container width, legible at
  small sizes.
- Desktop = the same column centered; do not build separate desktop layouts.

## 7. Definition-of-done checklist (every page/PR)
- [ ] Renders inside the shared `<AppShell>` (fixed header + bottom nav + single container).
- [ ] Same container max-width + padding as every other page.
- [ ] Tokens only — no magic px / hard-coded colors.
- [ ] Verified at 360px width; safe-area insets respected; fixed bars never overlap content.
- [ ] Telegram light & dark themes both look correct.
- [ ] Data only via the generated client + TanStack Query (cached, no fetch storms).
- [ ] `frontend-design` skill was invoked for the design pass.
- [ ] No new library outside §1.

## 8. Pointers
- Target architecture & legacy-site lesson: `docs/ARCHITECTURE.md`.
- Phase 5 plan & tasks: `tasks/roadmap/gym-12-rebuild-website.md`, `tasks/phase-5/`.
- API contract & TS client: `packages/api-contract/`.
- Owning agent: `frontend-design-engineer` (mandated to use this spec + the `frontend-design` skill).
