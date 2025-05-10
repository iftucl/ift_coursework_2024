import pytest
from unittest.mock import MagicMock, patch
from coursework_two.modules.storage.mongostore import save_indicators_to_mongo, reset_indicators_collection, initialize_indicators_database


@patch.dict("coursework_two.modules.storage.mongostore.THEMATIC_MAPPING", {
    "Scope 1 Emissions": "Greenhouse Gas Emissions",
    "Scope 2 Emissions": "Greenhouse Gas Emissions",
})



@pytest.fixture
def mock_collection():
    with patch("coursework_two.modules.storage.mongostore.initialize_indicators_database") as mock:
        mock_coll = MagicMock()
        mock_coll.name = "sustainability_indicators"
        mock.return_value = mock_coll
        yield mock_coll

def test_reset_indicators_collection(mock_collection):
    mock_collection.delete_many.return_value.deleted_count = 5

    reset_indicators_collection()

    mock_collection.delete_many.assert_called_once_with({})

