def default_flow() -> dict:
    return {
        "nodes": [
            {
                "id": "node_1764942725377_0",
                "data": {"global": True, "command": "/start", "context": {}, "node_type": "CommandTriggerNode"},
                "type": "CommandTriggerNode",
                "width": 320,
                "height": 236,
                "dragging": False,
                "position": {"x": 256, "y": 193},
                "selected": False,
            },
            {
                "id": "node_1764942728388_1",
                "data": {
                    "keyboard": {
                        "active": "inline",
                        "inline": [
                            [
                                {
                                    "id": "btn-1764942771822",
                                    "text": "Bot haqida malumot",
                                    "type": "callback",
                                    "value": "info",
                                }
                            ],
                            [
                                {
                                    "id": "btn-1764943122674",
                                    "text": "Bot yaratish",
                                    "type": "url",
                                    "value": "https://botspace.uz/uz/website",
                                }
                            ],
                        ],
                        "reply": [],
                    },
                    "parseMode": "None",
                    "recipients": {"sendToSender": True, "additionalIds": []},
                    "messageText": {
                        "time": 1764942745533,
                        "blocks": [
                            {
                                "id": "2sezHPbhBI",
                                "data": {"text": "Assalomu Alaykum {{first_name}} botga xush kelibsiz"},
                                "type": "paragraph",
                            }
                        ],
                        "version": "2.31.0",
                    },
                },
                "type": "SendTextMessageNode",
                "width": 400,
                "height": 527,
                "dragging": False,
                "position": {"x": 212.16947571835288, "y": 495.6874641042931},
                "selected": False,
                "positionAbsolute": {"x": 212.16947571835288, "y": 495.6874641042931},
            },
            {
                "id": "node_1764943126709_0",
                "type": "CallbackQueryTriggerNode",
                "position": {"x": 224.43450724471836, "y": 1107.8725618257108},
                "data": {
                    "context": {"value": "info"},
                    "node_type": "CallbackQueryTriggerNode",
                    "global": False,
                    "filter": "equals",
                },
                "width": 320,
                "height": 308,
                "selected": False,
                "positionAbsolute": {"x": 224.43450724471836, "y": 1107.8725618257108},
                "dragging": False,
            },
            {
                "id": "node_1764943145008_2",
                "type": "SendTextMessageNode",
                "position": {"x": 202.48035174089603, "y": 1525.459534044204},
                "data": {
                    "recipients": {"sendToSender": True, "additionalIds": []},
                    "keyboard": {"active": "inline", "inline": [], "reply": []},
                    "messageText": {
                        "time": 1764944001378,
                        "blocks": [
                            {
                                "id": "fv6cMIkvlM",
                                "type": "paragraph",
                                "data": {
                                    "text": "Bot botspace.uz yordamida yaratilgan. Siz ham o'z biznesingizni BotSpace yordamida rivojlantirishingiz mumkun"
                                },
                            }
                        ],
                        "version": "2.31.0",
                    },
                    "parseMode": "None",
                },
                "width": 400,
                "height": 533,
                "selected": True,
                "positionAbsolute": {"x": 202.48035174089603, "y": 1525.459534044204},
                "dragging": False,
            },
        ],
        "edges": [
            {
                "id": "reactflow__edge-node_1764942725377_0source-handler-node_1764942728388_1target-handler",
                "type": "step",
                "style": {"stroke": "#495057", "strokeWidth": 1.5},
                "source": "node_1764942725377_0",
                "target": "node_1764942728388_1",
                "animated": False,
                "markerEnd": {"type": "arrow", "color": "#495057", "width": 30, "height": 30},
                "sourceHandle": "source-handler",
                "targetHandle": "target-handler",
            },
            {
                "source": "node_1764942728388_1",
                "sourceHandle": "source-handler",
                "target": "node_1764943126709_0",
                "targetHandle": "target-handler",
                "type": "step",
                "markerEnd": {"type": "arrow", "width": 30, "height": 30, "color": "#495057"},
                "style": {"strokeWidth": 1.5, "stroke": "#495057"},
                "animated": False,
                "id": "reactflow__edge-node_1764942728388_1source-handler-node_1764943126709_0target-handler",
            },
            {
                "source": "node_1764943126709_0",
                "sourceHandle": "source-handler",
                "target": "node_1764943145008_2",
                "targetHandle": "target-handler",
                "type": "step",
                "markerEnd": {"type": "arrow", "width": 30, "height": 30, "color": "#495057"},
                "style": {"strokeWidth": 1.5, "stroke": "#495057"},
                "animated": False,
                "id": "reactflow__edge-node_1764943126709_0source-handler-node_1764943145008_2target-handler",
            },
        ],
    }
