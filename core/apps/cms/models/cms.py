# type: ignore
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.apps.api.models.project import ProjectModel
from core.apps.cms.enums import FieldType
from django_core.models import AbstractBaseModel
from model_bakery import baker

User = get_user_model()


class CollectionModel(AbstractBaseModel):
    name = models.CharField(verbose_name=_("name"), max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(
        "api.ProjectModel", on_delete=models.CASCADE, null=True, blank=True, related_name="collections"
    )

    @property
    def can_delete(self):
        return self.name not in [
            "users",
            "chat",
        ]

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(cls, name=None, **kwargs):
        """Create fake collection with reasonable name length

        Args:
            name: Collection name (max 50 chars for MongoDB namespace limit)
            **kwargs: Additional fields
        """
        import random
        import string

        # Generate short random name if not provided
        if name is None:
            name = "test_" + "".join(random.choices(string.ascii_lowercase, k=20))

        # Ensure name doesn't exceed MongoDB namespace limit
        # MongoDB limit: database.collection = 255 chars
        # Database name: project_{id} ≈ 15 chars
        # Safe collection name: max 50 chars
        name = name[:50]

        return baker.make(
            cls,
            name=name,
            user=kwargs.get("user") or User._create_fake(),
            project=kwargs.get("project") or ProjectModel._create_fake(),
            **{k: v for k, v in kwargs.items() if k not in ["user", "project", "name"]}
        )

    class Meta:
        db_table = "collection"
        verbose_name = _("CollectionModel")
        verbose_name_plural = _("CollectionModels")
        constraints = [models.UniqueConstraint(fields=["name", "project"], name="name_project_collection")]


class FieldModel(AbstractBaseModel):
    collection = models.ForeignKey("CollectionModel", on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(verbose_name=_("name"), max_length=255)
    type = models.CharField(_("name"), max_length=255, default=FieldType.TEXT.value, choices=FieldType.choices)
    required = models.BooleanField(_("required"), default=False)
    default = models.CharField(_("default"), max_length=255, null=True, blank=True)
    is_primary = models.BooleanField(
        _("is primary"),
        default=False,
        help_text=_("Marks this field as the primary display field for the collection"),
    )
    relation_collection = models.ForeignKey(
        "CollectionModel",
        on_delete=models.SET_NULL,
        related_name="related_fields",
        null=True,
        blank=True,
        help_text=_("Referenced collection for RELATION type fields"),
    )

    def __str__(self):
        return str(self.pk)

    @classmethod
    def _create_fake(cls, name=None, **kwargs):
        """Create fake field with reasonable name length

        Args:
            name: Field name (max 50 chars)
            **kwargs: Additional fields
        """
        import random
        import string

        if name is None:
            name = "field_" + "".join(random.choices(string.ascii_lowercase, k=20))

        name = name[:50]

        return baker.make(cls, name=name, **kwargs)

    class Meta:
        db_table = "field"
        verbose_name = _("FieldModel")
        verbose_name_plural = _("FieldModels")
        constraints = [models.UniqueConstraint(fields=["name", "collection"], name="field_name_collection_constraint")]
