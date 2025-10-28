from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def ws_publish(user_id, message):
    async_to_sync(get_channel_layer().group_send)(  # type: ignore
        "user_%s" % user_id,
        {"type": "chat_message", "message": message},
    )
