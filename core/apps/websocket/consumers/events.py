import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer


class EventsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        logging.info("user_%s" % self.user.pk)
        await self.channel_layer.group_add("user_%s" % self.user.pk, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("user_%s" % self.user.pk, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        await self.channel_layer.group_send("user_%s" % self.user.pk, {"type": "chat_message", "message": message})

    async def chat_message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))
