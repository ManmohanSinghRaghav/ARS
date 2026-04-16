import google.generativeai as genai
import os
from app.config import get_settings

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)

print("Listing available generation models:")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"GEN: {m.name}")
        if 'embedContent' in m.supported_generation_methods:
            print(f"EMB: {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
