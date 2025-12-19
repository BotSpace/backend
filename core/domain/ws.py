from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from core.apps.api.enums import ContainerStatusEnum


class EventTypes(Enum):
    DEBUG_STATUS = "debug_status"
    RELEASE_STATUS = "release_status"


class DebugContainerStatus(BaseModel):
    project: int
    status: ContainerStatusEnum
    service_id: Optional[str]

    updated_at: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class ReleaseContainerStatus(BaseModel):
    project: int
    status: ContainerStatusEnum
    version: int
    service_id: Optional[str]

    model_config = ConfigDict(use_enum_values=True)


class WsEvents(BaseModel):
    event: EventTypes
    data: Any

    model_config = ConfigDict(use_enum_values=True)
