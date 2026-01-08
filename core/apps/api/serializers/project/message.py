# type: ignore
import json
from rest_framework import serializers

from core.apps.api.models.message import MessageModel


class ButtonSerializer(serializers.Serializer):
    """Serializer for Telegram button"""

    title = serializers.CharField(help_text="Button text")
    callback_data = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, help_text="Callback data for inline buttons"
    )
    link = serializers.URLField(
        required=False, allow_null=True, allow_blank=True, help_text="URL for inline URL buttons"
    )
    request_contact = serializers.BooleanField(default=False, help_text="Request contact for reply keyboard")
    request_location = serializers.BooleanField(default=False, help_text="Request location for reply keyboard")

    def validate(self, data):
        """Validate that button has either callback_data or link for inline buttons"""
        callback_data = data.get("callback_data")
        link = data.get("link")

        # Remove empty strings
        if callback_data == "":
            data.pop("callback_data", None)
            callback_data = None
        if link == "":
            data.pop("link", None)
            link = None

        return data


class SendMessageSerializer(serializers.ModelSerializer):
    """Serializer for sending messages to bot users"""

    buttons = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="2D array of buttons (rows and columns) - can be JSON string or array",
    )
    photo = serializers.ImageField(
        required=False, allow_null=True, write_only=True, help_text="Photo file for photo messages (max 10 MB)"
    )
    video = serializers.FileField(
        required=False, allow_null=True, write_only=True, help_text="Video file for video messages (max 50 MB)"
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
            "fail",
        ]
        extra_kwargs = {
            "status": {"read_only": True},
            "total": {"read_only": True},
            "done": {"read_only": True},
            "fail": {"read_only": True},
        }

    def validate_project(self, value):
        if value.owner != self.context["request"].user:
            raise serializers.ValidationError("Project does not belong to the authenticated user")
        return value

    def validate_photo(self, value):
        """Validate photo file size (Telegram limit: 10 MB)"""
        if value:
            max_size = 10 * 1024 * 1024  # 10 MB
            if value.size > max_size:
                size_mb = value.size / 1024 / 1024
                raise serializers.ValidationError(f"Photo size is {size_mb:.2f} MB. Telegram Bot API limit is 10 MB.")
        return value

    def validate_video(self, value):
        """Validate video file size (Telegram limit: 50 MB)"""
        if value:
            max_size = 50 * 1024 * 1024  # 50 MB
            if value.size > max_size:
                size_mb = value.size / 1024 / 1024
                raise serializers.ValidationError(f"Video size is {size_mb:.2f} MB. Telegram Bot API limit is 50 MB.")
        return value

    def validate_buttons(self, value):
        """Parse buttons from JSON string if needed and validate structure"""
        # If buttons is a string, parse it
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format for buttons")

        # If empty or None, return empty list
        if not value:
            return []

        # Validate it's a list
        if not isinstance(value, list):
            raise serializers.ValidationError("Buttons must be a 2D array (list of lists)")

        # Validate structure: must be list of lists
        for i, row in enumerate(value):
            if not isinstance(row, list):
                raise serializers.ValidationError(f"Row {i} must be a list of button objects")

            # Validate each button in the row
            for j, button in enumerate(row):
                if not isinstance(button, dict):
                    raise serializers.ValidationError(f"Button at row {i}, position {j} must be an object")

                # Validate required field
                if "title" not in button:
                    raise serializers.ValidationError(f"Button at row {i}, position {j} must have a 'title' field")

                # Use ButtonSerializer to validate each button
                button_serializer = ButtonSerializer(data=button)
                if not button_serializer.is_valid():
                    raise serializers.ValidationError(f"Button at row {i}, position {j}: {button_serializer.errors}")

        return value

    def create(self, validated_data):
        """Create message and handle file uploads"""
        photo = validated_data.pop("photo", None)
        video = validated_data.pop("video", None)

        # Ensure buttons is not None
        if validated_data.get("buttons") is None:
            validated_data["buttons"] = []

        # Set file based on message type
        if photo and validated_data.get("message_type") == "photo":
            validated_data["file"] = photo
        elif video and validated_data.get("message_type") == "video":
            validated_data["file"] = video

        return super().create(validated_data)


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for listing messages"""

    class Meta:
        model = MessageModel
        fields = ["id", "caption", "message_type", "status", "total", "fail", "done", "file_id"]
        extra_kwargs = {
            "file_id": {"read_only": True},
        }
