import json

from pydantic import BaseModel

from core.domain.ws import EventTypes, WsEvents
from core.services.redis_service import publish


def ws_publish(user_id, schema: BaseModel, event: EventTypes):
    data = WsEvents(event=event, data=schema)
    publish(
        "websocket",
        json.dumps({
            "room": "user_%s" % user_id,
            "data": data.model_dump(),
        }),
    )
