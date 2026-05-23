# type: ignore
"""
Migration script to move from single MongoDB database with prefixed collections
to separate databases per project.

Old structure: botmother DB -> collection_user_project_name collections
New structure: project_{id} DB -> {name} collections
"""
import logging
from django.core.management.base import BaseCommand
from core.apps.cms_legacy.models.cms import CollectionModel
from core.apps.cms_legacy.services.mongo import MongoDBClient, MongoService
from rich.console import Console
from rich.progress import track

console = Console()


class Command(BaseCommand):
    help = "Migrate MongoDB from single database to per-project databases"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without actually migrating",
        )
        parser.add_argument(
            "--drop-old",
            action="store_true",
            help="Drop old collections after successful migration",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        drop_old = options["drop_old"]

        if dry_run:
            console.print("[yellow]DRY RUN MODE - Ma'lumotlar ko'chirilmaydi[/yellow]")

        # Initialize MongoDB service
        mongo_client = MongoDBClient()
        mongo_service = MongoService(mongo_client)
        
        old_db = mongo_client.client["botmother"]

        # Get all collections from Django
        collections = CollectionModel.objects.select_related("project", "user").all()

        if not collections.exists():
            console.print("[green]Hech qanday collection topilmadi[/green]")
            return

        console.print(f"\n[cyan]Jami {collections.count()} ta collection topildi[/cyan]\n")

        migrated_count = 0
        error_count = 0
        skipped_count = 0

        for collection_model in track(list(collections), description="Ko'chirish..."):
            # Old format: collection_user_project_name
            old_collection_name = f"collection_{collection_model.user_id}_{collection_model.project_id}_{collection_model.name}"
            
            # New format: project_{id} DB -> {name} collection
            new_db_name = f"project_{collection_model.project_id}"
            new_collection_name = collection_model.name

            try:
                # Check if old collection exists
                if old_collection_name not in old_db.list_collection_names():
                    console.print(
                        f"[yellow]Skip: {old_collection_name} topilmadi[/yellow]"
                    )
                    skipped_count += 1
                    continue

                # Get document count
                old_collection = old_db[old_collection_name]
                doc_count = old_collection.count_documents({})

                console.print(
                    f"\n[blue]Ko'chirish:[/blue] {old_collection_name} -> "
                    f"{new_db_name}.{new_collection_name} ({doc_count} ta document)"
                )

                if dry_run:
                    console.print(f"  [yellow]DRY RUN: O'zgarish qilinmadi[/yellow]")
                    migrated_count += 1
                    continue

                # Create new database and collection
                new_db = mongo_client.get_project_database(collection_model.project_id)
                new_collection = new_db[new_collection_name]

                # Check if new collection already has data
                existing_count = new_collection.count_documents({})
                if existing_count > 0:
                    console.print(
                        f"  [yellow]Warning: Yangi collection allaqachon {existing_count} ta document bor[/yellow]"
                    )

                # Copy all documents
                if doc_count > 0:
                    documents = list(old_collection.find({}))
                    if documents:
                        new_collection.insert_many(documents)
                        console.print(f"  [green]✓ {len(documents)} ta document ko'chirildi[/green]")

                # Copy indexes
                indexes = list(old_collection.list_indexes())
                for index in indexes:
                    if index["name"] != "_id_":  # Skip default _id index
                        try:
                            index_keys = list(index["key"].items())
                            index_options = {k: v for k, v in index.items() if k not in ["key", "v", "ns"]}
                            new_collection.create_index(index_keys, **index_options)
                            console.print(f"  [green]✓ Index ko'chirildi: {index['name']}[/green]")
                        except Exception as e:
                            console.print(f"  [yellow]Warning: Index ko'chirishda xatolik: {e}[/yellow]")

                # Drop old collection if requested
                if drop_old:
                    old_collection.drop()
                    console.print(f"  [red]✓ Eski collection o'chirildi[/red]")

                migrated_count += 1

            except Exception as e:
                error_count += 1
                console.print(f"  [red]✗ Xatolik: {e}[/red]")
                logging.error(
                    f"Migration error for collection {old_collection_name}: {e}",
                    exc_info=True,
                )

        # Summary
        console.print("\n[bold cyan]Natija:[/bold cyan]")
        console.print(f"  ✓ Ko'chirildi: {migrated_count}")
        console.print(f"  ⊘ O'tkazildi: {skipped_count}")
        console.print(f"  ✗ Xatolar: {error_count}")

        if dry_run:
            console.print("\n[yellow]Bu dry run edi. Haqiqiy migratsiya uchun --dry-run parametrisiz ishga tushiring.[/yellow]")
        elif drop_old:
            console.print("\n[green]Migratsiya tugallandi va eski collectionlar o'chirildi![/green]")
        else:
            console.print("\n[green]Migratsiya tugallandi! Eski collectionlarni --drop-old bilan o'chirishingiz mumkin.[/green]")
