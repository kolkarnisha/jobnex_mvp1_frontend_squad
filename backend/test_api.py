# import os
# from dotenv import load_dotenv
# from google import genai

# load_dotenv()

# api_key = os.getenv("GEMINI_API_KEY")

# if not api_key:
#     raise ValueError("GEMINI_API_KEY was not found in .env")

# client = genai.Client(api_key=api_key)

# response = client.models.generate_content(
#     model="gemini-3.0-flash","gemini-2.5-flash","gemini-2.0-flash","gemini-1.5-flash",

#     contents="Reply with exactly: Gemini API connection successful")

# print(response.text)


# import os
# import time
# from dotenv import load_dotenv
# from google import genai

# load_dotenv()

# api_key = os.getenv("GEMINI_API_KEY")
# if not api_key:
#     raise ValueError("GEMINI_API_KEY was not found in .env")

# client = genai.Client(api_key=api_key)

# def call_gemini(model, contents, retries=5, delay=5):
#     for attempt in range(retries):
#         try:
#             response = client.models.generate_content(
#                 model=model,
#                 contents=contents
#             )
#             return response.text
#         except Exception as e:
#             print(f"Attempt {attempt+1} failed → {e}")
#             time.sleep(delay * (attempt+1))  # exponential backoff
#     raise RuntimeError("Gemini API unavailable after retries")

# # Use the latest supported model
# print(call_gemini("gemini-3.8-flash", "Reply with exactly: Gemini API connection successful"))


#test_api.py
import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="Reply with exactly: Gemini API connection successful"
)

print(response.text)