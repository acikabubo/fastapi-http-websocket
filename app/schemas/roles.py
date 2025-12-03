from app.schemas.generic_typing import JsonSchemaType

ROLE_CONFIG_SCHEMA: JsonSchemaType = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "roles": {"type": "array", "items": {"type": "string"}},
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
    "required": ["roles", "http"],
    "additionalProperties": False,
}
