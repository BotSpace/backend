from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from pydantic import BaseModel

from core.domain.ws import EventTypes, WsEvents


def ws_publish(user_id, schema: BaseModel, event: EventTypes):
    data = WsEvents(event=event, data=schema)
    async_to_sync(get_channel_layer().group_send)(  # type: ignore
        "user_%s" % user_id,
        {"type": "chat_message", "message": data.model_dump()},
    )
