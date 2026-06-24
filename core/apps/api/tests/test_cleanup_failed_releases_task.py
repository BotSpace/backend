"""
cleanup_failed_releases celery task uchun unit testlar.

Strategiya: kubernetes client va remove_deployment mock qilinadi,
RelaseModel uchun haqiqiy Django ORM (pytest-django + DB) ishlatiladi.
"""

from unittest.mock import MagicMock, patch, call

import pytest

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.tasks.release import (
    CRASH_RESTART_THRESHOLD,
    FAILED_WAITING_REASONS,
    _is_crashlooping,
    cleanup_failed_releases,
)


# ---------------------------------------------------------------------------
# Yordamchi fabrika funksiyalar
# ---------------------------------------------------------------------------


def _make_container_status(restart_count: int, waiting_reason: str | None):
    """kubernetes V1ContainerStatus-ga o'xshash mock."""
    cs = MagicMock()
    cs.restart_count = restart_count
    if waiting_reason:
        cs.state.waiting.reason = waiting_reason
    else:
        cs.state.waiting = None
    return cs


def _make_pod(engine_name: str, container_statuses: list):
    pod = MagicMock()
    pod.metadata.name = f"{engine_name}-abc12"
    pod.metadata.labels = {"app": "botmother-engine", "engine-name": engine_name}
    pod.status.container_statuses = container_statuses
    return pod


# ---------------------------------------------------------------------------
# _is_crashlooping unit testlar (DB shart emas)
# ---------------------------------------------------------------------------


def test_is_crashlooping_true_when_threshold_and_reason():
    cs = _make_container_status(CRASH_RESTART_THRESHOLD, "CrashLoopBackOff")
    pod = _make_pod("release-1-1", [cs])
    assert _is_crashlooping(pod) is True


def test_is_crashlooping_false_below_threshold():
    cs = _make_container_status(CRASH_RESTART_THRESHOLD - 1, "CrashLoopBackOff")
    pod = _make_pod("release-1-1", [cs])
    assert _is_crashlooping(pod) is False


def test_is_crashlooping_false_when_no_waiting_reason():
    cs = _make_container_status(CRASH_RESTART_THRESHOLD + 2, None)
    pod = _make_pod("release-1-1", [cs])
    assert _is_crashlooping(pod) is False


def test_is_crashlooping_false_for_unknown_reason():
    cs = _make_container_status(CRASH_RESTART_THRESHOLD + 2, "OOMKilled")
    pod = _make_pod("release-1-1", [cs])
    assert _is_crashlooping(pod) is False


@pytest.mark.parametrize("reason", sorted(FAILED_WAITING_REASONS))
def test_is_crashlooping_true_for_all_known_reasons(reason):
    cs = _make_container_status(CRASH_RESTART_THRESHOLD, reason)
    pod = _make_pod("release-1-1", [cs])
    assert _is_crashlooping(pod) is True


# ---------------------------------------------------------------------------
# cleanup_failed_releases integration testlar (DB kerak)
# ---------------------------------------------------------------------------


def _patch_k8s(pods):
    """k8s tegishli funksiyalarni mock qiladigan patch kontekst menejeriga"""
    mock_core = MagicMock()
    mock_core.list_namespaced_pod.return_value = MagicMock(items=pods)

    return (
        patch("core.apps.api.tasks.release.get_k8s_client", return_value=MagicMock()),
        patch("core.apps.api.tasks.release.get_namespace", return_value="botmother"),
        patch("kubernetes.client.CoreV1Api", return_value=mock_core),
        patch("core.apps.api.tasks.release.remove_deployment", return_value=True),
    )


@pytest.fixture
def project(db):
    from core.apps.accounts.models import User
    from core.apps.api.models.project import ProjectModel

    user = User.objects.create_user(
        phone="+998901230001",
        username="task_test_user",
        email="task_test@example.com",
        password="pass",
    )
    return ProjectModel.objects.create(name="Task Test Project", owner=user, flow=[])


@pytest.mark.django_db
def test_cleanup_marks_db_failed_and_calls_remove(project):
    """Crashloop pod → remove_deployment chaqiriladi, DB status FAILED bo'ladi."""
    from core.apps.api.models.project import RelaseModel

    engine_name = "release-task-test-1"
    release = RelaseModel.objects.create(
        project=project, version=1, flow=[], service_id=engine_name,
        status=ContainerStatusEnum.RUNNING.value,
    )

    cs = _make_container_status(CRASH_RESTART_THRESHOLD, "CrashLoopBackOff")
    pod = _make_pod(engine_name, [cs])

    patches = _patch_k8s([pod])
    with patches[0], patches[1], patches[2], patches[3] as mock_remove:
        result = cleanup_failed_releases()

    assert result == 1
    mock_remove.assert_called_once_with(engine_name)
    release.refresh_from_db()
    assert release.status == ContainerStatusEnum.FAILED.value


@pytest.mark.django_db
def test_cleanup_skips_non_release_pods(project):
    """debug- prefiksi bilan boshlanadigan pod tozalanmaydi."""
    from core.apps.api.models.project import RelaseModel

    engine_name = "debug-task-test-1"
    RelaseModel.objects.create(
        project=project, version=1, flow=[], service_id=engine_name,
        status=ContainerStatusEnum.RUNNING.value,
    )

    cs = _make_container_status(CRASH_RESTART_THRESHOLD, "CrashLoopBackOff")
    pod = _make_pod(engine_name, [cs])

    patches = _patch_k8s([pod])
    with patches[0], patches[1], patches[2], patches[3] as mock_remove:
        result = cleanup_failed_releases()

    assert result == 0
    mock_remove.assert_not_called()


@pytest.mark.django_db
def test_cleanup_skips_healthy_pod(project):
    """Restart soni past bo'lgan sog'lom pod tozalanmaydi."""
    from core.apps.api.models.project import RelaseModel

    engine_name = "release-task-test-healthy"
    RelaseModel.objects.create(
        project=project, version=1, flow=[], service_id=engine_name,
        status=ContainerStatusEnum.RUNNING.value,
    )

    cs = _make_container_status(1, "CrashLoopBackOff")  # restart_count past
    pod = _make_pod(engine_name, [cs])

    patches = _patch_k8s([pod])
    with patches[0], patches[1], patches[2], patches[3] as mock_remove:
        result = cleanup_failed_releases()

    assert result == 0
    mock_remove.assert_not_called()


@pytest.mark.django_db
def test_cleanup_deduplicates_same_deployment(project):
    """Bitta deployment uchun bir nechta pod bo'lsa faqat bir marta o'chiriladi."""
    from core.apps.api.models.project import RelaseModel

    engine_name = "release-task-test-dup"
    RelaseModel.objects.create(
        project=project, version=1, flow=[], service_id=engine_name,
        status=ContainerStatusEnum.RUNNING.value,
    )

    cs = _make_container_status(CRASH_RESTART_THRESHOLD, "CrashLoopBackOff")
    pod1 = _make_pod(engine_name, [cs])
    pod2 = _make_pod(engine_name, [cs])
    pod2.metadata.name = f"{engine_name}-xyz99"

    patches = _patch_k8s([pod1, pod2])
    with patches[0], patches[1], patches[2], patches[3] as mock_remove:
        result = cleanup_failed_releases()

    assert result == 1
    mock_remove.assert_called_once_with(engine_name)


@pytest.mark.django_db
def test_cleanup_continues_after_single_failure(project):
    """Birinchi release tozalashda xato chiqsa ikkinchisi baribir tozalanadi."""
    from core.apps.api.models.project import RelaseModel

    engine_name_1 = "release-fail-first"
    engine_name_2 = "release-fail-second"

    rel1 = RelaseModel.objects.create(
        project=project, version=1, flow=[], service_id=engine_name_1,
        status=ContainerStatusEnum.RUNNING.value,
    )
    rel2 = RelaseModel.objects.create(
        project=project, version=2, flow=[], service_id=engine_name_2,
        status=ContainerStatusEnum.RUNNING.value,
    )

    cs = _make_container_status(CRASH_RESTART_THRESHOLD, "CrashLoopBackOff")
    pods = [_make_pod(engine_name_1, [cs]), _make_pod(engine_name_2, [cs])]

    def remove_side_effect(name):
        if name == engine_name_1:
            raise RuntimeError("k8s connection lost")
        return True

    patches = _patch_k8s(pods)
    with patches[0], patches[1], patches[2], patches[3] as mock_remove:
        mock_remove.side_effect = remove_side_effect
        result = cleanup_failed_releases()

    # Ikkinchi release tozalangan bo'lishi kerak
    assert result >= 1
    rel2.refresh_from_db()
    assert rel2.status == ContainerStatusEnum.FAILED.value
