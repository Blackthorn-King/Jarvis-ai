import urllib.request
import urllib.error
import json
import sys

JARVIS_URL = input("Paste your ngrok URL (e.g. https://abc123.ngrok.io): ").strip().rstrip("/")

print("\n" + "="*50)
print("  JARVIS - VS Code Client")
print("  Connected to:", JARVIS_URL)
print("  Type 'exit' or 'quit' to stop")
print("="*50 + "\n")

def ask_jarvis(query):
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        f"{JARVIS_URL}/ask",
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
    answer = ask_jarvis(user_input)
    print(f"JARVIS: {answer}\n")
