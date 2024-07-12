from decouple import config

ACTIONS_FILE_PATH = config(
    "ACTIONS_FILE_PATH", cast=str, default="actions.json"
)
