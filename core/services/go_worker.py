"""Go worker (worker-golang) uchun on-demand task producer.

Celery .delay() o'rniga Redis Stream'ga JSON yozadi — worker-golang XREADGROUP
bilan o'qiydi. GO_WORKER_TASKS=false (default) bo'lsa chaqiruv joylari celery'da
qolaveradi; true bo'lsa stream'ga yoziladi. Shu bayroq bilan bosqichma-bosqich
migratsiya qilinadi (avval worker deploy, keyin bayroq).

Kontrakt (worker-golang internal/shared/redisq bilan mos):
    XADD goworker:tasks * payload='{"task":"send_message","args":{"message_id":1}}'
"""

import json
from functools import lru_cache

import redis

from config.env import env

TASK_STREAM = env.str("TASK_STREAM", default="goworker:tasks")


def enabled() -> bool:
    return env.bool("GO_WORKER_TASKS", default=False)


@lru_cache(maxsize=1)
def _conn() -> redis.Redis:
    return redis.Redis.from_url(env.str("REDIS_URL"))


def enqueue(task: str, **args) -> None:
    _conn().xadd(TASK_STREAM, {"payload": json.dumps({"task": task, "args": args})})
