"""seed operator-approved Russian exercise aliases (GYM-92)

Revision ID: 0009_seed_ru_aliases
Revises: 0008_apply_catalog_curation
Create Date: 2026-06-10 04:00:00.000000+00:00

GYM-92 — seed one Russian alias per curated canonical exercise (Channel B,
ADR 0001/0003) so RU search resolves ("Жим штанги лёжа" -> Barbell Bench Press).

WHAT THIS DOES
--------------
Inserts 98 rows into ``exercise_alias`` — one Russian alias for each of the 98
``action==KEEP`` canonical exercises that survive the 0008 curation. The values
are GENERATED from the operator-reviewed seed
``packages/db/seeds/exercise_aliases_ru.tsv`` and EMBEDDED below (the TSV is NOT
read at runtime). Each row:

    INSERT INTO exercise_alias (canonical_id, alias_name, lang)
    VALUES (:cid, :ru, 'ru')
    ON CONFLICT (canonical_id, name_key) DO NOTHING

- ``is_global`` defaults TRUE and ``created_by`` is NULL (table defaults): these
  are GLOBAL, admin-curated catalog aliases, world-readable under catalog RLS.
- ``name_key`` is the table's GENERATED column (``app_name_key(alias_name)``) —
  never set here; it is what the search alias tier matches on.
- ``lang='ru'`` so the search endpoint's lang filter (``a.lang = :lang``) returns
  these hits for Russian queries.

CANONICAL_ID INTEGRITY
----------------------
Every ``canonical_id`` below is one of the 98 KEEP ids from 0008 (verified 1:1
against the worksheet's KEEP set): KEEP rows stay public with their id unchanged,
so the FK ``canonical_id REFERENCES exercises(id)`` always resolves on the real
catalog post-0008. DEMOTE / MERGE-source / junk (337) ids are deliberately NOT
here.

Each INSERT is guarded by ``WHERE EXISTS (SELECT 1 FROM exercises ...)`` so it is
a clean no-op when the canonical row is absent (e.g. a fresh container or a test
DB bootstrapped from ``init.sql`` with no catalog seeded). This keeps the
migration runnable on ANY DB — it never raises a dangling-FK error — while on
prod (where all 98 KEEP rows exist) every row is seeded.

NAME ESCAPING
-------------
All Russian alias text is passed as a BOUND PARAMETER (``:ru``) — never
string-concatenated — so Cyrillic, the «» guillemets, the ``°`` sign and any
punctuation are handled safely by the driver.

IDEMPOTENCY
-----------
``ON CONFLICT (canonical_id, name_key) DO NOTHING`` makes each insert a no-op on
re-run (the unique key is (canonical_id, generated name_key)). Re-running
``upgrade()`` inserts nothing the second time.

BACKWARD COMPATIBILITY
----------------------
Additive, data-only. New global dictionary rows; no schema change, no existing
row touched. English-name search is unaffected; RU search gains 98 resolvable
aliases.

DOWNGRADE
---------
Clean and reversible (unlike 0008): ``DELETE FROM exercise_alias WHERE lang='ru'``
removes exactly the rows this migration seeds (all ru-tagged catalog aliases).
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "0009_seed_ru_aliases"
down_revision: Union[str, Sequence[str], None] = "0008_apply_catalog_curation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Generated from packages/db/seeds/exercise_aliases_ru.tsv (operator-approved,
# final). Tuples are (canonical_id, russian_alias). canonical_id == exercises.id
# == the alias's canonical_id; every id is a 0008 KEEP row. The trailing comment
# is the English canonical name, for reviewer reference only.
# ---------------------------------------------------------------------------
RU_ALIASES: tuple[tuple[int, str], ...] = (
    (71, "Скручивания в тренажёре"),  # Ab Crunch Machine
    (77, "Подъём корпуса на наклонной скамье"),  # Incline Sit-Up
    (38, "Подтягивания в гравитроне"),  # Assisted Chin-Up
    (345, "Тяга штанги в наклоне"),  # Bent-Over Barbell Row
    (58, "Шраги со штангой"),  # Barbell Shrug
    (3, "Тяга верхнего блока узким хватом"),  # Close-Grip Lat Pulldown
    (34, "Тяга гантели одной рукой в наклоне"),  # One-Arm Dumbbell Row
    (76, "Тяга гантелей лёжа на наклонной скамье"),  # Chest-Supported Dumbbell Row
    (348, "Шраги с гантелями"),  # Dumbbell Shrug
    (47, "Вертикальная тяга к груди в Hammer"),  # Iso-Lateral Front Lat Pulldown
    (53, "Пуловер в тренажёре"),  # Machine Pullover
    (352, "Гиперэкстензия"),  # Back Extension
    (5, "Нижняя горизонтальная тяга в Hammer"),  # Iso-Lateral Low Row
    (35, "Горизонтальная тяга в Hammer"),  # Iso-Lateral Row
    (4, "Тяга верхнего блока"),  # Lat Pulldown
    (240, "Тяга верхнего блока нейтральным хватом"),  # Neutral-Grip Lat Pulldown
    (33, "Тяга верхнего блока параллельным хватом"),  # Parallel-Grip Lat Pulldown
    (57, "Пуловер на верхнем блоке"),  # Cable Pullover
    (355, "Подтягивания"),  # Pull-Up
    (147, "Горизонтальная тяга в тренажёре"),  # Machine Row
    (6, "Тяга горизонтального блока узким хватом"),  # Seated Cable Row (Close Grip)
    (37, "Тяга горизонтального блока нейтральным хватом"),  # Seated Cable Row (Neutral Grip)
    (46, "Тяга горизонтального блока широким хватом"),  # Seated Cable Row (Wide Grip)
    (369, "Т-образная тяга"),  # T-Bar Row
    (17, "Тяга верхнего блока широким хватом"),  # Wide-Grip Lat Pulldown
    (23, "Подъём на бицепс с EZ-грифом"),  # EZ-Bar Curl
    (32, "Подъём штанги на бицепс"),  # Barbell Curl
    (75, "Сгибание на бицепс на блоке с канатом"),  # Cable Curl (Rope)
    (371, "Подъём гантелей на бицепс без супинации"),  # Dumbbell Curl (No Supination)
    (11, "Подъём гантелей на бицепс с супинацией"),  # Dumbbell Curl (Supinated)
    (363, "Молотки с гантелями"),  # Dumbbell Hammer Curl
    (10, "Молотки с гантелями поперёк корпуса"),  # Cross-Body Hammer Curl
    (72, "Сгибание на бицепс на скамье Скотта с гантелью"),  # Dumbbell Preacher Curl
    (335, "Сгибание на бицепс в тренажёре Скотта"),  # Machine Preacher Curl
    (127, "Подъём штанги на бицепс обратным хватом"),  # Reverse Barbell Curl
    (7, "Жим штанги лёжа"),  # Barbell Bench Press
    (20, "Жим штанги лёжа на наклонной скамье"),  # Incline Barbell Bench Press
    (8, "Жим гантелей лёжа на наклонной скамье"),  # Incline Dumbbell Bench Press
    (31, "Жим в Смите на наклонной скамье"),  # Incline Smith Machine Press
    (54, "Жим от груди в тренажёре"),  # Cable Chest Press (Machine)
    (30, "Жим гантелей лёжа"),  # Dumbbell Bench Press
    (44, "Жим от груди в тренажёре вниз"),  # Decline Chest Press (Machine)
    (43, "Жим от груди в тренажёре"),  # Flat Chest Press (Machine)
    (21, "Жим от груди в тренажёре под наклоном"),  # Incline Chest Press (Machine)
    (9, "Сведение рук в кроссовере снизу"),  # Low Cable Crossover
    (22, "Сведение рук в тренажёре «бабочка»"),  # Pec Deck (Machine Fly)
    (36, "Сведение рук в кроссовере сверху"),  # High Cable Crossover
    (61, "Разгибание запястий со штангой"),  # Barbell Reverse Wrist Curl
    (16, "Сгибание запястий со штангой"),  # Barbell Wrist Curl
    (340, "Разгибание запястий с гантелями"),  # Dumbbell Reverse Wrist Curl
    (285, "Сгибание запястий с гантелями"),  # Dumbbell Wrist Curl
    (373, "Болгарские приседания"),  # Bulgarian Split Squat
    (29, "Подъём на носки в тренажёре"),  # Calf Raise (Machine)
    (56, "Подъём на носки стоя"),  # Standing Calf Raise
    (52, "Отведение бёдер в тренажёре"),  # Hip Abduction (Machine)
    (51, "Сведение бёдер в тренажёре"),  # Hip Adduction (Machine)
    (358, "Ягодичный мостик со штангой"),  # Barbell Hip Thrust
    (357, "Ягодичный мостик в тренажёре"),  # Machine Hip Thrust
    (50, "Наклонная гиперэкстензия (45°)"),  # Hyperextension (45-Degree)
    (28, "Сгибание ног лёжа"),  # Lying Leg Curl
    (69, "Сгибание ног сидя"),  # Seated Leg Curl
    (365, "Сгибание ноги стоя"),  # Standing Leg Curl
    (25, "Разгибание ног в тренажёре"),  # Leg Extension
    (367, "Жим ногами на блоке"),  # Cable Leg Press
    (64, "Жим ногами"),  # Leg Press
    (73, "Горизонтальный жим ногами сидя"),  # Seated Leg Press
    (342, "Выпады в Смите"),  # Smith Machine Lunge
    (49, "Румынская тяга со штангой"),  # Romanian Deadlift (Barbell)
    (62, "Румынская тяга с гантелями"),  # Romanian Deadlift (Dumbbell)
    (370, "Румынская тяга в Смите"),  # Romanian Deadlift (Smith)
    (376, "Махи ногой назад на блоке"),  # Cable Glute Kickback
    (375, "Махи ногой назад в тренажёре"),  # Glute Kickback (Machine)
    (63, "Гакк-приседания"),  # Hack Squat
    (346, "Приседания с поясом в тренажёре"),  # Belt Squat (Machine)
    (341, "Приседания в Смите"),  # Smith Machine Squat
    (374, "Становая тяга сумо с гантелью"),  # Dumbbell Sumo Deadlift
    (372, "Становая тяга сумо в Смите"),  # Smith Machine Sumo Deadlift
    (70, "Махи в стороны на блоке"),  # Cable Lateral Raise
    (66, "Разведение на задние дельты на блоке"),  # Cable Rear Delt Fly
    (14, "Махи гантелями в стороны"),  # Dumbbell Lateral Raise
    (24, "Разведение гантелей в наклоне на задние дельты"),  # Bent-Over Dumbbell Rear Delt Fly
    (13, "Жим гантелей сидя"),  # Dumbbell Shoulder Press
    (65, "Тяга к лицу"),  # Face Pull
    (68, "Махи в стороны в тренажёре"),  # Lateral Raise (Machine)
    (42, "Обратная «бабочка» на задние дельты"),  # Reverse Pec Deck (Rear Delt Fly)
    (41, "Жим над головой в тренажёре"),  # Shoulder Press (Machine)
    (12, "Жим над головой в Смите"),  # Smith Machine Shoulder Press
    (15, "Протяжка"),  # Upright Row
    (74, "Жим лёжа узким хватом"),  # Close-Grip Bench Press
    (18, "Французский жим"),  # Skull Crusher (Lying Triceps Extension)
    (359, "JM-жим в Смите"),  # Smith Machine JM Press
    (336, "Отжимания на трицепс в тренажёре"),  # Triceps Dip Machine
    (19, "Французский жим стоя на блоке"),  # Overhead Cable Triceps Extension
    (354, "Французский жим стоя с гантелью"),  # Overhead Dumbbell Triceps Extension
    (59, "Разгибание на трицепс на блоке одной рукой"),  # Single-Arm Triceps Pushdown
    (1, "Разгибание на трицепс на блоке с канатом"),  # Rope Triceps Pushdown
    (2, "Разгибание на трицепс на блоке с прямой рукоятью"),  # Straight-Bar Triceps Pushdown
    (39, "Разгибание на трицепс на блоке с V-образной рукоятью"),  # V-Bar Triceps Pushdown
)


def upgrade() -> None:
    """Seed the 98 Russian catalog aliases (idempotent via ON CONFLICT).

    Each Russian string is bound (``:ru``) — never concatenated. ``name_key`` is
    the table's generated column; ``is_global``/``created_by`` use the table
    defaults (global, admin-curated). Re-runnable: ON CONFLICT DO NOTHING. The
    ``WHERE EXISTS`` guard makes a row a no-op when its canonical exercise is
    absent, so the migration never raises a dangling-FK error on a fresh DB.
    """
    conn = op.get_bind()
    # WHERE EXISTS guards the FK: a no-op when the canonical row is absent (fresh
    # DB / unseeded test catalog), real insert when it exists (prod, post-0008).
    stmt = text(
        "INSERT INTO exercise_alias (canonical_id, alias_name, lang) "
        "SELECT :cid, :ru, 'ru' "
        "WHERE EXISTS (SELECT 1 FROM exercises WHERE id = :cid) "
        "ON CONFLICT (canonical_id, name_key) DO NOTHING"
    )
    for canonical_id, ru in RU_ALIASES:
        conn.execute(stmt, {"cid": canonical_id, "ru": ru})


def downgrade() -> None:
    """Remove every ru-tagged catalog alias seeded by upgrade(). Reversible."""
    op.get_bind().execute(text("DELETE FROM exercise_alias WHERE lang = 'ru'"))
