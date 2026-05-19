SPECTACULAR_SETTINGS = {
    "TITLE": "BotMother API",
    "DESCRIPTION": (
        "BotMother backend public API. All endpoints live under "
        "`/api/v1/`. Legacy `/api/` and root paths are deprecated and "
        "will be removed in a future release."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CAMELIZE_NAMES": True,
    "POSTPROCESSING_HOOKS": ["config.conf.spectacular.custom_postprocessing_hook"],
    "SERVERS": [
        {"url": "/api/v1", "description": "Stable v1"},
    ],
}


def custom_postprocessing_hook(result, generator, request, public):
    """
    Customizes the API schema to wrap all responses in a standard format.
    """
    for path, methods in result.get("paths", {}).items():
        for method, operation in methods.items():
            if "responses" in operation:
                for status_code, response in operation["responses"].items():
                    if "content" in response and status_code in ["200", "201", "202"]:
                        for content_type, content in response["content"].items():
                            # Wrap original schema
                            original_schema = content.get("schema", {})
                            response["content"][content_type]["schema"] = {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "boolean", "example": True},
                                    "data": original_schema,
                                },
                                "required": ["status", "data"],
                            }
    return result
