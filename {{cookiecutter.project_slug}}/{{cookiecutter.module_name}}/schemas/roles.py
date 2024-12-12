from {{cookiecutter.module_name}}.schemas.generic_typing import JsonSchemaType

ROLE_CONFIG_SCHEMA: JsonSchemaType = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "roles": {"type": "array", "items": {"type": "string"}},
        "ws": {
            "type": "object",
            "patternProperties": {"^\\d+$": {"type": "string"}},
            "additionalProperties": False,
        },
        "http": {
            "type": "object",
            "patternProperties": {
                "^/": {
                    "type": "object",
                    "properties": {
                        "GET": {"type": "string"},
                        "POST": {"type": "string"},
                        "PUT": {"type": "string"},
                        "DELETE": {"type": "string"},
                    },
                    "additionalProperties": False,
                }
            },
            "additionalProperties": False,
        },
    },
    "required": ["roles", "ws", "http"],
    "additionalProperties": False,
}
