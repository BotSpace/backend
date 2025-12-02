from rest_framework import serializers

from core.apps.cms.models import FieldModel
from core.apps.cms.enums.cms import FieldType


class BaseFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldModel
        fields = [
            "id",
            "name",
            "type",
            "required",
            "default",
            "relation_collection",
        ]
    
    def validate(self, data):
        """Validate that relation_collection is set only for RELATION type"""
        field_type = data.get('type')
        relation_collection = data.get('relation_collection')
        
        if field_type == FieldType.RELATION.value:
            if not relation_collection:
                raise serializers.ValidationError({
                    "relation_collection": "relation_collection is required for RELATION type fields"
                })
        else:
            # Clear relation_collection for non-relation fields
            data['relation_collection'] = None
        
        return data


class ListFieldSerializer(BaseFieldSerializer):
    class Meta(BaseFieldSerializer.Meta): ...


class RetrieveFieldSerializer(BaseFieldSerializer):
    relation_collection = serializers.CharField(source='relation_collection.name', read_only=True, allow_null=True)
    
    class Meta(BaseFieldSerializer.Meta):
        fields = [
            "id",
            "name",
            "type",
            "required",
            "default",
            "relation_collection",  # Now returns name instead of ID
        ]


class CreateFieldSerializer(BaseFieldSerializer):
    class Meta(BaseFieldSerializer.Meta):
        fields = [
            "id",
            "name",
            "type",
            "required",
            "default",
            "relation_collection",
        ]
