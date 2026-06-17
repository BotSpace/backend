"""v2 migration: credentials app — drop CredentialType table, remove Credential.project FK,
replace Credential.type FK with type_key CharField, update unique constraint.

Forward-safe: checks column/table existence before acting so it can run whether
v1 (0001+0002) is applied or not. In practice prod always has 0001+0002, but the
guard makes it re-runnable without errors.
"""
from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("credentials", "0002_seed_builtin_types"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Drop old unique constraint (project, name) — ignore if missing
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        DO $$
                        BEGIN
                            IF EXISTS (
                                SELECT 1 FROM pg_constraint
                                WHERE conname = 'credential_unique_name_per_project'
                            ) THEN
                                ALTER TABLE credential
                                    DROP CONSTRAINT credential_unique_name_per_project;
                            END IF;
                        END;
                        $$;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="credential",
                    name="credential_unique_name_per_project",
                ),
            ],
        ),

        # 2. Drop old index (project, deleted_at) — ignore if missing
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        DO $$
                        BEGIN
                            IF EXISTS (
                                SELECT 1 FROM pg_indexes
                                WHERE indexname = 'credential_project_deleted_idx'
                            ) THEN
                                DROP INDEX credential_project_deleted_idx;
                            END IF;
                        END;
                        $$;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveIndex(
                    model_name="credential",
                    name="credential_project_deleted_idx",
                ),
            ],
        ),

        # 3. Remove Credential.project FK
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        DO $$
                        BEGIN
                            IF EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'credential' AND column_name = 'project_id'
                            ) THEN
                                ALTER TABLE credential DROP COLUMN project_id CASCADE;
                            END IF;
                        END;
                        $$;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name="credential",
                    name="project",
                ),
            ],
        ),

        # 4. Remove Credential.type FK — add type_key CharField
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        DO $$
                        BEGIN
                            -- Add type_key if it doesn't exist yet
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'credential' AND column_name = 'type_key'
                            ) THEN
                                ALTER TABLE credential ADD COLUMN type_key VARCHAR(40) NOT NULL DEFAULT '';
                            END IF;

                            -- Copy key from credential_type if type_id exists
                            IF EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'credential' AND column_name = 'type_id'
                            ) AND EXISTS (
                                SELECT 1 FROM information_schema.tables
                                WHERE table_name = 'credential_type'
                            ) THEN
                                UPDATE credential c
                                SET type_key = ct.key
                                FROM credential_type ct
                                WHERE c.type_id = ct.id AND c.type_key = '';
                            END IF;

                            -- Drop type_id FK column
                            IF EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'credential' AND column_name = 'type_id'
                            ) THEN
                                ALTER TABLE credential DROP COLUMN type_id CASCADE;
                            END IF;
                        END;
                        $$;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name="credential",
                    name="type",
                ),
                migrations.AddField(
                    model_name="credential",
                    name="type_key",
                    field=models.CharField(max_length=40, verbose_name="type key"),
                ),
            ],
        ),

        # 5. Make owner NOT NULL (it was nullable in v1)
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        DO $$
                        BEGIN
                            IF EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'credential'
                                  AND column_name = 'owner_id'
                                  AND is_nullable = 'YES'
                            ) THEN
                                -- Remove orphaned rows without owner
                                DELETE FROM credential WHERE owner_id IS NULL;
                                ALTER TABLE credential ALTER COLUMN owner_id SET NOT NULL;
                            END IF;
                        END;
                        $$;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="credential",
                    name="owner",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="credentials",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="owner",
                    ),
                ),
            ],
        ),

        # 6. Add new unique constraint (owner, name) WHERE deleted_at IS NULL
        migrations.AddConstraint(
            model_name="credential",
            constraint=models.UniqueConstraint(
                fields=["owner", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="credential_unique_name_per_owner",
            ),
        ),

        # 7. Add new index (owner, deleted_at)
        migrations.AddIndex(
            model_name="credential",
            index=models.Index(fields=["owner", "deleted_at"], name="credential_owner_deleted_idx"),
        ),

        # 8. Drop CredentialType table (safe: check existence)
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        DO $$
                        BEGIN
                            IF EXISTS (
                                SELECT 1 FROM information_schema.tables
                                WHERE table_name = 'credential_type'
                            ) THEN
                                DROP TABLE credential_type CASCADE;
                            END IF;
                        END;
                        $$;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.DeleteModel(
                    name="CredentialType",
                ),
            ],
        ),
    ]
