from django.http import StreamingHttpResponse

from core.apps.api.services.docker_service import service_logs_async


async def logs(request, service_id):
    async def stream():
        async for line in service_logs_async(service_id):
            if not line:
                continue
            if line.endswith("\n"):
                line = line[:-1]
            if not line:
                continue
            yield f"data: {line}\n\n"

        yield "data: Container is not running\n\n"

    response = StreamingHttpResponse(stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Origin, X-Requested-With, Content-Type, Accept, Authorization"
    response["Access-Control-Allow-Credentials"] = "false"
    return response
