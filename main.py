
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

TRUE_VALUES = {"true", "1", "yes", "on"}


def normalize_key(key):
    key = key.strip().lower()

    if key == "num_workers":
        return "workers"

    if key.startswith("app_"):
        key = key[4:]

    return key


def coerce(key, value):
    value = str(value)

    if key in {"port", "workers"}:
        return int(value)

    if key == "debug":
        return value.strip().lower() in TRUE_VALUES

    return value


def apply_layer(config, values):
    for key, value in values.items():
        if value is not None:
            key = normalize_key(key)
            config[key] = coerce(key, value)


@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    # 1. Start with a fresh copy of defaults.
    config = DEFAULTS.copy()

    # 2. Read the environment name and load its YAML file.
    environment = os.environ.get("APP_ENV", "development")
    yaml_path = Path(f"config.{environment}.yaml")

    if yaml_path.exists():
        with yaml_path.open(encoding="utf-8") as file:
            yaml_config = yaml.safe_load(file) or {}

        apply_layer(config, yaml_config)

    # 3. Apply .env values.
    env_file_config = dotenv_values(".env")
    apply_layer(config, env_file_config)

    # 4. Apply OS environment variables, except APP_ENV.
    os_config = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("APP_") and key != "APP_ENV"
    }
    apply_layer(config, os_config)

    # 5. Apply URL overrides last.
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = normalize_key(key)
        config[key] = coerce(key, value)

    # 6. Never expose the real API key.
    config["api_key"] = "****"

    return config
