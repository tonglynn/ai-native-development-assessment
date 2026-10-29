"""Check the DeepSeek key and model name before spending money on experiments.

Usage (inside the Codespace):
    python scripts/check_model.py

Optional: EM_MODEL=deepseek/<model-id> python scripts/check_model.py
The key is read from the DEEPSEEK_API_KEY environment variable and is never printed.
"""

import os
import sys
import time

import requests
from litellm import completion

key = os.environ.get("DEEPSEEK_API_KEY")
if not key:
    sys.exit(
        "DEEPSEEK_API_KEY is not set.\n"
        "Add it under GitHub Settings -> Codespaces -> Secrets, give this repository access, "
        "then rebuild or restart the codespace."
    )

model = os.environ.get("EM_MODEL", "deepseek/deepseek-flash")

# 1. Which models does this key see?
resp = requests.get(
    "https://api.deepseek.com/models",
    headers={"Authorization": f"Bearer {key}"},
    timeout=20,
)
if not resp.ok:
    sys.exit(f"Listing models failed (HTTP {resp.status_code}): {resp.text[:300]}")
ids = [m["id"] for m in resp.json().get("data", [])]
print("Available models:", ", ".join(ids) or "(none)")

name = model.split("/", 1)[-1]
if name not in ids:
    print(f"WARNING: '{name}' is not in the list. Rerun with EM_MODEL=deepseek/<one of the above>.")

# 2. One tiny real call through litellm, the same path mini-swe-agent uses.
start = time.time()
reply = completion(
    model=model,
    messages=[{"role": "user", "content": "Reply with exactly one word: pong"}],
    max_tokens=300,
)
print("Model:", model)
print("Reply:", (reply.choices[0].message.content or "").strip()[:100])
print("Usage:", reply.usage)
print(f"Latency: {time.time() - start:.1f}s")
