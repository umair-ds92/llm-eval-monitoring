import os
import yaml


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        cfg = yaml.safe_load(f) or {}

    env = os.getenv("APP_ENV")
    if env:
        cfg["environment"] = env

    return cfg
