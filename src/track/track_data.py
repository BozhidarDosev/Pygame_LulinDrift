# src/1/track_data.py

BASE_L1 = [
    {"length": 400, "curve": 0.0},
    {"length": 450, "curve": -0.9},
    {"length": 200, "curve": 0.0},
    {"length": 550, "curve": 1.0},
    {"length": 250, "curve": 0.0},
    {"length": 350, "curve": -0.7},
    {"length": 200, "curve": 0.0},
    {"length": 300, "curve": 0.8},
    {"length": 300, "curve": 0.0},
]

LEVELS = {
    1: {
        "length": 9000.0,
        "checkpoint_every": 600.0,
        "segments": BASE_L1 + BASE_L1 + BASE_L1,
    },
    2: {
        "length": 9000.0,
        "checkpoint_every": 600.0,
        "segments": ([
            {"length": 800, "curve": 0.0},
            {"length": 700, "curve": 0.6},
            {"length": 300, "curve": 0.0},
            {"length": 900, "curve": -1.0},
            {"length": 400, "curve": 0.0},
            {"length": 600, "curve": 0.8},
        ] * 3),
    },
    3: {
        "length": 9000.0,
        "checkpoint_every": 600.0,
        "segments": ([
            {"length": 600, "curve": 0.0},
            {"length": 800, "curve": -0.7},
            {"length": 350, "curve": 0.0},
            {"length": 900, "curve": 1.1},
            {"length": 500, "curve": 0.0},
            {"length": 650, "curve": -0.9},
        ] * 3),
    },
}
