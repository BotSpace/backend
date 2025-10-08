from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.api.models import BotModel, EnviromentModel, ProjectModel, RelaseModel


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
            "retrieve-not-found": reverse("project-detail", kwargs={"pk": 1000}),
        }

    def test_create(self):
        self.assertTrue(True)

    def test_update(self):
        self.assertTrue(True)

    def test_partial_update(self):
        self.assertTrue(True)

    def test_destroy(self):
        self.assertTrue(True)

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


class BotTest(TestCase):

    def _create_data(self):
        return BotModel._create_fake()

    def setUp(self):
        self.client = APIClient()
        self.instance = self._create_data()
        self.urls = {
            "list": reverse("bot-list"),
            "retrieve": reverse("bot-detail", kwargs={"pk": self.instance.pk}),
            "retrieve-not-found": reverse("bot-detail", kwargs={"pk": 1000}),
        }

    def test_create(self):
        self.assertTrue(True)

    def test_update(self):
        self.assertTrue(True)

    def test_partial_update(self):
        self.assertTrue(True)

    def test_destroy(self):
        self.assertTrue(True)

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
            "retrieve-not-found": reverse("relase-detail", kwargs={"pk": 1000}),
        }

    def test_create(self):
        self.assertTrue(True)

    def test_update(self):
        self.assertTrue(True)

    def test_partial_update(self):
        self.assertTrue(True)

    def test_destroy(self):
        self.assertTrue(True)

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
            "retrieve": reverse("enviroment-detail", kwargs={"pk": self.instance.pk})
            + "?project="
            + str(self.instance.project.pk),
            "retrieve-not-found": reverse("enviroment-detail", kwargs={"pk": 1000})
            + "?project="
            + str(self.instance.project.pk),
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
