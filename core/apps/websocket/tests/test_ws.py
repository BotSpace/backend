from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.websocket.services.events import ws_publish
from core.domain.ws import DebugContainerStatus, EventTypes


def test_ws_publish():
    ws_publish(
        user_id="1",
        schema=DebugContainerStatus(project=1, status=ContainerStatusEnum.RUNNING, service_id="1111"),
        event=EventTypes.DEBUG_STATUS,
    )
