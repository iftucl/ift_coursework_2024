import os
from dotenv import load_dotenv
from openai import OpenAI
import yaml

# Load .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

# Setup DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# Load Mongo config
config_path = os.getenv("CONF_PATH", "coursework_one/a_pipeline/config/conf.yaml")
with open(config_path, "r") as file:
    config = yaml.safe_load(file)

mongo_config = config["databasedocker"] if os.getenv("DOCKER_ENV") else config["databaselocal"]
