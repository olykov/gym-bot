---
name: telegram-design
description: Design native Telegram bot UI/UX with aiogram 3.28+ — inline keyboard layouts, button colors (ButtonStyle primary/success/danger, Bot API 9.4), custom emoji on buttons, WebApp buttons, callback_data conventions, and message formatting. Use when building, reviewing, or styling Telegram bot keyboards and messages, when the user mentions buttons, InlineKeyboardMarkup, button colors/styles, keyboard layout, reply_markup, or "telegram design".
---

# Telegram Bot Native Design

Guidance for designing the *native* Telegram UI of a bot (not web frontends): inline
keyboards, button colors, layout ergonomics, message formatting. Targets **aiogram 3.28+**
and **Bot API 9.4+** (button `style` and `icon_custom_emoji_id`).

This project (`tg-app-gym-bot`) builds all keyboards in `app/utils/markups.py` as factory
functions returning `InlineKeyboardMarkup`. Follow those patterns; handlers in
`app/modules/handlers.py` consume them via `reply_markup=`.

## Core rules

1. **Color = signal, not decoration.** Only style *action* and *terminal* buttons. Keep
   data-selection buttons (lists, pickers) and navigation (back/cancel/close) neutral —
   otherwise the keyboard becomes a rainbow and the color stops meaning anything.
2. **Always design graceful degradation.** Old Telegram clients ignore `style` and
   `icon_custom_emoji_id` and render a normal button. Never make behavior depend on color.
3. **One screen, at most one primary action.** The main call-to-action gets the accent;
   everything else is neutral or semantic.
4. **Don't touch handlers for cosmetics.** Text, `callback_data`, and row order must stay
   identical when restyling, so handler logic and FSM transitions are unaffected.

## Button colors (ButtonStyle)

Bot API 9.4 added `style` to `InlineKeyboardButton` / `KeyboardButton`. In aiogram:

```python
from aiogram.enums import ButtonStyle  # values: PRIMARY, SUCCESS, DANGER
from aiogram.types import InlineKeyboardButton

InlineKeyboardButton(text="Delete exercise", callback_data="del", style=ButtonStyle.DANGER)
```

Semantic mapping (this project's convention):

| Style | Color | Use for |
|-------|-------|---------|
| `SUCCESS` | 🟢 green | positive / additive / completion / main "go" action (record, continue, done) |
| `PRIMARY` | 🔵 blue | secondary highlighted action (edit) |
| `DANGER` | 🔴 red | destructive (delete) |
| *(omit)* | ⚪ neutral | data selection, navigation (back/cancel/close), WebApp launch |

No `style` argument → neutral/transparent button. To "uncolor" a button, remove the
`style=` kwarg entirely.

## Custom emoji on buttons — usually NOT available

`icon_custom_emoji_id` shows a premium custom emoji on a button. **Two hard requirements:**

1. The **bot owner must have Telegram Premium** (or a Fragment username), else Telegram
   ignores the field.
2. You need a **real `custom_emoji_id`** (numeric ID of a specific premium emoji), sourced
   from a message or sticker set — it cannot be invented.

If the owner has no Premium, **skip custom emoji** and rely on plain Unicode emoji in the
button `text` (e.g. `➕`, `❌`, `⬅️`). Those are not custom emoji and always work.

## Keyboard layout & ergonomics

- **Row width by content type** (this project's tuning, see `markups.py`): muscles 3/row,
  exercises 1/row (long names), sets 6/row, weights 7/row, reps 8/row. Short labels → wider
  rows; long labels → 1/row.
- **Navigation goes last**, on its own bottom row: `⬅️ Go back`, `⬅️ Cancel`, `Close`.
- **Action buttons** (add/delete) sit just above navigation, grouped on one row.
- **Build rows incrementally** with a `btn_row`/`inline_keyboard` accumulator and flush when
  `len(btn_row) == N`; append the leftover `btn_row` after the loop.

## callback_data conventions

- Keep `callback_data` ≤ 64 bytes (Telegram hard limit).
- Use stable prefixes for routing: `mus_`, `ex_`, `del_ex_`, `continue_ex||..`. Match these
  in handlers with `F.data.startswith(...)`.
- Never put display text in `callback_data`; keep it machine-stable.

## Message formatting

- Set parse mode once globally: `Bot(token=..., default=DefaultBotProperties(parse_mode=ParseMode.HTML))`.
- Prefer **HTML** parse mode over MarkdownV2 (HTML needs less escaping; MarkdownV2 requires
  escaping `_ * [ ] ( ) ~ \` > # + - = | { } . !`).
- WebApp buttons: `InlineKeyboardButton(text="Open", web_app=WebAppInfo(url=https_url))` —
  URL must be HTTPS.

## Workflow for a design/restyle request

1. Read `app/utils/markups.py`; identify the affected factory function(s).
2. Propose a concise **before/after color-map table** (button → old → new) and get approval
   per this project's `CLAUDE.md` feature workflow.
3. Edit only `markups.py`. Add/remove `style=` or `web_app=`; never change `text` or
   `callback_data` for a pure restyle.
4. Verify: `python3 -m py_compile app/utils/markups.py`, and confirm the
   `from aiogram.enums import ButtonStyle` import exists.
5. Remind the user that colors require aiogram ≥ 3.28 and appear only after redeploy /
   image rebuild; already-rendered keyboards in old messages are not recolored.

For the full button catalog, parse-mode escaping tables, and reply-vs-inline guidance, see
[reference.md](reference.md).
