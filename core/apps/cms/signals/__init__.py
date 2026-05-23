from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.apps.cms.models import Collection, Field
from core.apps.cms.services import cache, index_manager
from core.apps.cms.services.schema import schema_dict_for


@receiver(post_save, sender=Field)
@receiver(post_delete, sender=Field)
def _on_field_change(sender, instance: Field, **kwargs) -> None:
    coll = instance.collection
    # Refresh schema cache.
    coll.schema_version = (coll.schema_version or 0) + 1
    coll.save(update_fields=["schema_version", "updated_at"])
    cache.invalidate_schema(coll.project_id, coll.name)
    # Ensure MongoDB indexes track the desired set.
    try:
        index_manager.ensure_indexes(coll.project_id, coll.name, schema_dict_for(coll)["fields"])
    except Exception:
        # Index management must not block schema saves.
        pass


@receiver(post_save, sender=Collection)
def _on_collection_save(sender, instance: Collection, **kwargs) -> None:
    cache.invalidate_schema(instance.project_id, instance.name)
