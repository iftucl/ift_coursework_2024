import os
import dotenv

dotenv.load_dotenv(override=True)

#print all the environment variables
for key, value in os.environ.items():
    print(f"{key}: {value}")