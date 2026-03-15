"""
Tests for is_primary field and relation field resolution.
"""
from unittest.mock import MagicMock

import pytest
from bson import ObjectId
from django.contrib.auth import get_user_model

from core.apps.api.models.project import ProjectModel
from core.apps.cms.enums.cms import FieldType
from core.apps.cms.models import CollectionModel, FieldModel
from core.apps.cms.services.action import ActionService

User = get_user_model()


@pytest.mark.django_db
class TestIsPrimaryField:
    """Tests for the is_primary boolean field on FieldModel."""

    def test_default_is_primary_false(self):
        """New fields should have is_primary=False by default."""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        collection = CollectionModel._create_fake(name="test_primary_default", user=user, project=project)

        field = FieldModel.objects.create(
            collection=collection,
            name="title",
            type=FieldType.TEXT.value,
        )

        assert field.is_primary is False

    def test_set_is_primary_true(self):
        """A field can be marked as primary."""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        collection = CollectionModel._create_fake(name="test_primary_set", user=user, project=project)

        field = FieldModel.objects.create(
            collection=collection,
            name="username",
            type=FieldType.TEXT.value,
            is_primary=True,
        )

        assert field.is_primary is True

    def test_primary_field_serializer_includes_is_primary(self):
        """Field serializers must include the is_primary field."""
        from core.apps.cms.serializers.cms.field import (
            BaseFieldSerializer,
            CreateFieldSerializer,
            ListFieldSerializer,
            RetrieveFieldSerializer,
        )

        for cls in [BaseFieldSerializer, CreateFieldSerializer, ListFieldSerializer, RetrieveFieldSerializer]:
            assert "is_primary" in cls.Meta.fields, f"is_primary missing from {cls.__name__}"

    def test_create_field_serializer_accepts_is_primary(self):
        """CreateFieldSerializer should accept is_primary=True."""
        from core.apps.cms.serializers.cms.field import CreateFieldSerializer

        user = User._create_fake()
        project = ProjectModel._create_fake()
        collection = CollectionModel._create_fake(name="test_primary_serial", user=user, project=project)

        serializer = CreateFieldSerializer(
            data={"name": "username", "type": "text", "required": False, "is_primary": True},
            context={"collection": collection},
        )

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["is_primary"] is True

    def test_update_collection_persists_is_primary(self):
        """UpdateCollectionSerializer should persist is_primary when updating fields."""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        collection = CollectionModel._create_fake(name="test_primary_update", user=user, project=project)

        from core.apps.cms.serializers.cms.collection import UpdateCollectionSerializer

        serializer = UpdateCollectionSerializer(
            instance=collection,
            data={
                "fields": [
                    {"name": "username", "type": "text", "required": False, "is_primary": True},
                    {"name": "email", "type": "text", "required": False, "is_primary": False},
                ]
            },
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        primary_field = collection.fields.get(name="username")
        non_primary_field = collection.fields.get(name="email")

        assert primary_field.is_primary is True
        assert non_primary_field.is_primary is False


@pytest.mark.django_db
class TestRelationResolution:
    """Tests for _resolve_relations in ActionService."""

    def _make_collection_with_relation(self, user, project, primary_field_name="title"):
        """Helper: create a related collection with a primary field."""
        related_col = CollectionModel._create_fake(
            name="test_rel_related",
            user=user,
            project=project,
        )
        FieldModel.objects.create(
            collection=related_col,
            name=primary_field_name,
            type=FieldType.TEXT.value,
            is_primary=True,
        )

        main_col = CollectionModel._create_fake(
            name="test_rel_main",
            user=user,
            project=project,
        )
        FieldModel.objects.create(
            collection=main_col,
            name="author",
            type=FieldType.RELATION.value,
            relation_collection=related_col,
        )
        return main_col, related_col

    def test_resolve_relation_with_string_id(self):
        """_resolve_relations replaces a bare ObjectId string with {_id, primary}."""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        main_col, related_col = self._make_collection_with_relation(user, project)

        related_oid = ObjectId()
        related_doc = {"_id": related_oid, "title": "Jane Doe"}

        mock_related_repo = MagicMock()
        mock_related_repo.find_one.return_value = related_doc

        mock_service = MagicMock()
        mock_service.get_repository.return_value = mock_related_repo

        service = ActionService(main_col, {}, mongo_service=mock_service)

        doc = {"author": str(related_oid)}
        resolved = service._resolve_relations(doc)

        assert resolved["author"] == {"_id": str(related_oid), "primary": "Jane Doe"}
        mock_related_repo.find_one.assert_called_once_with({"_id": related_oid})

    def test_resolve_relation_with_dict_id(self):
        """_resolve_relations handles existing dict values with _id key."""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        main_col, related_col = self._make_collection_with_relation(user, project)

        related_oid = ObjectId()
        related_doc = {"_id": related_oid, "title": "John"}

        mock_related_repo = MagicMock()
        mock_related_repo.find_one.return_value = related_doc

        mock_service = MagicMock()
        mock_service.get_repository.return_value = mock_related_repo

        service = ActionService(main_col, {}, mongo_service=mock_service)

        doc = {"author": {"_id": str(related_oid), "extra": "data"}}
        resolved = service._resolve_relations(doc)

        assert resolved["author"]["primary"] == "John"
        assert resolved["author"]["_id"] == str(related_oid)

    def test_resolve_relation_no_primary_field(self):
        """_resolve_relations leaves relation unchanged when related collection has no primary field."""
        user = User._create_fake()
        project = ProjectModel._create_fake()

        related_col = CollectionModel._create_fake(name="test_rel_noprimary", user=user, project=project)
        FieldModel.objects.create(
            collection=related_col,
            name="title",
            type=FieldType.TEXT.value,
            is_primary=False,  # no primary field
        )

        main_col = CollectionModel._create_fake(name="test_rel_noprimary_main", user=user, project=project)
        FieldModel.objects.create(
            collection=main_col,
            name="author",
            type=FieldType.RELATION.value,
            relation_collection=related_col,
        )

        mock_service = MagicMock()
        service = ActionService(main_col, {}, mongo_service=mock_service)

        original_value = str(ObjectId())
        doc = {"author": original_value}
        resolved = service._resolve_relations(doc)

        # Value should remain unchanged
        assert resolved["author"] == original_value
        mock_service.get_repository.assert_not_called()

    def test_resolve_relation_related_doc_not_found(self):
        """_resolve_relations leaves relation unchanged when related document is not in MongoDB."""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        main_col, related_col = self._make_collection_with_relation(user, project)

        mock_related_repo = MagicMock()
        mock_related_repo.find_one.return_value = None  # document not found

        mock_service = MagicMock()
        mock_service.get_repository.return_value = mock_related_repo

        service = ActionService(main_col, {}, mongo_service=mock_service)

        oid = str(ObjectId())
        doc = {"author": oid}
        resolved = service._resolve_relations(doc)

        # Should stay as original string when document not found
        assert resolved["author"] == oid

    def test_resolve_relation_none_value_skipped(self):
        """_resolve_relations skips None relation field values."""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        main_col, related_col = self._make_collection_with_relation(user, project)

        mock_service = MagicMock()
        service = ActionService(main_col, {}, mongo_service=mock_service)

        doc = {"author": None}
        resolved = service._resolve_relations(doc)

        assert resolved["author"] is None
        mock_service.get_repository.assert_not_called()

    def test_find_uses_resolve_relations(self):
        """ActionService.find() applies _resolve_relations to each document."""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        main_col, related_col = self._make_collection_with_relation(user, project)

        related_oid = ObjectId()
        related_doc = {"_id": related_oid, "title": "Alice"}

        mock_main_repo = MagicMock()
        mock_main_repo.find.return_value = [{"author": str(related_oid), "content": "Hello"}]

        mock_related_repo = MagicMock()
        mock_related_repo.find_one.return_value = related_doc

        def get_repo(col):
            if col == main_col:
                return mock_main_repo
            return mock_related_repo

        mock_service = MagicMock()
        mock_service.get_repository.side_effect = get_repo

        service = ActionService(main_col, {"where": {}}, mongo_service=mock_service)
        # Override the lazy-loaded repository to use our mock
        service._repository = mock_main_repo

        result, status = service.find()

        assert status == 200
        assert result[0]["author"]["primary"] == "Alice"

    def test_find_one_uses_resolve_relations(self):
        """ActionService.find_one() applies _resolve_relations to the returned document."""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        main_col, related_col = self._make_collection_with_relation(user, project)

        related_oid = ObjectId()
        related_doc = {"_id": related_oid, "title": "Bob"}

        mock_main_repo = MagicMock()
        mock_main_repo.find_one.return_value = {"author": str(related_oid), "content": "World"}

        mock_related_repo = MagicMock()
        mock_related_repo.find_one.return_value = related_doc

        def get_repo(col):
            if col == main_col:
                return mock_main_repo
            return mock_related_repo

        mock_service = MagicMock()
        mock_service.get_repository.side_effect = get_repo

        service = ActionService(main_col, {"where": {"content": "World"}}, mongo_service=mock_service)
        service._repository = mock_main_repo

        result, status = service.find_one()

        assert status == 200
        assert result["author"]["primary"] == "Bob"
