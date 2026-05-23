"""MongoDB-related service contracts.

These Protocols describe the inter-app boundary. The concrete
implementations live in ``core.apps.cms_legacy.services.mongo`` (
``MongoDBClient``, ``MongoRepository``) — that module is the only
place that may import ``pymongo`` directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Protocol


@dataclass(frozen=True)
class MongoCredentials:
    username: str
    password: str
    database: str
    connection_string: str


class MongoCredentialsService(Protocol):
    """Owns per-project MongoDB credentials and lifecycle."""

    def get_or_create(self, project_id: int) -> MongoCredentials:
        ...

    def rotate(self, project_id: int) -> MongoCredentials:
        ...

    def revoke(self, project_id: int) -> None:
        ...


class MongoRepository(Protocol):
    """Thin repository over a Mongo collection.

    Matches the public API of
    ``core.apps.cms_legacy.services.mongo.MongoRepository``.
    """

    def count(self, where: Mapping[str, Any]) -> int:
        ...

    def find_one(self, where: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
        ...

    def find(
        self,
        where: Optional[Mapping[str, Any]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        sort: Optional[List[Any]] = None,
    ) -> List[Mapping[str, Any]]:
        ...

    def insert_one(self, data: Mapping[str, Any]) -> str:
        ...

    def update(self, where: Mapping[str, Any], data: Mapping[str, Any]) -> Any:
        ...

    def delete(self, where: Mapping[str, Any]) -> Any:
        ...
