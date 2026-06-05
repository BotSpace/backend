from rest_framework import exceptions, status


class RunningBotLimitExceeded(exceptions.APIException):
    """HTTP 409 — foydalanuvchi bir vaqtda ishlatishi mumkin bo'lgan running botlar sonini oshirdi."""

    status_code = status.HTTP_409_CONFLICT
    default_code = "running_bot_limit"
    default_detail = "Bir vaqtda ko'pi bilan {limit} ta bot ishlatish mumkin. Birini to'xtatib qayta urinib ko'ring."

    def __init__(self, limit: int, running: list[dict]) -> None:
        msg = self.default_detail.format(limit=limit)
        # DRF APIException.detail must be set for drf_default_handler to produce
        # a proper Response.  We pass a plain string so ErrorDetail wraps it.
        super().__init__(detail=msg)
        self.limit = limit
        self.running = running
