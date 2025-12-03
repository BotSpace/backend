# type: ignore
from rest_framework import serializers

from core.apps.api.models.message import MessageModel


class ButtonSerializer(serializers.Serializer):
    """Serializer for Telegram button"""
    title = serializers.CharField(help_text="Button text")
    callback_data = serializers.CharField(
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="Callback data for inline buttons"
    )
    link = serializers.URLField(
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="URL for inline URL buttons"
    )
    request_contact = serializers.BooleanField(
        default=False,
        help_text="Request contact for reply keyboard"
    )
    request_location = serializers.BooleanField(
        default=False,
        help_text="Request location for reply keyboard"
    )

    def validate(self, data):
        """Validate that button has either callback_data or link for inline buttons"""
        callback_data = data.get('callback_data')
        link = data.get('link')
        
        # Remove empty strings
        if callback_data == '':
            data.pop('callback_data', None)
            callback_data = None
        if link == '':
            data.pop('link', None)
            link = None
            
        return data


class SendMessageSerializer(serializers.ModelSerializer):
    """Serializer for sending messages to bot users"""
    buttons = serializers.ListField(
        child=serializers.ListField(child=ButtonSerializer()),
        required=False,
        allow_empty=True,
        help_text="2D array of buttons (rows and columns)"
    )
    photo = serializers.ImageField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="Photo file for photo messages"
    )
    video = serializers.FileField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="Video file for video messages"
    )

    class Meta:
        model = MessageModel
        fields = [
            "id", 
            "project", 
            "caption", 
            "message_type", 
            "status", 
            "button_type", 
            "buttons",
            "photo",
            "video",
            "total",
            "done",
            "fail"
        ]
        extra_kwargs = {
            "status": {"read_only": True},
            "total": {"read_only": True},
            "done": {"read_only": True},
            "fail": {"read_only": True},
        }

    def create(self, validated_data):
        """Create message and handle file uploads"""
        photo = validated_data.pop('photo', None)
        video = validated_data.pop('video', None)
        
        # Set file based on message type
        if photo and validated_data.get('message_type') == 'photo':
            validated_data['file'] = photo
        elif video and validated_data.get('message_type') == 'video':
            validated_data['file'] = video
            
        return super().create(validated_data)


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for listing messages"""
    class Meta:
        model = MessageModel
        fields = ["id", "caption", "message_type", "status", "total", "fail", "done"]
