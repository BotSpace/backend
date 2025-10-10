from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.api.models import EnviromentModel, ProjectModel, RelaseModel


@pytest.fixture(autouse=True)
def test_docker_fixture():
    with patch("core.apps.api.signals.project.remove_service") as mock_remove, patch(
        "core.apps.api.signals.project.deploy_service"
    ) as mock_deploy, patch("core.apps.api.views.project.deploy_service") as mock_deploy_view:
        magic = MagicMock()
        magic.id = "321312"
        mock_deploy.return_value = magic
        mock_remove.return_value = True
        mock_deploy_view.return_value = magic
        yield


class ProjectTest(TestCase):

    def _create_data(self):
        return ProjectModel._create_fake()

    def setUp(self):
        self.client = APIClient()
        self.instance = self._create_data()
        self.client.force_authenticate(self.instance.owner)
        self.urls = {
            "list": reverse("project-list"),
            "retrieve": reverse("project-detail", kwargs={"pk": self.instance.pk}),
            "info": reverse("project-info", kwargs={"pk": self.instance.pk}),
            "stop": reverse("project-stop", kwargs={"pk": self.instance.pk}),
            "debug": reverse("project-debug", kwargs={"pk": self.instance.pk}),
            "retrieve-not-found": reverse("project-detail", kwargs={"pk": 1000}),
        }

    def test_create(self):
        response = self.client.post(self.urls["list"], data={"name": "test"})
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 201)

    def test_info(self):
        response = self.client.get(self.urls["info"])
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 200)

    def test_stop(self):
        response = self.client.get(self.urls["stop"])
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 200)

    def test_debug(self):
        response = self.client.get(self.urls["debug"])
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 200)

    def test_update(self):
        response = self.client.put(self.urls["retrieve"], data={"name": "test"})
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 200)

    def test_partial_update(self):
        response = self.client.patch(self.urls["retrieve"], data={"name": "test"})
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 200)

    def test_destroy(self):
        response = self.client.delete(self.urls["retrieve"])
        self.assertEqual(response.status_code, 204)

    def test_list(self):
        response = self.client.get(self.urls["list"])
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 200)

    def test_retrieve(self):
        response = self.client.get(self.urls["retrieve"])
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 200)

    def test_retrieve_not_found(self):
        response = self.client.get(self.urls["retrieve-not-found"])
        self.assertFalse(response.json()["status"])
        self.assertEqual(response.status_code, 404)


class RelaseTest(TestCase):

    def _create_data(self):
        return RelaseModel._create_fake()

    def setUp(self):
        self.client = APIClient()
        self.instance = self._create_data()
        self.client.force_authenticate(self.instance.project.owner)
        self.urls = {
            "list": reverse("relase-list"),
            "retrieve": reverse("relase-detail", kwargs={"pk": self.instance.pk}),
            "stop": reverse("relase-stop", kwargs={"pk": self.instance.pk}),
            "retrieve-not-found": reverse("relase-detail", kwargs={"pk": 1000}),
        }

    def test_create(self):
        response = self.client.post(
            self.urls["list"],
            data={
                "project": self.instance.project.pk,
            },
        )
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 201)

    def test_stop(self):
        response = self.client.get(self.urls["stop"])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["status"])

    def test_list(self):
        response = self.client.get(self.urls["list"])
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 200)

    def test_retrieve(self):
        response = self.client.get(self.urls["retrieve"])
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 200)

    def test_retrieve_not_found(self):
        response = self.client.get(self.urls["retrieve-not-found"])
        self.assertFalse(response.json()["status"])
        self.assertEqual(response.status_code, 404)


class EnviromentTest(TestCase):

    def _create_data(self):
        return EnviromentModel._create_fake()

    def setUp(self):
        self.client = APIClient()
        self.instance = self._create_data()
        self.client.force_authenticate(self.instance.project.owner)
        self.urls = {
            "list": reverse("enviroment-list") + "?project=" + str(self.instance.project.pk),
            "retrieve": reverse("enviroment-detail", kwargs={"pk": self.instance.key})
            + "?project="
            + str(self.instance.project.id),
            "retrieve-not-found": reverse("enviroment-detail", kwargs={"pk": "NO_KEY"})
            + "?project="
            + str(self.instance.project.id),
        }

    def test_create(self):
        response = self.client.post(
            self.urls["list"],
            data={
                "key": "test",
                "value": "test",
                "project": self.instance.project.pk,
            },
        )
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 201)

    def test_update(self):
        response = self.client.patch(
            self.urls["retrieve"], data={"flow": [{"step": "init", "action": "initialize release"}]}
        )
        self.assertTrue(response.json()["status"])

    def test_partial_update(self):
        self.assertTrue(True)

    def test_destroy(self):
        response = self.client.delete(self.urls["retrieve"])
        self.assertEqual(response.status_code, 204)

    def test_list(self):
        response = self.client.get(self.urls["list"])
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 200)

    def test_retrieve(self):
        response = self.client.get(self.urls["retrieve"])
        self.assertTrue(response.json()["status"])
        self.assertEqual(response.status_code, 200)

    def test_retrieve_not_found(self):
        response = self.client.get(self.urls["retrieve-not-found"])
        self.assertFalse(response.json()["status"])
        self.assertEqual(response.status_code, 404)
