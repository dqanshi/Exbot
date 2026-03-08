import json
import os
from config import STATE_FILE


def save_state(line):

    with open(STATE_FILE, "w") as f:
        json.dump({"line": line}, f)


def load_state():

    if not os.path.exists(STATE_FILE):
        return 0

    with open(STATE_FILE) as f:
        data = json.load(f)

    return data["line"]
