def default_flow() -> dict:
    return {
        "nodes": [
            {
                "id": "node_0",
                "type": "CommandTriggerNode",
                "position": {"x": -63.47046493902432, "y": 208.63414634146335},
                "data": {"context": {}, "node_type": "CommandTriggerNode", "global": True, "command": "/start"},
                "width": 320,
                "height": 236,
            },
            {
                "id": "node_1",
                "type": "SendTextMessageNode",
                "position": {"x": -118.60948932926817, "y": 579.7048780487804},
                "data": {
                    "recipients": {"sendToSender": True, "additionalIds": []},
                    "keyboard": {
                        "active": "inline",
                        "inline": [
                            [
                                {
                                    "id": "btn-1765521805822",
                                    "text": "Bot yaratish",
                                    "type": "url",
                                    "value": "https://botspace.uz",
                                }
                            ]
                        ],
                        "reply": [],
                    },
                    "messageText": "Assalomu Alaykum {{first_name}} botga xush kelibsiz\n\nbot botspace.uz da yaratildi",
                    "parseMode": "HTML",
                    "disableNotification": False,
                    "protectContent": False,
                },
                "width": 400,
                "height": 480,
                "selected": True,
                "positionAbsolute": {"x": -118.60948932926817, "y": 579.7048780487804},
                "dragging": False,
            },
        ],
        "edges": [
            {
                "source": "node_0",
                "sourceHandle": "source-handler",
                "target": "node_1",
                "targetHandle": "target-handler",
                "type": "step",
                "markerEnd": {"type": "arrow", "width": 30, "height": 30, "color": "#495057"},
                "style": {"strokeWidth": 1.5, "stroke": "#495057"},
                "animated": False,
                "id": "reactflow__edge-node_0source-handler-node_1target-handler",
            }
        ],
    }
