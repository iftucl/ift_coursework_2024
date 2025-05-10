import pytest
from pymongo import MongoClient
from fastapi.testclient import TestClient
from fast_api.app import app
from mongo_db.company_data import CompanyData
import os
from io import BytesIO


@pytest.fixture
def test_client():
    """Test client fixture for FastAPI application"""
    client = TestClient(app)
    return client

@pytest.fixture
def mock_pdf_data():
    """Mock PDF data fixture"""
    return BytesIO(b"Mock PDF data for testing")

@pytest.fixture
def mock_company_data():
    """Mock company data fixture"""
    return CompanyData(
        symbol="TEST",
        security="Test Company",
        gics_sector="Technology",
        gics_industry="Software",
        country="US",
        region="North America",
        website_url="https://example.com",
        csr_reports={"2022": "https://example.com/csr/2022.pdf"}
    )

@pytest.fixture
def mongo_db():
    """Mock MongoDB connection fixture"""
    return MockMongo()  # Create a mock MongoDB object

'''
@pytest.fixture
def mongo_db():
    """Temporary MongoDB connection fixture"""
    mongo_uri = os.getenv("TEST_MONGO_URI", "mongodb://localhost:27018")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=1000)
    
    # Create temporary test database
    db = client["test_db"]
    
    # Initialize test collection
    db.companies.delete_many({})
    
    yield db
    
    # Clean up after test completion
    client.drop_database("test_db")
    client.close() 
'''

class MockMongo:
    """Mock MongoDB database"""
    def __init__(self):
        self.collections = {}
        self.companies = MockCollection("companies")
    
    def __getitem__(self, collection_name):
        if collection_name not in self.collections:
            self.collections[collection_name] = MockCollection(collection_name)
        return self.collections[collection_name]

class MockCollection:
    """Mock MongoDB collection"""
    def __init__(self, name):
        self.name = name
        self.documents = []
    
    def find_one(self, query, projection=None):
        for doc in self.documents:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None
    
    def insert_one(self, document):
        self.documents.append(document)
        return MockResult(1)
    
    def delete_many(self, query):
        old_count = len(self.documents)
        self.documents = [d for d in self.documents if not all(d.get(k) == v for k, v in query.items())]
        return MockResult(old_count - len(self.documents))

class MockResult:
    """Mock MongoDB operation result"""
    def __init__(self, count):
        self.modified_count = count
        self.deleted_count = count

