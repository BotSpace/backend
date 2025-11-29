from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture(autouse=True)
def patch_mongo():
    with patch("core.apps.cms.services.action.insert_one") as insert_one_mock, patch(
        "core.apps.cms.services.action.find"
    ) as mock_find, patch("core.apps.cms.services.action.find_one") as mock_find_one, patch(
        "core.apps.cms.services.action.update"
    ) as mock_update, patch(
        "core.apps.cms.services.action.delete"
    ) as mock_delete:

        mock_delete_data = MagicMock()
        mock_delete_data.deleted_count = 10
        mock_delete.return_value = mock_delete_data

        mock_find_one.return_value = {"name": "Samandar"}

        mock_update_data = MagicMock()
        mock_update_data.modified_count = 10
        mock_update.return_value = mock_update_data

        mock_find.return_value = [{"name": "Samandar"}]
        insert_one_mock.return_value = "mock_id"
        yield
