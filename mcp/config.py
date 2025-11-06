# config.py
import os
from dotenv import load_dotenv

# Load .env file into environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = "gemini-2.5-flash"


OPENAI_API_KEY = "your_openai_api_key_here"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL_NAME = "gpt-4o-mini"


LLM_PROVIDER = "gemini"  
LLM_TEMPERATURE = 0.0
LLM_TIMEOUT = 15  # seconds
LLM_MAX_RETRIES = 3
