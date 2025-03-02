class Exercise:
    name: str
    reps: float
    weight: float

reps = [
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", 
    "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"
]

weights = [
    "5", "7.5", "10", "12.5", "15", "17.5",
    "20", "22.5", "25", "30", "35", "40",
    "45", "50", "55", "60", "65", "70",
    "75", "80", "90", "100", "110", "120"
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
            "Dumbbell incline bench press",
            "Bench press incline",
            "Крос на грудь",
            "Hammer",
            "Fly machine",
            "Chest press machine"
        ]
    },
    {
        "name": "Shoulders",
        "exercises": [
            "Cable lateral raises",
            "Sholder press machine",
            "Cable Rope Rear Delt Rows",
            "Lateral raise machine",
            "Dumbbell shoulders press (bench)",
            "Dumbbell lateral raises",
            "Dumbbell rear raises",
            "Rear delts fly",
            "45* cable rear delt fly",
            "Тяга на заднюю (45*)",
            "Протяжка"
        ]
    },
    {
        "name": "Back",
        "exercises": [
            "Wide-grip lat pull-down"
        ]
    },
    {
        "name": "Biceps",
        "exercises": []
    },
    {
        "name": "Triceps",
        "exercises": [
            "French press",
            "Triceps pushdown V-bar",
            "Close-grip bench press",
            "Cable overhead shoulder extension",
            "Single-arm cable triceps pushdown"
        ]
    },
    {
        "name": "Forearms",
        "exercises": []
    },
    {
        "name": "Legs",
        "exercises": []
    },
    {
        "name": "Abs",
        "exercises": []
    }
]
