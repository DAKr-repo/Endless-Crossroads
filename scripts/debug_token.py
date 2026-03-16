import os
from pathlib import Path
from dotenv import load_dotenv

CODEX_DIR = Path(__file__).resolve().parent
load_dotenv(CODEX_DIR / ".env")

token = os.getenv("DISCORD_TOKEN")

if not token:
    print("❌ ERROR: No token found. The variable is empty.")
else:
    print(f"✅ Token Found!")
    print(f"   Length: {len(token)} characters")
    print(f"   Starts with: '{token[:5]}...'")
    print(f"   Contains spaces? {'YES (Bad!)' if ' ' in token else 'No'}")
    
    # Check if it looks like a Client Secret (usually 32 chars) vs a Bot Token (usually ~70+ chars)
    if len(token) < 50:
        print("⚠️ WARNING: This looks too short to be a Bot Token.")
        print("   Did you copy the 'Client Secret' instead?")
