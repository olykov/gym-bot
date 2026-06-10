"""apply catalog curation: renames + demotes + merges (GYM-110)

Revision ID: 0008_apply_catalog_curation
Revises: 0007_pg_trgm
Create Date: 2026-06-10 03:00:00.000000+00:00

GYM-110 — apply the operator-reviewed canonical catalog curation (ADR 0004).

WHAT THIS DOES
--------------
A single, tested DATA migration that mutates the real ``exercises`` catalog per
the operator-reviewed worksheet ``packages/db/seeds/canonical_curation.tsv``
(v3.1) and the free-exercise-db cross-map ``packages/db/seeds/fxdb_crossmap.tsv``
(GYM-111). The worksheet is the source of truth; the per-id SQL below is
GENERATED from it and the values are EMBEDDED (the TSV is NOT read at runtime).

Three operations (ADR 0004), plus one junk-row delete:

1. KEEP (98 rows) — stays public canonical, renamed to a standard name:
       UPDATE exercises SET name = <canonical_name> WHERE id = <id>
   The id is unchanged, so all training history stays attached.

2. DEMOTE (18 rows) — moves to the operator's personal list:
       UPDATE exercises SET name = <canonical_name>, is_global = false,
              created_by = 2107709598 WHERE id = <id>
   Operator olykov = users.id 2107709598 (telegram id). Id unchanged → history
   intact; RLS then shows the row only to the operator.

3. MERGE (5 rows, source -> target) — duplicate folded into its canonical:
       UPDATE training              SET exercise_id = <target> WHERE exercise_id = <src>;
       UPDATE user_hidden_exercises SET exercise_id = <target> WHERE exercise_id = <src>;  -- defensive
       UPDATE user_exercise_override SET exercise_id = <target> WHERE exercise_id = <src>;  -- defensive
       DELETE FROM exercises WHERE id = <src>;
   Merge map (source -> target):
       26  -> 127   (Reverse Barbell Curl)            59 sets
       347 -> 54    (Cable Chest Press (Machine))      3 sets
       351 -> 362   (Side Pressure (Dumbbell))         0 sets
       338 -> 30    (Dumbbell Bench Press)             4 sets
       40  -> 373   (Bulgarian Split Squat)            3 sets

4. JUNK DELETE — id 337 ("Bench press incline-delete1"), 0 training sets, NOT in
   the worksheet:
       DELETE FROM exercises WHERE id = 337

ORDER (load-bearing)
--------------------
KEEP/DEMOTE renames+ownership FIRST, then MERGEs (repoint + delete source), then
the 337 delete. Doing renames before merges guarantees every MERGE TARGET that
is itself renamed ends with its canonical name BEFORE any source folds into it
(e.g. 338 merges into 30, which this migration renames to "Dumbbell Bench
Press"; 40 merges into 373 -> "Bulgarian Split Squat"). The repoint/delete then
preserves all of the source's training history on the (correctly named) target.

NAME ESCAPING
-------------
All canonical names are passed as bound parameters (``%(p)s`` / SQLAlchemy
``:param``) — never string-concatenated — so embedded parentheses (34 names)
and any quotes are handled safely by the driver. No name in v3.1 contains an
apostrophe; parentheses need no escaping inside a bound literal.

NAME_KEY UNIQUENESS
-------------------
``exercises`` has two partial unique indexes on the GENERATED ``name_key``:
``(name_key, muscle) WHERE created_by IS NULL`` (global) and
``(name_key, muscle, created_by) WHERE created_by IS NOT NULL`` (user). Pre-flight
on prod confirmed the worksheet's canonical names introduce NO collisions in
either scope (KEEP keeps rows global; DEMOTE moves rows into the operator's
personal scope without clashing with the operator's existing personal rows). The
GYM-110 integration test asserts the migration runs without a unique violation.

IDEMPOTENCY
-----------
Largely re-runnable: UPDATE-by-id is naturally idempotent; "repoint WHERE
exercise_id = <src>" and "DELETE WHERE id = <src>" / id 337 are no-ops on a
second run (the source/junk rows are already gone, no training references them).

BACKWARD COMPATIBILITY
----------------------
Training history is preserved for every exercise: id-stable for KEEP/DEMOTE,
repointed (never dropped) for MERGE. No schema change — data only.

DOWNGRADE
---------
This is a DELIBERATE, one-way curation. Renames discard the old display names and
MERGE deletes source rows after folding their history into the target — neither
is cleanly reversible (the pre-curation names and the source/target split are not
recorded). ``downgrade()`` therefore raises ``NotImplementedError``. To revert,
restore from a backup taken before the upgrade.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "0008_apply_catalog_curation"
down_revision: Union[str, Sequence[str], None] = "0007_pg_trgm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Operator olykov (telegram id == users.id). FK target for DEMOTE.created_by.
OPERATOR_USER_ID = 2107709598

# ---------------------------------------------------------------------------
# Generated from packages/db/seeds/canonical_curation.tsv (v3.1).
# Tuples are (exercise_id, canonical_name). Order within each list mirrors the
# worksheet; order between lists does NOT matter for KEEP/DEMOTE (UPDATE-by-id).
# ---------------------------------------------------------------------------

# KEEP — stays public; rename only. 98 rows.
KEEP: tuple[tuple[int, str], ...] = (
    (71, "Ab Crunch Machine"),
    (77, "Incline Sit-Up"),
    (38, "Assisted Chin-Up"),
    (345, "Bent-Over Barbell Row"),
    (58, "Barbell Shrug"),
    (3, "Close-Grip Lat Pulldown"),
    (34, "One-Arm Dumbbell Row"),
    (76, "Chest-Supported Dumbbell Row"),
    (348, "Dumbbell Shrug"),
    (47, "Iso-Lateral Front Lat Pulldown"),
    (53, "Machine Pullover"),
    (352, "Back Extension"),
    (5, "Iso-Lateral Low Row"),
    (35, "Iso-Lateral Row"),
    (4, "Lat Pulldown"),
    (240, "Neutral-Grip Lat Pulldown"),
    (33, "Parallel-Grip Lat Pulldown"),
    (57, "Cable Pullover"),
    (355, "Pull-Up"),
    (147, "Machine Row"),
    (6, "Seated Cable Row (Close Grip)"),
    (37, "Seated Cable Row (Neutral Grip)"),
    (46, "Seated Cable Row (Wide Grip)"),
    (369, "T-Bar Row"),
    (17, "Wide-Grip Lat Pulldown"),
    (23, "EZ-Bar Curl"),
    (32, "Barbell Curl"),
    (75, "Cable Curl (Rope)"),
    (371, "Dumbbell Curl (No Supination)"),
    (11, "Dumbbell Curl (Supinated)"),
    (363, "Dumbbell Hammer Curl"),
    (10, "Cross-Body Hammer Curl"),
    (72, "Dumbbell Preacher Curl"),
    (335, "Machine Preacher Curl"),
    (127, "Reverse Barbell Curl"),
    (7, "Barbell Bench Press"),
    (20, "Incline Barbell Bench Press"),
    (8, "Incline Dumbbell Bench Press"),
    (31, "Incline Smith Machine Press"),
    (54, "Cable Chest Press (Machine)"),
    (30, "Dumbbell Bench Press"),
    (44, "Decline Chest Press (Machine)"),
    (43, "Flat Chest Press (Machine)"),
    (21, "Incline Chest Press (Machine)"),
    (9, "Low Cable Crossover"),
    (22, "Pec Deck (Machine Fly)"),
    (36, "High Cable Crossover"),
    (61, "Barbell Reverse Wrist Curl"),
    (16, "Barbell Wrist Curl"),
    (340, "Dumbbell Reverse Wrist Curl"),
    (285, "Dumbbell Wrist Curl"),
    (373, "Bulgarian Split Squat"),
    (29, "Calf Raise (Machine)"),
    (56, "Standing Calf Raise"),
    (52, "Hip Abduction (Machine)"),
    (51, "Hip Adduction (Machine)"),
    (358, "Barbell Hip Thrust"),
    (357, "Machine Hip Thrust"),
    (50, "Hyperextension (45-Degree)"),
    (28, "Lying Leg Curl"),
    (69, "Seated Leg Curl"),
    (365, "Standing Leg Curl"),
    (25, "Leg Extension"),
    (367, "Cable Leg Press"),
    (64, "Leg Press"),
    (73, "Seated Leg Press"),
    (342, "Smith Machine Lunge"),
    (49, "Romanian Deadlift (Barbell)"),
    (62, "Romanian Deadlift (Dumbbell)"),
    (370, "Romanian Deadlift (Smith)"),
    (376, "Cable Glute Kickback"),
    (375, "Glute Kickback (Machine)"),
    (63, "Hack Squat"),
    (346, "Belt Squat (Machine)"),
    (341, "Smith Machine Squat"),
    (374, "Dumbbell Sumo Deadlift"),
    (372, "Smith Machine Sumo Deadlift"),
    (70, "Cable Lateral Raise"),
    (66, "Cable Rear Delt Fly"),
    (14, "Dumbbell Lateral Raise"),
    (24, "Bent-Over Dumbbell Rear Delt Fly"),
    (13, "Dumbbell Shoulder Press"),
    (65, "Face Pull"),
    (68, "Lateral Raise (Machine)"),
    (42, "Reverse Pec Deck (Rear Delt Fly)"),
    (41, "Shoulder Press (Machine)"),
    (12, "Smith Machine Shoulder Press"),
    (15, "Upright Row"),
    (74, "Close-Grip Bench Press"),
    (18, "Skull Crusher (Lying Triceps Extension)"),
    (359, "Smith Machine JM Press"),
    (336, "Triceps Dip Machine"),
    (19, "Overhead Cable Triceps Extension"),
    (354, "Overhead Dumbbell Triceps Extension"),
    (59, "Single-Arm Triceps Pushdown"),
    (1, "Rope Triceps Pushdown"),
    (2, "Straight-Bar Triceps Pushdown"),
    (39, "V-Bar Triceps Pushdown"),
)

# DEMOTE — move to operator's personal list (is_global=false, created_by=operator)
# + rename. 18 rows.
DEMOTE: tuple[tuple[int, str], ...] = (
    (353, "Iso-Lateral Low Row (Traps)"),
    (67, "Half-Kneeling Single-Arm Cable Row"),
    (356, "Seated Single-Arm Cable Row"),
    (366, "T-Bar Row (Upper Back)"),
    (27, "Standing Dumbbell Curl"),
    (55, "Single-Arm Cable Drag Curl"),
    (362, "Side Pressure (Dumbbell)"),
    (290, "Brachioradialis Curl"),
    (60, "Cable Wrist Curl (Behind Back)"),
    (360, "Cable Wrist Curl (Over Bench)"),
    (344, "Cable Reverse Wrist Curl"),
    (361, "Cable Wrist Curl (Thick Grip)"),
    (350, "Pronation (Plate)"),
    (349, "Pronation (Cable)"),
    (343, "Side Pressure (Cable)"),
    (48, "Bulgarian Split Squat (Barbell)"),
    (339, "Cable Rope Lateral Raise"),
    (368, "Single-Arm Reverse Triceps Extension"),
)

# MERGE — (source_id, target_id). Repoint source's references to target, then
# delete source. 5 rows.
MERGE: tuple[tuple[int, int], ...] = (
    (26, 127),
    (347, 54),
    (351, 362),
    (338, 30),
    (40, 373),
)

# Junk row not in the worksheet: 0 training sets, explicit delete.
JUNK_DELETE_IDS: tuple[int, ...] = (337,)


def upgrade() -> None:
    """Apply renames, demotes, merges, and the junk delete in the safe order.

    Order is load-bearing: KEEP/DEMOTE first (so merge targets are renamed
    before any source folds into them), then MERGE (repoint + delete source),
    then the junk-row delete. All names are passed as bound parameters — never
    concatenated — so parentheses/quotes are escaped by the driver.
    """
    conn = op.get_bind()

    # 1. KEEP — rename only; row stays public (id stable -> history intact).
    for ex_id, name in KEEP:
        conn.execute(
            text("UPDATE exercises SET name = :name WHERE id = :id"),
            {"name": name, "id": ex_id},
        )

    # 2. DEMOTE — rename + flip to operator's personal list.
    for ex_id, name in DEMOTE:
        conn.execute(
            text(
                "UPDATE exercises "
                "SET name = :name, is_global = false, created_by = :op "
                "WHERE id = :id"
            ),
            {"name": name, "op": OPERATOR_USER_ID, "id": ex_id},
        )

    # 3. MERGE — repoint training (+ hidden/override defensively) to target,
    #    then delete the source. Targets are already correctly renamed by now.
    for src_id, target_id in MERGE:
        conn.execute(
            text("UPDATE training SET exercise_id = :tgt WHERE exercise_id = :src"),
            {"tgt": target_id, "src": src_id},
        )
        # Defensive: these tables had no rows for the merge sources at pre-flight,
        # but repoint anyway in case data appeared before the migration runs.
        conn.execute(
            text(
                "UPDATE user_hidden_exercises SET exercise_id = :tgt "
                "WHERE exercise_id = :src "
                # Avoid violating the (user_id, exercise_id) PK if the user already
                # hides the target: only repoint rows that would not collide.
                "AND NOT EXISTS ("
                "  SELECT 1 FROM user_hidden_exercises h2 "
                "  WHERE h2.user_id = user_hidden_exercises.user_id "
                "    AND h2.exercise_id = :tgt"
                ")"
            ),
            {"tgt": target_id, "src": src_id},
        )
        # Any remaining (collision) source-hidden rows are now redundant; drop them.
        conn.execute(
            text("DELETE FROM user_hidden_exercises WHERE exercise_id = :src"),
            {"src": src_id},
        )
        conn.execute(
            text(
                "UPDATE user_exercise_override SET exercise_id = :tgt "
                "WHERE exercise_id = :src "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM user_exercise_override o2 "
                "  WHERE o2.user_id = user_exercise_override.user_id "
                "    AND o2.exercise_id = :tgt"
                ")"
            ),
            {"tgt": target_id, "src": src_id},
        )
        conn.execute(
            text("DELETE FROM user_exercise_override WHERE exercise_id = :src"),
            {"src": src_id},
        )
        # Any custom exercise that pointed at the deleted source's canonical link
        # would be left dangling; ON DELETE SET NULL on exercises.canonical_id
        # already handles that when the source row is deleted below.
        conn.execute(
            text("DELETE FROM exercises WHERE id = :src"),
            {"src": src_id},
        )

    # 4. Junk delete — id 337, 0 training sets, not in the worksheet.
    for junk_id in JUNK_DELETE_IDS:
        conn.execute(
            text("DELETE FROM exercises WHERE id = :id"),
            {"id": junk_id},
        )


def downgrade() -> None:
    """One-way curation; not cleanly reversible. See module docstring.

    Renames discard the old display names and MERGE deletes source rows after
    folding their history into the target. Neither the pre-curation names nor the
    source/target split is recorded, so there is no faithful inverse. To revert,
    restore from a backup taken before this upgrade.
    """
    raise NotImplementedError(
        "0008_apply_catalog_curation is a deliberate one-way data curation "
        "(renames + merges + deletes). It has no clean inverse; restore from a "
        "pre-upgrade backup to revert."
    )
