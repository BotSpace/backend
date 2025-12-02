"""
Tests for Relation field type
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.apps.cms.models import CollectionModel, FieldModel
from core.apps.cms.enums.cms import FieldType
from core.apps.api.models.project import ProjectModel

User = get_user_model()


@pytest.mark.django_db
class TestRelationField:
    """Test RELATION field type functionality"""
    
    def test_create_relation_field(self):
        """Test creating a RELATION type field"""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        
        # Create two collections with unique names
        users_collection = CollectionModel._create_fake(
            name="test_users_rel",
            user=user,
            project=project
        )
        posts_collection = CollectionModel._create_fake(
            name="test_posts_rel",
            user=user,
            project=project
        )
        
        # Create relation field in posts pointing to users
        author_field = FieldModel.objects.create(
            collection=posts_collection,
            name="author",
            type=FieldType.RELATION.value,
            relation_collection=users_collection,
            required=True
        )
        
        assert author_field.type == FieldType.RELATION.value
        assert author_field.relation_collection == users_collection
        assert author_field.relation_collection.name == "test_users_rel"
    
    def test_relation_field_serializer_validation(self):
        """Test that relation_collection is required for RELATION type"""
        from core.apps.cms.serializers.cms.field import CreateFieldSerializer
        
        user = User._create_fake()
        project = ProjectModel._create_fake()
        collection = CollectionModel._create_fake(
            name="test_collection_serial",
            user=user,
            project=project
        )
        
        # Try to create RELATION field without relation_collection
        serializer = CreateFieldSerializer(data={
            "name": "author",
            "type": "relation",
            "required": True
        })
        
        # Should fail validation
        assert not serializer.is_valid()
        assert "relation_collection" in serializer.errors
    
    def test_relation_field_data_validation(self):
        """Test validation of data with relation fields"""
        from core.apps.cms.services.collection import collection_validate_data
        
        user = User._create_fake()
        project = ProjectModel._create_fake()
        
        users_collection = CollectionModel._create_fake(
            name="test_users_valid",
            user=user,
            project=project
        )
        posts_collection = CollectionModel._create_fake(
            name="test_posts_valid",
            user=user,
            project=project
        )
        
        # Create relation field
        FieldModel.objects.create(
            collection=posts_collection,
            name="author",
            type=FieldType.RELATION.value,
            relation_collection=users_collection,
            required=True
        )
        
        # Valid data with ObjectId string
        data1 = {"author": "507f1f77bcf86cd799439011"}
        errors1, valid1 = collection_validate_data(posts_collection, data1)
        assert valid1 is True
        assert len(errors1) == 0
        
        # Valid data with object containing _id
        data2 = {"author": {"_id": "507f1f77bcf86cd799439011", "name": "John"}}
        errors2, valid2 = collection_validate_data(posts_collection, data2)
        assert valid2 is True
        assert len(errors2) == 0
        
        # Invalid data - object without _id
        data3 = {"author": {"name": "John"}}
        errors3, valid3 = collection_validate_data(posts_collection, data3)
        assert valid3 is False
        assert "author" in errors3
        
        # Invalid data - wrong type
        data4 = {"author": 123}
        errors4, valid4 = collection_validate_data(posts_collection, data4)
        assert valid4 is False
        assert "author" in errors4
    
    def test_multiple_relation_fields(self):
        """Test collection with multiple relation fields"""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        
        users_collection = CollectionModel._create_fake(
            name="test_users_multi",
            user=user,
            project=project
        )
        categories_collection = CollectionModel._create_fake(
            name="test_categories_multi",
            user=user,
            project=project
        )
        posts_collection = CollectionModel._create_fake(
            name="test_posts_multi",
            user=user,
            project=project
        )
        
        # Create multiple relation fields
        FieldModel.objects.create(
            collection=posts_collection,
            name="author",
            type=FieldType.RELATION.value,
            relation_collection=users_collection
        )
        FieldModel.objects.create(
            collection=posts_collection,
            name="category",
            type=FieldType.RELATION.value,
            relation_collection=categories_collection
        )
        
        assert posts_collection.fields.filter(type=FieldType.RELATION.value).count() == 2
        
        author_field = posts_collection.fields.get(name="author")
        category_field = posts_collection.fields.get(name="category")
        
        assert author_field.relation_collection == users_collection
        assert category_field.relation_collection == categories_collection
    
    def test_self_referencing_relation(self):
        """Test collection that references itself (e.g., comments with parent)"""
        user = User._create_fake()
        project = ProjectModel._create_fake()
        
        comments_collection = CollectionModel._create_fake(
            name="test_comments_self",
            user=user,
            project=project
        )
        
        # Create self-referencing field
        parent_field = FieldModel.objects.create(
            collection=comments_collection,
            name="parent",
            type=FieldType.RELATION.value,
            relation_collection=comments_collection,
            required=False
        )
        
        assert parent_field.relation_collection == comments_collection
        assert parent_field.collection == comments_collection
