import json, os, pathlib

CONFIG_DIR   = pathlib.Path(__file__).with_suffix('').parent / "../../config"
CONFIG_FILE  = CONFIG_DIR / "settings.json"
DEFAULT_CONF = {"theme": "dark"}          # “dark” ya da “light”

def load():
    if not CONFIG_FILE.exists():
        CONFIG_DIR.mkdir(exist_ok=True)
        save(DEFAULT_CONF)
        return dict(DEFAULT_CONF)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = {}
    cfg = dict(DEFAULT_CONF); cfg.update(data)
    return cfg

def save(data: dict):
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
