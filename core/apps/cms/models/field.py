from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.apps.cms.enums import CascadeMode, FieldKind, IndexKind


class Field(models.Model):
    """One column in a cms Collection.

    `validators` JSON shape:
        {
          "regex": "...",
          "min_length": 3, "max_length": 120,
          "min": 0, "max": 100,
          "choices": ["a", "b"],            # for ENUM
          "ttl_seconds": 3600,              # for IndexKind.TTL
          "geo_2dsphere": true,             # for GEO
          "array_kind": "text|int|...",     # for ARRAY (element kind)
        }
    """

    collection = models.ForeignKey(
        "cms.Collection",
        on_delete=models.CASCADE,
        related_name="fields",
    )
    name = models.SlugField(max_length=64)
    label = models.CharField(max_length=120, blank=True, default="")
    kind = models.CharField(max_length=20, choices=FieldKind.choices, default=FieldKind.TEXT)

    required = models.BooleanField(default=False)
    default = models.JSONField(null=True, blank=True)
    validators = models.JSONField(default=dict, blank=True)

    # Relations
    relation_collection = models.ForeignKey(
        "cms.Collection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referenced_by",
    )
    cascade = models.CharField(
        max_length=20,
        choices=CascadeMode.choices,
        default=CascadeMode.RESTRICT,
    )

    # Indexing — driven by the schema, applied on Mongo via index_manager
    index = models.CharField(max_length=20, choices=IndexKind.choices, default=IndexKind.NONE)

    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cms_field"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["collection", "name"], name="cms_field_unique_per_coll"),
        ]
        indexes = [
            models.Index(fields=["collection", "kind"]),
        ]

    def __str__(self) -> str:
        return f"{self.collection_id}.{self.name}:{self.kind}"

    @property
    def is_relation(self) -> bool:
        return self.kind == FieldKind.RELATION
