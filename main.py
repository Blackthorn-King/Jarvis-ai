import threading
import subprocess
import re
import os
import json
import time
import sys
import argparse

sys.stdout.reconfigure(line_buffering=True)

# --- Find Ollama executable ---
def find_ollama():
    result = subprocess.run(["which", "ollama"], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    nix_result = subprocess.run(
        "ls /nix/store/*ollama*/bin/ollama 2>/dev/null | sort -V | tail -1",
        shell=True, capture_output=True, text=True
    )
    if nix_result.stdout.strip():
        return nix_result.stdout.strip()
    for path in ["/usr/local/bin/ollama", "/usr/bin/ollama"]:
        if os.path.exists(path):
            return path
    return None

ollama_executable_path = find_ollama()
print("\n--- Checking Ollama installation ---")
if ollama_executable_path:
    print(f"Ollama found at: {ollama_executable_path}")
else:
    print("Ollama not found. Please install it via the package manager.")
    sys.exit(1)

# --- Imports that require installed packages ---
import ollama
from flask import Flask, request, jsonify
from pyngrok import ngrok

# --- JARVIS Core ---
SCRIPT_DIR = os.getcwd()
MEMORY_FILE = os.path.join(SCRIPT_DIR, "jarvis_memory.jsonl")
MODEL = "phi"

SYSTEM_PROMPT = """You are JARVIS, an advanced AI assistant built by Stark Industries.
Be concise, smart, and helpful. Speak like a sophisticated AI assistant.

When the user asks you to perform a computer action, include an ACTION block at the end:
ACTION:{"type":"open","data":"notepad"}   — to open an app or URL
ACTION:{"type":"search","data":"query"}  — to search Google
ACTION:{"type":"type","data":"text"}     — to type text
ACTION:{"type":"click","data":"x,y"}     — to click coordinates

Only include ACTION when the user explicitly asks to DO something on their computer.
"""

# --- Memory ---
def load_memory(max_turns=10):
    if not os.path.exists(MEMORY_FILE):
        return []
    turns = []
    with open(MEMORY_FILE, "r") as f:
        for line in f:
            try:
                turns.append(json.loads(line.strip()))
            except Exception:
                pass
    return turns[-max_turns:]

def save_memory(role, content):
    with open(MEMORY_FILE, "a") as f:
        f.write(json.dumps({"role": role, "content": content}) + "\n")

# --- Parse action from AI response ---
def extract_action(text):
    match = re.search(r'ACTION:\s*(\{.*?\})', text, re.DOTALL)
    if match:
        try:
            action = json.loads(match.group(1))
            clean_text = text[:match.start()].strip()
            return clean_text, action
        except Exception:
            pass
    return text, None

# --- Also parse action from query directly ---
def parse_action_from_query(query):
    q = query.lower().strip()
    if q.startswith("open "):
        return {"type": "open", "data": query[5:].strip()}
    if q.startswith("search "):
        return {"type": "search", "data": query[7:].strip()}
    if q.startswith("go to ") or q.startswith("visit "):
        return {"type": "open", "data": query.split(" ", 2)[-1].strip()}
    if q.startswith("type "):
        return {"type": "type", "data": query[5:].strip()}
    if q.startswith("click ") and "," in query:
        return {"type": "click", "data": query[6:].strip()}
    return None

# --- Core AI function ---
def ask_jarvis_ai(query, image_b64=None):
    history = load_memory()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)

    if image_b64:
        user_content = f"[Screen shared] {query}"
    else:
        user_content = query

    messages.append({"role": "user", "content": user_content})

    try:
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            options={"temperature": 0.3}
        )
        answer = response["message"]["content"]
        save_memory("user", user_content)
        save_memory("assistant", answer)
        return answer
    except Exception as e:
        return f"AI Error: {e}"

# --- Start Ollama and pull phi model ---
print("\n--- Starting Ollama Server ---")
log_file_path = "ollama_server_output.log"

if not os.path.exists(ollama_executable_path):
    print(f"Ollama executable not found at {ollama_executable_path}")
    sys.exit(1)

# Kill any existing Ollama instances
try:
    subprocess.run([ollama_executable_path, "stop"], capture_output=True, timeout=5)
except Exception:
    pass
try:
    pids = subprocess.check_output(
        ["lsof", "-ti", "tcp:11434"], stderr=subprocess.DEVNULL
    ).decode().strip().split('\n')
    pids = [p for p in pids if p]
    if pids:
        subprocess.run(["kill", "-9"] + pids, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except Exception:
    pass

time.sleep(2)

with open(log_file_path, "w") as log_file:
    subprocess.Popen(
        [ollama_executable_path, "serve"],
        stdout=log_file, stderr=log_file,
        preexec_fn=os.setsid
    )

time.sleep(8)
print("Ollama server started.")

# Verify connectivity
server_up = False
for attempt in range(5):
    try:
        client = ollama.Client()
        client.list()
        server_up = True
        print("Ollama server is reachable.")
        break
    except Exception:
        print(f"Waiting for Ollama... ({attempt + 1}/5)")
        time.sleep(4)

if server_up:
    print(f"Pulling '{MODEL}' model...")
    pull_result = subprocess.run(
        [ollama_executable_path, "pull", MODEL],
        capture_output=True, text=True, check=False
    )
    print(pull_result.stdout[-500:] if pull_result.stdout else "")
    print(f"'{MODEL}' model ready.")
else:
    print("Ollama server not reachable — skipping model pull.")

print("Ollama setup complete.")

# --- Flask Server ---
print("\n--- Setting up Flask Server ---")

try:
    pids = subprocess.check_output(
        ["lsof", "-ti", "tcp:5001"], stderr=subprocess.DEVNULL
    ).decode().strip().split('\n')
    pids = [p for p in pids if p]
    if pids:
        subprocess.run(["kill", "-9"] + pids, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except Exception:
    pass

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "JARVIS online", "model": MODEL})

@app.route('/ask', methods=['POST'])
def ask_endpoint():
    data = request.json or {}
    query = data.get('query', '').strip()
    image_b64 = data.get('image')

    if not query:
        return jsonify({'error': 'No query provided'}), 400

    try:
        # Check for direct action command in query
        direct_action = parse_action_from_query(query)

        # Get AI answer
        raw_answer = ask_jarvis_ai(query, image_b64)

        # Check if AI embedded an action in its response
        answer, ai_action = extract_action(raw_answer)

        # Direct action takes priority over AI-parsed action
        action = direct_action or ai_action

        response = {'answer': answer}
        if action:
            response['action'] = action
        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/memory', methods=['GET'])
def get_memory():
    return jsonify(load_memory())

@app.route('/memory/clear', methods=['POST'])
def clear_memory():
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
    return jsonify({'status': 'Memory cleared'})

@app.route('/status', methods=['GET'])
def status():
    try:
        client = ollama.Client()
        models = client.list()
        return jsonify({'status': 'online', 'model': MODEL, 'ollama': 'running'})
    except Exception as e:
        return jsonify({'status': 'degraded', 'error': str(e)})

# --- Chat mode (terminal) ---
def run_chat_mode():
    print("\n" + "="*50)
    print("  JARVIS - Terminal Chat")
    print("  Type 'exit' or 'quit' to stop")
    print("  Type 'clear memory' to reset memory")
    print("="*50 + "\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nJARVIS offline.")
            break
        if not user_input:
            continue
        if user_input.lower() in ['exit', 'quit']:
            print("JARVIS: Goodbye, sir.")
            break
        if user_input.lower() == 'clear memory':
            if os.path.exists(MEMORY_FILE):
                os.remove(MEMORY_FILE)
            print("JARVIS: Memory cleared.")
            continue
        answer = ask_jarvis_ai(user_input)
        clean_answer, action = extract_action(answer)
        print(f"JARVIS: {clean_answer}")
        if action:
            print(f"[ACTION] {action}")

# --- Entry point ---
parser = argparse.ArgumentParser()
parser.add_argument('--chat', action='store_true', help='Run in terminal chat mode')
args, _ = parser.parse_known_args()

if args.chat:
    run_chat_mode()
else:
    # Start ngrok tunnel
    print("\n--- Setting up ngrok Tunnel ---")
    ngrok.kill()
    time.sleep(1)

    ngrok_token = os.environ.get("NGROK_AUTH_TOKEN", "")
    if ngrok_token:
        ngrok.set_auth_token(ngrok_token)
    else:
        print("WARNING: NGROK_AUTH_TOKEN not set.")

    try:
        tunnel = ngrok.connect(5001, bind_tls=True)
        public_url = tunnel.public_url
        print(f"\n{'='*50}")
        print(f"  JARVIS IS ONLINE")
        print(f"  ngrok tunnel: {public_url}")
        print(f"  Set this in your HUD: set url {public_url}")
        print(f"{'='*50}\n")
    except Exception as e:
        print(f"ngrok failed: {e}")
        public_url = "http://localhost:5001"

    # Run Flask
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
