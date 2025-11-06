import os
import json

PROFILE_DIR = os.path.join("data", "players")
os.makedirs(PROFILE_DIR, exist_ok=True)

DEFAULT_PROFILE = {
    "level": 1,
    "unlocked_cars": [1],
    "selected_car": 1
}


def profile_path(username):
    """Returns the absolute path to a player's save file."""
    filename = f"{username}.json"
    return os.path.join(PROFILE_DIR, filename)


def create_profile(username):
    """Creates a new profile file if it doesn't exist."""
    path = profile_path(username)
    if os.path.exists(path):
        return None  # profile already exists
    data = {"username": username, **DEFAULT_PROFILE}
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
    return data


def load_profile(username):
    """Loads existing player data, returns None if not found."""
    path = profile_path(username)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def save_profile(data):
    """Saves player data safely."""
    if not data or "username" not in data:
        return
    path = profile_path(data["username"])
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
