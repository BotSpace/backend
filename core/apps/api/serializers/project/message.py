# type: ignore
from rest_framework import serializers

from core.apps.api.models.message import MessageModel


class ButtonSerializer(serializers.Serializer):
    title = serializers.CharField()
    callback_data = serializers.CharField(required=False, allow_null=True)
    request_contact = serializers.BooleanField(default=False)
    request_location = serializers.BooleanField(default=False)
    link = serializers.CharField(required=False)


class SendMessageSerializer(serializers.ModelSerializer):
    buttons = serializers.ListSerializer(child=ButtonSerializer(), required=False)

    class Meta:
        model = MessageModel
        fields = ["id", "project", "caption", "message_type", "status", "button_type", "buttons"]
        extra_kwargs = {
            "status": {
                "read_only": True,
            }
        }


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageModel
        fields = ["id", "caption", "message_type", "total", "fail", "done"]
