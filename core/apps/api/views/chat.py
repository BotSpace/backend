# type: ignore
from core.apps.api.tasks.chat import send_telegram_message
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django_core.mixins import BaseViewSetMixin
from datetime import datetime

from core.apps.api.models.file import FileModel
from core.apps.api.models.project import ProjectModel
from core.apps.cms.models.cms import CollectionModel
from core.apps.cms.services.mongo import MongoRepository, MongoDBClient
from core.apps.api.serializers.chat import (
    UsersListResponseSerializer,
    MessagesListResponseSerializer,
    MarkAsReadRequestSerializer,
    MarkAsReadResponseSerializer,
    ChatStatsResponseSerializer,
    ErrorResponseSerializer,
    SendMessageRequestSerializer,
    SendMessageResponseSerializer,
)


@extend_schema(tags=["chat"])
class ChatViewSet(BaseViewSetMixin, ViewSet):
    """ViewSet for managing chat users and messages"""

    permission_classes = [IsAuthenticated]

    def get_collections(self, project_id):
        """Get users and chat collections for a project"""
        project = get_object_or_404(ProjectModel, id=project_id, owner=self.request.user)

        try:
            users_collection = CollectionModel.objects.get(project=project, name="users")
            chat_collection = CollectionModel.objects.get(project=project, name="chat")
        except CollectionModel.DoesNotExist:
            return None, None, None

        return project, users_collection, chat_collection

    @extend_schema(
        summary="Userlar va ularning xabarlarini olish",
        description="""
        Project uchun barcha userlarni olish, har bir user uchun:
        - Oxirgi 1 ta xabar
        - O'qilmagan xabarlar soni
        - Jami xabarlar soni
        
        Userlar oxirgi xabar vaqti bo'yicha tartiblangan (eng yangi xabar tepada).
        Pagination qo'llab-quvvatlanadi (limit va skip parametrlari).
        """,
        parameters=[
            OpenApiParameter(
                name="project_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Project ID",
                required=True,
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Qaytariladigan userlar soni",
                required=False,
                default=50,
            ),
            OpenApiParameter(
                name="skip",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="O'tkazib yuborilgan userlar soni (pagination)",
                required=False,
                default=0,
            ),
        ],
        responses={
            200: UsersListResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @action(detail=False, methods=["get"], url_path="users/(?P<project_id>[0-9]+)")
    def get_users_with_messages(self, request, project_id=None):
        """
        Get all users with their chat messages and unread count

        Query params:
        - limit: Number of users to return (default: 50)
        - skip: Number of users to skip (default: 0)
        """
        project, users_collection, chat_collection = self.get_collections(project_id)

        if not users_collection or not chat_collection:
            return Response({"error": "Collections not found for this project"}, status=status.HTTP_404_NOT_FOUND)

        # Get pagination params
        limit = int(request.query_params.get("limit", 50))
        skip = int(request.query_params.get("skip", 0))

        # Create repositories
        mongo_client = MongoDBClient()
        try:
            users_repo = MongoRepository(users_collection, mongo_client)
            chat_repo = MongoRepository(chat_collection, mongo_client)

            # Get all users (without pagination first, to sort by last message)
            users = users_repo.find(where={}, limit=0)

            # Get total count
            total_users = users_repo.count({})

            # For each user, get their last message and count unread ones
            result = []
            for user in users:
                chat_id = user.get("chat_id")

                # Get only the last message for this user
                messages = chat_repo.find(
                    where={"chat_id": chat_id}, sort=[("_id", -1)], limit=1  # Get only last message
                )

                # Count unread messages (messages without 'is_read' field or is_read=False)
                unread_count = chat_repo.count(
                    {"chat_id": chat_id, "$or": [{"is_read": {"$exists": False}}, {"is_read": False}]}
                )

                # Get total message count for this user
                total_message_count = chat_repo.count({"chat_id": chat_id})

                # Convert ObjectId to string for JSON serialization
                for msg in messages:
                    if "_id" in msg:
                        msg["_id"] = str(msg["_id"])

                # Convert user _id to string
                if "_id" in user:
                    user["_id"] = str(user["_id"])

                # Get last message timestamp for sorting and the message itself
                last_message = messages[0] if messages else None
                last_message_time = last_message.get("_id") if last_message else None

                result.append(
                    {
                        "user": user,
                        "last_message": last_message,
                        "unread_count": unread_count,
                        "total_messages": total_message_count,
                        "last_message_time": last_message_time,
                    }
                )

            # Sort users by last message time (newest first)
            result.sort(key=lambda x: x.get("last_message_time") or "", reverse=True)

            # Remove the temporary sorting field and apply pagination
            for item in result:
                item.pop("last_message_time", None)

            # Apply pagination after sorting
            paginated_result = result[skip : skip + limit] if limit > 0 else result[skip:]

            return Response({"users": paginated_result, "total": total_users, "limit": limit, "skip": skip})

        finally:
            mongo_client.close()

    @extend_schema(
        summary="Bitta user uchun barcha xabarlarni olish",
        description="""
        Bitta user (chat_id) uchun barcha xabarlarni olish.
        Pagination bilan qo'llab-quvvatlanadi.
        """,
        parameters=[
            OpenApiParameter(
                name="project_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Project ID",
                required=True,
            ),
            OpenApiParameter(
                name="chat_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Telegram chat ID",
                required=True,
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Qaytariladigan xabarlar soni",
                required=False,
                default=50,
            ),
            OpenApiParameter(
                name="skip",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="O'tkazib yuborilgan xabarlar soni",
                required=False,
                default=0,
            ),
        ],
        responses={
            200: MessagesListResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @action(detail=False, methods=["get"], url_path="messages/(?P<project_id>[0-9]+)/(?P<chat_id>[^/.]+)")
    def get_user_messages(self, request, project_id=None, chat_id=None):
        """
        Get messages for a specific user

        Query params:
        - limit: Number of messages to return (default: 50)
        - skip: Number of messages to skip (default: 0)
        """
        project, users_collection, chat_collection = self.get_collections(project_id)

        if not chat_collection:
            return Response({"error": "Chat collection not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get pagination params
        limit = int(request.query_params.get("limit", 50))
        skip = int(request.query_params.get("skip", 0))

        mongo_client = MongoDBClient()
        try:
            chat_repo = MongoRepository(chat_collection, mongo_client)

            # Get messages for this chat_id
            messages = chat_repo.find(where={"chat_id": chat_id}, limit=limit, skip=skip, sort=[("_id", -1)])

            # Get total count
            total_messages = chat_repo.count({"chat_id": chat_id})

            # Convert ObjectId to string
            for msg in messages:
                if "_id" in msg:
                    msg["_id"] = str(msg["_id"])

            return Response({"messages": messages, "total": total_messages, "limit": limit, "skip": skip})

        finally:
            mongo_client.close()

    @extend_schema(
        summary="Xabarlarni o'qilgan deb belgilash",
        description="""
        Userning xabarlarini o'qilgan deb belgilash.
        
        - Agar message_ids berilsa, faqat shu xabarlar o'qilgan bo'ladi
        - Agar message_ids berilmasa, userning barcha xabarlari o'qilgan bo'ladi
        """,
        parameters=[
            OpenApiParameter(
                name="project_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Project ID",
                required=True,
            ),
        ],
        request=MarkAsReadRequestSerializer,
        responses={
            200: MarkAsReadResponseSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @action(detail=False, methods=["post"], url_path="mark-read/(?P<project_id>[0-9]+)")
    def mark_messages_as_read(self, request, project_id=None):
        """
        Mark messages as read for a specific user

        Body:
        - chat_id: User's chat_id
        - message_ids: List of message IDs to mark as read (optional, if not provided marks all)
        """
        project, users_collection, chat_collection = self.get_collections(project_id)

        if not chat_collection:
            return Response({"error": "Chat collection not found"}, status=status.HTTP_404_NOT_FOUND)

        chat_id = request.data.get("chat_id")
        message_ids = request.data.get("message_ids", None)

        if not chat_id:
            return Response({"error": "chat_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        mongo_client = MongoDBClient()
        try:
            chat_repo = MongoRepository(chat_collection, mongo_client)

            # Build query
            query = {"chat_id": chat_id}

            if message_ids:
                from bson import ObjectId

                # Convert string IDs to ObjectId
                query["_id"] = {"$in": [ObjectId(mid) for mid in message_ids]}

            # Update messages to mark as read
            result = chat_repo.update(where=query, data={"$set": {"is_read": True, "updated_at": datetime.utcnow()}})

            return Response({"success": True, "modified_count": result.modified_count})

        finally:
            mongo_client.close()

    @extend_schema(
        summary="Chat statistikasini olish",
        description="""
        Project uchun chat statistikasi:
        - Jami userlar soni
        - Jami xabarlar soni  
        - O'qilmagan xabarlar soni
        - O'qilgan xabarlar soni
        """,
        parameters=[
            OpenApiParameter(
                name="project_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Project ID",
                required=True,
            ),
        ],
        responses={
            200: ChatStatsResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @action(detail=False, methods=["get"], url_path="stats/(?P<project_id>[0-9]+)")
    def get_chat_stats(self, request, project_id=None):
        """
        Get chat statistics for a project
        """
        project, users_collection, chat_collection = self.get_collections(project_id)

        if not users_collection or not chat_collection:
            return Response({"error": "Collections not found"}, status=status.HTTP_404_NOT_FOUND)

        mongo_client = MongoDBClient()
        try:
            users_repo = MongoRepository(users_collection, mongo_client)
            chat_repo = MongoRepository(chat_collection, mongo_client)

            # Get total users
            total_users = users_repo.count({})

            # Get total messages
            total_messages = chat_repo.count({})

            # Get unread messages count
            unread_messages = chat_repo.count({"$or": [{"is_read": {"$exists": False}}, {"is_read": False}]})

            return Response(
                {
                    "total_users": total_users,
                    "total_messages": total_messages,
                    "unread_messages": unread_messages,
                    "read_messages": total_messages - unread_messages,
                }
            )

        finally:
            mongo_client.close()

    @extend_schema(
        summary="Foydalanuvchiga xabar yuborish",
        description="""
        Bitta foydalanuvchiga xabar yuborish (matn va media).
        Yuborilgan xabar avtomatik ravishda chatga qo'shiladi va real-time stream orqali boshqa clientlarga yuboriladi.
        
        **Media yuborish:**
        - photo: max 10MB
        - video: max 50MB
        - audio: max 50MB
        - document: max 50MB
        
        **Telegram API limitlari:**
        - 1 ta botga 30 xabar/soniya
        - 1 ta chatga 1 xabar/soniya
        - Bu limitlar avtomatik kuzatiladi
        """,
        parameters=[
            OpenApiParameter(
                name="project_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Project ID",
                required=True,
            ),
        ],
        request=SendMessageRequestSerializer,
        responses={
            200: SendMessageResponseSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            413: ErrorResponseSerializer,
        },
    )
    @action(detail=False, methods=["post"], url_path="send-message/(?P<project_id>[0-9]+)")
    def send_message(self, request, project_id=None):
        """
        Send a message to a user (text and/or media)

        Body:
        - chat_id: User's Telegram chat ID
        - message: Message text or caption (optional if file is provided)
        - file: File to send (photo, video, audio, document) - optional
        - message_type: Type of message (text, photo, video, audio, document) - default: text
        """
        project, users_collection, chat_collection = self.get_collections(project_id)

        if not chat_collection:
            return Response({"error": "Chat collection not found"}, status=status.HTTP_404_NOT_FOUND)

        chat_id = request.data.get("chat_id")
        message = request.data.get("message", "")
        file = request.FILES.get("file")
        message_type = request.data.get("message_type", "text")

        if not chat_id:
            return Response({"error": "chat_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not message and not file:
            return Response({"error": "Either message or file must be provided"}, status=status.HTTP_400_BAD_REQUEST)

        if file and message_type == "text":
            return Response(
                {"error": "message_type must be specified when file is provided (photo, video, audio, document)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file:
            file_size_mb = file.size / (1024 * 1024)  # Convert to MB

            if message_type == "photo" and file_size_mb > 10:
                return Response(
                    {"error": "Photo file size must be less than 10MB"}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                )
            elif message_type in ["video", "audio", "document"] and file_size_mb > 50:
                return Response(
                    {"error": f"{message_type.capitalize()} file size must be less than 50MB"},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

        mongo_client = MongoDBClient()
        try:
            chat_repo = MongoRepository(chat_collection, mongo_client)
            message_data = {
                "chat_id": chat_id,
                "message": message,
                "message_type": message_type,
                "is_read": False,
                "from_admin": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            file_id = None
            if file:
                file_instance = FileModel.objects.create(
                    project=project,
                    user=request.user,
                    file=file,
                )
                message_data["file"] = str(file_instance.uuid)
                file_id = file_instance.pk

            result = chat_repo.insert_one(message_data)

            if result:
                message_id = str(result)
                message_data["_id"] = message_id
            else:
                message_id = None
            telegram_sent = False
            try:
                send_telegram_message.delay(
                    chat_id=chat_id,
                    project_id=project_id,
                    message_type=message_type,
                    text=message,
                    file_id=file_id,
                )
                telegram_sent = True
            except ImportError:
                pass

            return Response(
                {"success": True, "message_id": message_id, "message": message_data, "telegram_sent": telegram_sent}
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to send message: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            mongo_client.close()
