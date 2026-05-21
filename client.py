import urllib.request
import urllib.error
import json
import sys
import os
import argparse

URL_SAVE_FILE = os.path.join(os.path.dirname(__file__), ".jarvis_url")

def load_saved_url():
    if os.path.exists(URL_SAVE_FILE):
        with open(URL_SAVE_FILE, "r") as f:
            return f.read().strip()
    return None

def save_url(url):
    with open(URL_SAVE_FILE, "w") as f:
        f.write(url)

def ask_jarvis(url, query):
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        f"{url}/ask",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            result = json.loads(r.read())
            return result.get("answer", "No answer returned.")
    except urllib.error.URLError as e:
        return f"[Connection Error] Could not reach JARVIS: {e.reason}"
    except Exception as e:
        return f"[Error] {e}"

parser = argparse.ArgumentParser(description="JARVIS VS Code Client")
parser.add_argument("--save-url", metavar="URL", help="Save a new ngrok URL and connect")
parser.add_argument("--reset-url", action="store_true", help="Forget the saved URL and enter a new one")
args = parser.parse_args()

if args.reset_url and os.path.exists(URL_SAVE_FILE):
    os.remove(URL_SAVE_FILE)
    print("Saved URL cleared.\n")

if args.save_url:
    jarvis_url = args.save_url.strip().rstrip("/")
    save_url(jarvis_url)
    print(f"URL saved: {jarvis_url}\n")
else:
    jarvis_url = load_saved_url()
    if jarvis_url:
        print(f"Using saved URL: {jarvis_url}")
        print("(Run with --reset-url to change it)\n")
    else:
        jarvis_url = input("Paste your ngrok URL (e.g. https://abc123.ngrok.io): ").strip().rstrip("/")
        save_url(jarvis_url)
        print(f"URL saved for next time.\n")

print("="*50)
print("  JARVIS - VS Code Client")
print("  Type 'exit' or 'quit' to stop")
print("="*50 + "\n")

while True:
    try:
        user_input = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nJARVIS: Goodbye!")
        break

    if not user_input:
        continue

    if user_input.lower() in ["exit", "quit"]:
        print("JARVIS: Goodbye!")
        break

    print("JARVIS: Thinking...", end="\r")
    answer = ask_jarvis(jarvis_url, user_input)
    print(f"JARVIS: {answer}\n")
