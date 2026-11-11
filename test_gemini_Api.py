import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

response = client.models.generate_content(
    model=MODEL,
    contents="You are a game master. Describe a locked library in two sentences."
)
print(response.text)