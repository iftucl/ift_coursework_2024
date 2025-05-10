import os
import sys
from unittest.mock import MagicMock

# -- Patch required environment variables for Pydantic Settings --
os.environ["POSTGRES_DRIVER"] = "postgresql"
os.environ["POSTGRES_USERNAME"] = "user"
os.environ["POSTGRES_PASSWORD"] = "pass"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_DB_NAME"] = "mydb"
os.environ["MINIO_USERNAME"] = "user"
os.environ["MINIO_PASSWORD"] = "pass"
os.environ["MINIO_HOST"] = "localhost"
os.environ["MINIO_PORT"] = "9000"
os.environ["MINIO_BUCKET_NAME"] = "bucket"
os.environ["MONGO_URI"] = "mongodb://localhost:27017"
os.environ["MONGO_DB_NAME"] = "csr"
os.environ["MONGO_COLLECTION_NAME"] = "reports"
os.environ["OPENMETADATA_SERVER_URL"] = "http://localhost"
os.environ["OPENMETADATA_AUTH_PROVIDER"] = "no-auth"
os.environ["OPENMETADATA_AUTH_TOKEN"] = "token"
os.environ["LLAMACLOUD_API_KEY"] = "dummy"
os.environ["OPENAI_API_KEY"] = "dummy"

# -- Path setup --
sys.path.insert(0, os.path.abspath('..'))  # Root of coursework_two

# -- Project information --
project = 'Big Data - Coursework 2'
author = 'Dogwood'
release = '1.0'

# -- General configuration --
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # For Google-style docstrings
    'sphinx.ext.viewcode',
]

autodoc_mock_imports = [
    "pymongo",
    "minio",
    "openmetadata",
    "pydantic_settings",
    "llama_cloud",
    "ift_global",
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output --
html_theme = 'alabaster'

# -- Options for LaTeX output --
latex_elements = {}

# -- Source suffix --
source_suffix = '.rst'

# -- Master document --
master_doc = 'index'
