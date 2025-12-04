# type: ignore
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django_core.mixins import BaseViewSetMixin

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

                # Count unread messages (messages without 'read' field or read=False)
                unread_count = chat_repo.count(
                    {"chat_id": chat_id, "$or": [{"read": {"$exists": False}}, {"read": False}]}
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
            result = chat_repo.update(where=query, data={"$set": {"read": True}})

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
            unread_messages = chat_repo.count({"$or": [{"read": {"$exists": False}}, {"read": False}]})

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
