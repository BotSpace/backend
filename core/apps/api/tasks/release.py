import logging

from celery import shared_task
from kubernetes import client

from core.apps.api.enums.container import ContainerStatusEnum

logger = logging.getLogger(__name__)

# CrashLoopBackOff va shunga o'xshash holatlarda restart soni shu chegaradan oshsa
# deployment "haqiqatan yiqilgan" hisoblanadi va tozalanadi.
CRASH_RESTART_THRESHOLD = 5

# Ushbu waiting.reason qiymatlari container ishga tushishdan doimiy rad etayotganini bildiradi.
FAILED_WAITING_REASONS = frozenset(
    [
        "CrashLoopBackOff",
        "Error",
        "RunContainerError",
        "ImagePullBackOff",
        "ErrImagePull",
    ]
)


def _is_crashlooping(pod) -> bool:
    """Pod haqiqatan yiqilganmi yoki yo'qligini tekshiradi.

    container_statuses ichida kamida bitta container:
      - waiting.reason FAILED_WAITING_REASONS ichida bo'lishi VA
      - restart_count >= CRASH_RESTART_THRESHOLD
    bo'lsa True qaytaradi.
    """
    statuses = pod.status.container_statuses or []
    for cs in statuses:
        restart_count = cs.restart_count or 0
        if restart_count < CRASH_RESTART_THRESHOLD:
            continue
        waiting = cs.state and cs.state.waiting
        if waiting and waiting.reason in FAILED_WAITING_REASONS:
            return True
    return False


@shared_task
def cleanup_failed_releases():
    """CrashLoop/error holatidagi release deployment'larni Kubernetes'dan o'chiradi.

    - Namespace'dagi barcha botmother-engine podlarini ko'rib chiqadi.
    - Faqat engine-name "release-" bilan boshlanadigan podlar tekshiriladi.
    - CRASH_RESTART_THRESHOLD marta restart bo'lib yiqilgan podlar uchun:
        1. K8s deployment + unga tegishli secret/configmap/service o'chiriladi.
        2. DB'dagi RelaseModel.status = FAILED ga o'zgartiriladi (record saqlanadi).
    - Har bir release alohida try/except: bittasi xato bersa boshqalari davom etadi.

    Returns:
        int: Tozalangan (o'chirilgan) release soni.
    """
    from core.apps.api.models.project import RelaseModel
    from core.apps.api.services.kubernetes_service import (
        get_k8s_client,
        get_namespace,
        remove_deployment,
    )

    try:
        get_k8s_client()
    except Exception as exc:
        logger.error("cleanup_failed_releases: k8s client error: %s", exc)
        return 0

    namespace = get_namespace()
    core_api = client.CoreV1Api()

    try:
        pods = core_api.list_namespaced_pod(
            namespace=namespace,
            label_selector="app=botmother-engine",
        )
    except Exception as exc:
        logger.error("cleanup_failed_releases: list pods error: %s", exc)
        return 0

    # engine-name'ini bir karra aniqlangan podlar seti — bitta deployment bir nechta
    # pod chiqarishi mumkin, lekin biz deployment nomini bir marta o'chiramiz.
    processed: set[str] = set()
    cleaned = 0

    for pod in pods.items:
        labels = pod.metadata.labels or {}
        engine_name = labels.get("engine-name", "")

        if not engine_name.startswith("release-"):
            continue
        if engine_name in processed:
            continue

        if not _is_crashlooping(pod):
            continue

        processed.add(engine_name)
        logger.warning(
            "cleanup_failed_releases: crashloop detected engine_name=%s pod=%s",
            engine_name,
            pod.metadata.name,
        )

        # 1. K8s deployment va unga bog'liq resurslarni o'chir.
        try:
            removed = remove_deployment(engine_name)
            if not removed:
                logger.error(
                    "cleanup_failed_releases: remove_deployment returned False for %s",
                    engine_name,
                )
        except Exception as exc:
            logger.error(
                "cleanup_failed_releases: remove_deployment failed engine_name=%s err=%s",
                engine_name,
                exc,
            )
            # Davom et — DB holatini baribir yangilaymiz.

        # 2. DB record status'ini FAILED ga o'zgartir (o'chirmaydi).
        try:
            updated = RelaseModel.objects.filter(service_id=engine_name).update(
                status=ContainerStatusEnum.FAILED.value
            )
            logger.info(
                "cleanup_failed_releases: DB updated engine_name=%s rows=%d",
                engine_name,
                updated,
            )
        except Exception as exc:
            logger.error(
                "cleanup_failed_releases: DB update failed engine_name=%s err=%s",
                engine_name,
                exc,
            )
            continue

        cleaned += 1

    logger.info("cleanup_failed_releases: total cleaned=%d", cleaned)
    return cleaned
