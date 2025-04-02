class Exercise:
    name: str
    reps: float
    weight: float

reps = [
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", 
    "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"
]

weights = [
    "5", "6", "7.5", "8", "9", "10", "12", "12.5", "14", "15", "15.5", "16", "17", "17.5", "18",
    "20", "22", "22.5", "24", "25", "26", "27", "28", "30", "32", "32.5","34", "35", "36", "38", "40",
    "42", "42.5", "45", "47.5", "50", "52.5", "55", "57.5", "60", "65", "70",
    "75", "80", "85", "90", "95", "100", "105", "110", "115", "120", "125", "130", "135", "140"
]

sets = [
    {
        "name": "Set 1",
        "id": "1"
    },
    {
        "name": "Set 2",
        "id": "2"
    },
    {
        "name": "Set 3",
        "id": "3"
    },
    {
        "name": "Set 4",
        "id": "4"
    },
    {
        "name": "Set 5",
        "id": "5"
    },
    {
        "name": "Set 6",
        "id": "6"
    }
]

exercise_types = [
    {
        "name": "Chest",
        "exercises": [
            "Bench press",
            "Bench press incline",
            "Dumbbell incline bench press",
            "Lower chest cable crossover",
            "Upper chest cable crossover",
            "Hammer incline",
            "Hammer flat",
            "Hammer decline",
            "Peck Deck",
            "Chest press machine",
            "Dumbbell press flat bench",
            "Incline smith"
        ]
    },
    {
        "name": "Biceps",
        "exercises": [
            "EZ-bar bicep curl",
            "Straight-bar biceps curl",
            "Cross body hammer curl",
            "Biceps supinated",
            "Standing single-arm cable biceps curl",
            "One-arm dumbbell curl over bench",
            "Standing rope biceps curl",
            "African curls",
            "Biceps curl machine",
            "Dumbbell brachialis curls",
            "Barbell reverse curl",
            "Dumbbell side pressure"
        ]
    },
    {
        "name": "Back",
        "exercises": [
            "Wide-grip lat pulldown",
            "Close-grip lat pulldown",
            "Power-grip pulldown",
            "Neutral-grip pulldown",
            "Lat pulldown machine",
            "Seated close-grip row",
            "Seated wide grip row",
            "Seated neutral grip row",
            "Dumbbell row",
            "Incline bench dumbbell row",
            "Row machine",
            "Pullover",
            "Hammer pullover",
            "Hammer front pulldown",
            "Iso lateral row",
            "Iso lateral low row",
            "Lats cable",
            "Barbell shrugs",
            "Dumbbell shrugs",
            "Assist chin"
        ]
    },
    {
        "name": "Triceps",
        "exercises": [
            "French press",
            "Triceps pushdown v-bar",
            "Triceps pushdown rope",
            "Triceps pushdown rope straight bar",
            "Close-grip bench press",
            "Cable overhead shoulder extension",
            "Single-arm cable triceps pushdown"
        ]
    },
    {
        "name": "Shoulders",
        "exercises": [
            "Smith barbell shoulders press",
            "Dumbbell shoulders press",
            "Shoulder press machine",
            "Dumbbell lateral raises",
            "Cable lateral raises",
            "Cable rope lateral delt rows",
            "Upright row",
            "Lateral raise machine",
            "Dumbbell rear raises",
            "Cable rope rear delt rows",
            "Rear delts fly",
            "Cable rear delt fly 45"
        ]
    },
    {
        "name": "Forearms",
        "exercises": [
            "Barbell wrist curl",
            "Barbell reverse wrist curl",
            "Dumbbell wrist curl",
            "Dumbbell reverse wrist curl",
            "Cable over back wrist curl",
            "Pronator rope",
            "Pronator plates",
            "Brachioradialis hammer curls"
        ]
    },
    {
        "name": "Legs",
        "exercises": [
            "Leg extension",
            "Bench leg curl",
            "Seated leg curl",
            "Bulgarian split squats",
            "Smith Bulgarian split squats",
            "RDL barbell",
            "RDL dumbbell",
            "Calf stand on riser",
            "Calf raise machine",
            "Hyperextension",
            "Linear leg press",
            "Hack squat",
            "Seated leg press",
            "Hip adductor",
            "Hip abductor"
        ]
    },
    {
        "name": "Abs",
        "exercises": [
            "Abdominal machine",
            "Incline bench sit ups"
        ]
    }
]
