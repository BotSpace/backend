from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict
from core.apps.api.enums import ContainerStatusEnum


class EventTypes(Enum):
    DEBUG_CONTAINER_STATUS = "debug_container_status"
    RELEASE_CONTAINER_STATUS = "release_container_status"


class DebugContainerStatus(BaseModel):
    project: int
    status: ContainerStatusEnum

    model_config = ConfigDict(use_enum_values=True)


class ReleaseContainerStatus(BaseModel):
    project: int
    status: ContainerStatusEnum
    version: str

    model_config = ConfigDict(use_enum_values=True)


class WsEvents(BaseModel):
    event: EventTypes
    data: Any

    model_config = ConfigDict(use_enum_values=True)
