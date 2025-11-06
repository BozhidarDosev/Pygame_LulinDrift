import json
from settings1 import SAVE_FILE

def load_game():
    try:
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"level": 1, "unlocked_cars": [1]}

def save_game(data):
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=4)
