# type: ignore
from rest_framework import serializers


class UserSerializer(serializers.Serializer):
    """User ma'lumotlari"""
    _id = serializers.CharField(read_only=True, help_text="MongoDB ObjectId")
    chat_id = serializers.CharField(help_text="Telegram chat ID")
    first_name = serializers.CharField(help_text="User ismi")
    last_name = serializers.CharField(required=False, allow_blank=True, help_text="User familiyasi")
    created_at = serializers.DateTimeField(required=False, help_text="Yaratilgan vaqt")


class MessageSerializer(serializers.Serializer):
    """Chat xabari"""
    _id = serializers.CharField(read_only=True, help_text="MongoDB ObjectId")
    chat_id = serializers.CharField(help_text="Telegram chat ID")
    message = serializers.CharField(required=False, allow_blank=True, help_text="Xabar matni yoki caption")
    message_type = serializers.CharField(required=False, allow_null=True, help_text="Xabar turi (text, photo, video, audio, document)")
    is_read = serializers.BooleanField(default=False, help_text="O'qilgan/o'qilmagan")
    from_admin = serializers.BooleanField(default=False, required=False, help_text="Admin tomonidan yuborilganmi")
    file_url = serializers.CharField(required=False, allow_null=True, help_text="File URL")
    file_name = serializers.CharField(required=False, allow_null=True, help_text="File nomi")
    file_size = serializers.IntegerField(required=False, allow_null=True, help_text="File hajmi (bytes)")
    created_at = serializers.DateTimeField(required=False, help_text="Yaratilgan vaqt")
    updated_at = serializers.DateTimeField(required=False, help_text="Yangilangan vaqt")


class UserWithMessagesSerializer(serializers.Serializer):
    """User va uning xabarlari"""
    user = UserSerializer(help_text="User ma'lumotlari")
    last_message = MessageSerializer(required=False, allow_null=True, help_text="Oxirgi xabar")
    unread_count = serializers.IntegerField(help_text="O'qilmagan xabarlar soni")
    total_messages = serializers.IntegerField(help_text="Jami xabarlar soni")


class UsersListResponseSerializer(serializers.Serializer):
    """Userlar ro'yxati response"""
    users = UserWithMessagesSerializer(many=True, help_text="Userlar va ularning xabarlari")
    total = serializers.IntegerField(help_text="Jami userlar soni")
    limit = serializers.IntegerField(help_text="Sahifadagi elementlar soni")
    skip = serializers.IntegerField(help_text="O'tkazib yuborilgan elementlar soni")


class MessagesListResponseSerializer(serializers.Serializer):
    """Xabarlar ro'yxati response"""
    messages = MessageSerializer(many=True, help_text="Xabarlar ro'yxati")
    total = serializers.IntegerField(help_text="Jami xabarlar soni")
    limit = serializers.IntegerField(help_text="Sahifadagi xabarlar soni")
    skip = serializers.IntegerField(help_text="O'tkazib yuborilgan xabarlar soni")


class MarkAsReadRequestSerializer(serializers.Serializer):
    """Xabarlarni o'qilgan qilish request"""
    chat_id = serializers.CharField(required=True, help_text="User chat ID")
    message_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
        help_text="O'qilgan qilish uchun xabar IDlar. Agar berilmasa, barcha xabarlar o'qilgan bo'ladi"
    )


class MarkAsReadResponseSerializer(serializers.Serializer):
    """Xabarlarni o'qilgan qilish response"""
    success = serializers.BooleanField(help_text="Muvaffaqiyatli bajarildi")
    modified_count = serializers.IntegerField(help_text="O'zgartirilgan xabarlar soni")


class ChatStatsResponseSerializer(serializers.Serializer):
    """Chat statistikasi response"""
    total_users = serializers.IntegerField(help_text="Jami userlar soni")
    total_messages = serializers.IntegerField(help_text="Jami xabarlar soni")
    unread_messages = serializers.IntegerField(help_text="O'qilmagan xabarlar soni")
    read_messages = serializers.IntegerField(help_text="O'qilgan xabarlar soni")


class ErrorResponseSerializer(serializers.Serializer):
    """Xato response"""
    error = serializers.CharField(help_text="Xato xabari")


class SendMessageRequestSerializer(serializers.Serializer):
    """Xabar yuborish request"""
    chat_id = serializers.CharField(required=True, help_text="User chat ID (Telegram chat ID)")
    message = serializers.CharField(required=False, allow_blank=True, help_text="Yuborilayotgan xabar matni (caption)")
    file = serializers.FileField(required=False, allow_null=True, help_text="Yuborilayotgan file (photo, video, audio, document)")
    message_type = serializers.ChoiceField(
        choices=['text', 'photo', 'video', 'audio', 'document'],
        required=False,
        allow_null=True,
        default='text',
        help_text="Xabar turi (text, photo, video, audio, document)"
    )
    

class SendMessageResponseSerializer(serializers.Serializer):
    """Xabar yuborish response"""
    success = serializers.BooleanField(help_text="Muvaffaqiyatli yuborildi")
    message_id = serializers.CharField(help_text="Yuborilgan xabar ID", allow_null=True)
    message = MessageSerializer(help_text="Yuborilgan xabar ma'lumotlari", allow_null=True)
    telegram_sent = serializers.BooleanField(default=False, help_text="Telegram orqali yuborilganmi")
