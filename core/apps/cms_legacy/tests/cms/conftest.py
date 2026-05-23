from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture(autouse=True)
def patch_mongo():
    """Patch MongoDB repository methods for testing
    
    This fixture mocks the MongoRepository methods that are called
    by ActionService, allowing tests to run without actual MongoDB.
    """
    with patch("core.apps.cms_legacy.services.mongo.MongoRepository.insert_one") as mock_insert_one, \
         patch("core.apps.cms_legacy.services.mongo.MongoRepository.find") as mock_find, \
         patch("core.apps.cms_legacy.services.mongo.MongoRepository.find_one") as mock_find_one, \
         patch("core.apps.cms_legacy.services.mongo.MongoRepository.update") as mock_update, \
         patch("core.apps.cms_legacy.services.mongo.MongoRepository.delete") as mock_delete, \
         patch("core.apps.cms_legacy.services.mongo.MongoRepository.count") as mock_count:

        # Setup mock return values
        mock_insert_one.return_value = "mock_id_123"
        
        mock_find_one.return_value = {"name": "Samandar", "_id": "mock_id"}
        
        mock_find.return_value = [{"name": "Samandar", "_id": "mock_id"}]
        
        mock_update_result = MagicMock()
        mock_update_result.modified_count = 10
        mock_update.return_value = mock_update_result
        
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 10
        mock_delete.return_value = mock_delete_result
        
        mock_count.return_value = 5
        
        yield
