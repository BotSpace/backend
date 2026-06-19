from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from core.apps.api.enums import ContainerStatusEnum


class EventTypes(Enum):
    DEBUG_STATUS = "debug_status"
    RELEASE_STATUS = "release_status"
    NODE_EXECUTION = "node_execution"
    CONTEXT_SNAPSHOT = "context"


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


class NodeExecutionStatus(BaseModel):
    project: int
    chat_id: int
    node_id: str
    node_type: Optional[str] = None
    status: str  # running | success | error
    error: Optional[str] = None
    ts: Optional[int] = None
    # Engine 3.5.31+: run_id — har Telegram update uchun monotonik; seq — global
    # atomik hisoblagich. Frontend eventlarni tarmoq tartibiga emas, shu raqamlarga
    # qarab tartiblaydi. Eski engine'lar yubormaydi (None) — frontend ts fallback.
    run_id: Optional[int] = None
    seq: Optional[int] = None

    model_config = ConfigDict(use_enum_values=True)


class ContextSnapshot(BaseModel):
    """Engine debug rejimda yuboradigan flow context (o'zgaruvchilar) snapshot'i."""

    project: int
    chat_id: int
    variables: Any  # dict — engine har xil tuzilma yuborishi mumkin
    ts: Optional[int] = None


class WsEvents(BaseModel):
    event: EventTypes
    data: Any

    model_config = ConfigDict(use_enum_values=True)
