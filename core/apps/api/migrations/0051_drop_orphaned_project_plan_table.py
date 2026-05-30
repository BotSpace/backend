"""Physically drop the orphaned `project_plan` table.

ProjectPlanModel was removed from Django's STATE in migration 0049
(SeparateDatabaseAndState with empty database_operations), but the
actual `project_plan` table — and its FK to `plan(id)` — were never
dropped from the database. That dangling FK blocks deleting any plan
(IntegrityError: still referenced from table "project_plan").

CASCADE also removes the FK constraint. IF EXISTS keeps the migration
idempotent / safe on databases where the table is already gone.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0050_remove_plan_project_era_fields"),
    ]

    operations = [
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS "project_plan" CASCADE;',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
