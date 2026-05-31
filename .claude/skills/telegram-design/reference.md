# Telegram Design — Reference

Detailed reference for the `telegram-design` skill. Load when you need the full button
catalog, formatting escape tables, or reply-vs-inline decision guidance.

## This project's current button color map

Source of truth: `app/utils/markups.py`. Keep this table in sync when colors change.

| Button | Style | Function |
|--------|-------|----------|
| `Record training` | 🟢 SUCCESS | `generate_start_markup` |
| `Continue {exercise}` | 🟢 SUCCESS | `generate_post_set_markup` |
| `All sets completed!` | 🟢 SUCCESS | `generate_select_set_markup` |
| `Edit today's training` | 🔵 PRIMARY | `generate_edit_markup` |
| `❌ Delete Exercise` | 🔴 DANGER | `generate_exercise_markup` |
| `❌ {exercise}` (delete list) | 🔴 DANGER | `generate_delete_exercise_markup` |
| `➕ Add Muscle` | ⚪ neutral | `generate_muscle_markup` |
| `➕ Add Exercise` | ⚪ neutral | `generate_exercise_markup` |
| muscle / exercise / set / weight / reps pickers | ⚪ neutral | various |
| `Edit trainings` (WebApp) | ⚪ neutral | `generate_start_markup` |
| `Show All`, `New Exercise` | ⚪ neutral | `generate_exercise_markup` / `generate_post_set_markup` |
| `⬅️ Go back`, `⬅️ Cancel`, `Close` | ⚪ neutral | various |

## ButtonStyle values

```python
from aiogram.enums import ButtonStyle
[s.value for s in ButtonStyle]  # ['danger', 'success', 'primary']
```

Serialization check (button drops `style` if None):

```python
InlineKeyboardButton(text="X", callback_data="x", style=ButtonStyle.DANGER).model_dump(exclude_none=True)
# {'text': 'X', 'style': 'danger', 'callback_data': 'x'}
```

## Inline vs Reply keyboards

| | Inline (`InlineKeyboardMarkup`) | Reply (`ReplyKeyboardMarkup`) |
|---|---|---|
| Attached to | a specific message | the input field |
| Interaction | `callback_data` → `CallbackQuery` | sends text as a message |
| Edit in place | yes (`edit_reply_markup`) | no |
| Supports `style` colors | yes | yes |
| Supports WebApp | yes (`web_app`) | yes (`web_app`) |
| This project uses | **only this** | not used |

Default to **inline** for navigation/state machines (this bot's whole flow). Use reply
keyboards only for persistent quick-reply menus under the input field.

## Custom emoji — how to source an ID (only if owner has Premium)

1. Have the owner send the bot a message containing the desired premium custom emoji.
2. In a temporary handler, read `message.entities`; for `type == "custom_emoji"` read
   `entity.custom_emoji_id`. Or parse HTML `<tg-emoji emoji-id="...">` with regex
   `emoji-id="(\d+)"`.
3. Store IDs in env/config; pass via `icon_custom_emoji_id=...`. One static (non-animated)
   emoji per button.
4. Graceful fallback: if the ID is empty, omit `icon_custom_emoji_id` so the Unicode emoji
   in `text` shows instead.

## Message formatting

### Parse mode (set once)

```python
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
bot = Bot(token=..., default=DefaultBotProperties(parse_mode=ParseMode.HTML))
```

### HTML (preferred)

Supported: `<b> <i> <u> <s> <a href> <code> <pre> <blockquote> <tg-spoiler>`.
Escape only `<`, `>`, `&` in dynamic text.

### MarkdownV2 (avoid unless needed)

Must escape these characters anywhere they appear literally:
``_ * [ ] ( ) ~ ` > # + - = | { } . !``

### Common pitfalls

- Telegram limits a message to 4096 chars — split long outputs.
- A button row holds up to 8 buttons; a keyboard up to 100 buttons total.
- `callback_data` is capped at 64 bytes — encode IDs, not labels.

## Layout heuristics

- Choose row width from label length: 1 wide label per row; 6–8 short numeric labels per row.
- Keep destructive and confirm actions on separate rows to avoid mis-taps.
- Always provide a back/cancel path on every non-root keyboard.
- Place the primary action where the thumb lands first (top of the action group).
