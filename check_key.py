import os
import sys
from dotenv import load_dotenv

load_dotenv()

API_KEY = sys.argv[1] if len(sys.argv) > 1 else os.getenv("GEMINI_API_KEY", "AIzaSyClvKaJh3JzeIZX_f6kpzZHSEI65_wq7lo").strip()

if not API_KEY:
    print("❌ No API key found. Pass it as argument or set GEMINI_API_KEY in .env")
    sys.exit(1)

print(f"🔑 Key prefix : {API_KEY[:10]}...")
print(f"📏 Key length : {len(API_KEY)}")
print("⏳ Testing against Gemini API...\n")

try:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY, http_options={"api_version": "v1alpha"})
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say the word OK and nothing else.",
        config=types.GenerateContentConfig(temperature=0),
    )
    print(f"✅ Key is VALID")
    print(f"📝 Model response: {response.text.strip()}")

except Exception as e:
    err = str(e)
    print(f"❌ Key is INVALID or not working")
    print(f"🔍 Error: {err}")

    if "ACCESS_TOKEN_TYPE_UNSUPPORTED" in err or "401" in err:
        print("\n⚠️  This is the known AQ. key auth bug on Google's side.")
        print("   Try a different Google account or wait for Google to fix it.")
    elif "429" in err or "RESOURCE_EXHAUSTED" in err:
        print("\n⚠️  Key is valid but quota is exhausted.")
        print("   Wait a bit or check your quota at: https://ai.dev/rate-limit")
    elif "403" in err:
        print("\n⚠️  Key exists but doesn't have Gemini API access.")
        print("   Enable the Gemini API at: https://aistudio.google.com/app/apikey")
    elif "404" in err:
        print("\n⚠️  Model not found. The model name may be wrong.")
