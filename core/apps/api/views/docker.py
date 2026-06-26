import asyncio

from django.http import StreamingHttpResponse

from core.apps.api.services.docker_service import service_logs_async

# Seconds of log silence after which we emit an SSE keepalive comment so idle
# proxies (and the browser EventSource) don't close the connection — that idle
# close was causing the "log viewer drops & reconnects every few seconds" loop.
_KEEPALIVE_SECONDS = 15


async def logs(request, service_id):
    async def stream():
        queue: asyncio.Queue = asyncio.Queue()

        async def reader():
            # Owns the underlying k8s log stream and pushes lines into the queue.
            # Kept in its own task so the keepalive timeout below never cancels a
            # mid-flight read (which could corrupt the stream).
            try:
                async for line in service_logs_async(service_id):
                    await queue.put(("log", line))
            except Exception:  # noqa: BLE001 — stream ended/errored; signal end
                pass
            finally:
                await queue.put(("end", None))

        task = asyncio.create_task(reader())
        try:
            while True:
                try:
                    kind, line = await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    # No new log within the window — keep the connection alive.
                    yield ": keepalive\n\n"
                    continue
                if kind == "end":
                    break
                if line and line.endswith("\n"):
                    line = line[:-1]
                if not line:
                    continue
                yield f"data: {line}\n\n"
        finally:
            task.cancel()

        yield "data: Container is not running\n\n"

    response = StreamingHttpResponse(stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Origin, X-Requested-With, Content-Type, Accept, Authorization"
    response["Access-Control-Allow-Credentials"] = "false"
    return response
