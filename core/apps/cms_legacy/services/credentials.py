"""Per-project MongoDB credentials service.

Concrete implementation of
:class:`core.contracts.mongo.MongoCredentialsService`. Lives in the
``cms`` app because it owns the MongoDB integration; other apps
should depend on the Protocol, not on this module directly.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction

from core.contracts.mongo import MongoCredentials

logger = logging.getLogger(__name__)


class ProjectMongoCredentialsService:
    """Creates, fetches, and rotates project-scoped MongoDB users."""

    def __init__(self, mongo_client: Optional["MongoDBClient"] = None) -> None:  # noqa: F821
        from core.apps.cms_legacy.services.mongo import MongoDBClient

        self._mongo_client_factory = mongo_client or MongoDBClient

    def _new_client(self):
        if callable(self._mongo_client_factory):
            return self._mongo_client_factory()
        return self._mongo_client_factory

    @transaction.atomic
    def get_or_create(self, project_id: int) -> MongoCredentials:
        from core.apps.api.models import ProjectModel

        project = ProjectModel.objects.select_for_update().get(pk=project_id)
        if project.mongo_username and project.mongo_password and project.mongo_database:
            client = self._new_client()
            try:
                conn = client._build_connection_string(
                    project.mongo_username, project.mongo_password, project.mongo_database
                )
            finally:
                client.close()
            return MongoCredentials(
                username=project.mongo_username,
                password=project.mongo_password,
                database=project.mongo_database,
                connection_string=conn,
            )
        return self._create(project_id)

    def rotate(self, project_id: int) -> MongoCredentials:
        return self._create(project_id)

    def revoke(self, project_id: int) -> None:
        client = self._new_client()
        try:
            client.delete_project_user(project_id)
        finally:
            client.close()

    def _create(self, project_id: int) -> MongoCredentials:
        from core.apps.api.models import ProjectModel

        client = self._new_client()
        try:
            data = client.create_project_user(project_id)
        finally:
            client.close()

        ProjectModel.objects.filter(pk=project_id).update(
            mongo_username=data["username"],
            mongo_password=data["password"],
            mongo_database=data["database"],
        )
        logger.info("MongoDB credentials provisioned for project %s", project_id)
        return MongoCredentials(
            username=data["username"],
            password=data["password"],
            database=data["database"],
            connection_string=data["connection_string"],
        )


project_mongo_credentials = ProjectMongoCredentialsService()
