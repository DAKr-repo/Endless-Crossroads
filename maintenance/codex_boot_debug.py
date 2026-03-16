import os
import sys
from pathlib import Path

CODEX_DIR = Path(__file__).resolve().parent

print("--- DIAGNOSTICS START ---")

# 1. Check Imports
try:
    print("[1/4] Checking Libraries...", end=" ")
    import discord
    from dotenv import load_dotenv
    print("OK")
except ImportError as e:
    print(f"FAIL: {e}")
    sys.exit(1)

# 2. Check Environment File
print("[2/4] Loading .env...", end=" ")
env_path = CODEX_DIR / ".env"
load_dotenv(env_path)
token = os.getenv("DISCORD_TOKEN")

if env_path.exists():
    print("File Found.")
else:
    print(f"WARNING: .env file NOT found at {env_path}")

# 3. Check Token
print(f"[3/4] Verifying Token...", end=" ")
if token:
    print(f"OK (Length: {len(token)})")
else:
    print("FAIL! DISCORD_TOKEN is missing or empty.")
    print("ACTION: Create a .env file with: DISCORD_TOKEN=your_token_here")
    sys.exit(1)

# 4. Check Internal Modules
print("[4/4] Checking Internal Modules...", end=" ")
try:
    from codex_architect import Complexity
    from codex_cortex import Cortex
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)

print("--- DIAGNOSTICS PASS ---")
print("Attempting manual bot login (Ctrl+C to stop)...")

# 5. Live Connection Test
import asyncio
class TestBot(discord.Client):
    async def on_ready(self):
        print(f"SUCCESS! Logged in as {self.user}")
        await self.close()

try:
    client = TestBot(intents=discord.Intents.default())
    client.run(token)
except Exception as e:
    print(f"LOGIN ERROR: {e}")
