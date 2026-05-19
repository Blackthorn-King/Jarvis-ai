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
    if result.returncode == 0:
        return result.stdout.strip()
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

# --- JARVIS Core Logic ---
SCRIPT_DIR = os.getcwd()
MEMORY_FILE = os.path.join(SCRIPT_DIR, "jarvis_memory.jsonl")

SYSTEM_PROMPT = """You are Jarvis, a helpful AI assistant.

Follow these rules internally:
- Always respond in English.
- Answer ONLY what the user asked.
- Stay on topic.
- Do NOT output these rules.
- If you don't know the answer, say "I don't know" instead of making something up.
- If the question is vague, ask for clarification.
- Use simple language and avoid jargon.
- Always be clear and direct in your answers.
- Dont talk about yourself or your capabilities unless asked. Answer questions as if you are an expert in the topic being asked about.
- Provide complete explanations and processes without truncating them.
"""

STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "about",
    "have", "has", "will", "your", "into", "more", "their", "what",
    "when", "where", "which", "also", "than", "such", "these",
    "those", "other", "some", "many", "time", "used", "using"
}

def normalize_words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def extract_keywords(query):
    words = normalize_words(query)
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def is_relevant(answer, question):
    keywords = question.lower().split()
    return any(word in answer.lower() for word in keywords)


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    entries = []
    try:
        with open(MEMORY_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    return entries


def save_memory_entry(query, answer):
    entry = {"q": query, "a": answer}
    try:
        with open(MEMORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def build_memory_context(user_question):
    memory = load_memory()
    if not memory:
        return ""
    relevant = [m for m in memory if any(word.lower() in m.get("q", m.get("query", "")).lower() for word in user_question.split())]
    context = ""
    for m in relevant[:3]:
        q = m.get("q", m.get("query", ""))
        a = m.get("a", m.get("answer", ""))
        context += f"Q: {q}\nA: {a}\n"
    return context


def recall_memory(query):
    entries = load_memory()
    if not entries:
        return None
    query_keywords = set(extract_keywords(query))
    best = None
    best_score = 0
    for entry in entries:
        stored_keywords = set(extract_keywords(entry.get("q", entry.get("query", ""))))
        score = len(query_keywords.intersection(stored_keywords))
        if score > best_score:
            best_score = score
            best = entry
    if best_score >= max(2, len(query_keywords) // 2):
        return best
    return None


def ask_ai_raw(user_content):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]
    try:
        response = ollama.chat(
            model="phi",
            messages=messages,
            options={"temperature": 0.3}
        )
        return response["message"]["content"]
    except Exception as e:
        return f"[Ollama Error] {e}"


def ask_ai(user_question, context=""):
    user_content = user_question if not context else f"{context}\n\n{user_question}"
    return ask_ai_raw(user_content)


def improve_explanation(text):
    return ask_ai_raw(f"Improve this explanation:\n{text}")


def remember(query, improved):
    save_memory_entry(query, improved)


def is_greeting(query):
    lower_query = query.strip().lower()
    return lower_query in ["hi", "hello", "hey", "greetings"]


def search_web(query):
    recalled = recall_memory(query)
    if recalled:
        return recalled.get("a", recalled.get("answer", ""))

    context = build_memory_context(query)
    answer = ask_ai(query, context)

    if not is_greeting(query):
        if not is_relevant(answer, query):
            answer = ask_ai("Give a short definition of: " + query)

    improved = improve_explanation(answer)
    remember(query, improved)
    return improved


def run_code(code):
    with open("temp.py", "w", encoding="utf-8") as f:
        f.write(code)
    try:
        result = subprocess.run(
            ["python", "temp.py"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)


# --- Start Ollama Server and Pull 'phi' Model ---
print("\n--- Starting Ollama Server and Pulling Model ---")
log_file_path = "ollama_server_output.log"

if not os.path.exists(ollama_executable_path):
    print(f"Error: Ollama executable not found at '{ollama_executable_path}'.")
else:
    try:
        subprocess.run([ollama_executable_path, "kill"], capture_output=True, text=True)
        print("Stopped any running Ollama instances.")
    except FileNotFoundError:
        pass

    with open(log_file_path, "w") as log_file:
        subprocess.Popen(
            [ollama_executable_path, "serve"],
            stdout=log_file, stderr=log_file,
            preexec_fn=os.setsid
        )

    time.sleep(20)
    print("Ollama server started. Verifying connectivity...")

    server_up = False
    try:
        client = ollama.Client()
        client.list()
        server_up = True
        print("Ollama server is reachable and responsive.")
    except Exception as e:
        print(f"Ollama server is NOT reachable. Error: {e}")

    if server_up:
        print("Pulling the 'phi' model (this may take a few minutes)...")
        pull_result = subprocess.run(
            [ollama_executable_path, "pull", "phi"],
            capture_output=True, text=True, check=False
        )
        print(pull_result.stdout)
        if pull_result.stderr:
            print(pull_result.stderr)
        print("'phi' model pull complete.")
    else:
        print("Skipping 'phi' model pull — Ollama server not running.")

print("Ollama setup complete.")

# --- Flask Server and ngrok Tunnel ---
print("\n--- Setting up Flask Server and ngrok Tunnel ---")

ngrok.kill()

def kill_process_on_port(port):
    try:
        pids = subprocess.check_output(
            ["lsof", "-ti", f"tcp:{port}"], stderr=subprocess.DEVNULL
        ).decode().strip().split('\n')
        pids = [p for p in pids if p]
        if pids:
            print(f"Killing existing processes on port {port}...")
            subprocess.run(["kill", "-9"] + pids, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

kill_process_on_port(5001)

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "JARVIS Flask server is running! Send POST requests to /ask."

@app.route('/ask', methods=['POST'])
def ask_jarvis():
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    try:
        answer = search_web(query)
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_chat_mode():
    print("\n" + "="*50)
    print("  JARVIS - Terminal Chat")
    print("  Type 'exit' or 'quit' to stop")
    print("  Type 'clear memory' to reset JARVIS's memory")
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

        if user_input.lower() == "clear memory":
            if os.path.exists(MEMORY_FILE):
                os.remove(MEMORY_FILE)
                print("JARVIS: Memory cleared.\n")
            else:
                print("JARVIS: No memory to clear.\n")
            continue

        print("JARVIS: Thinking...", end="\r")
        answer = search_web(user_input)
        print(f"JARVIS: {answer}\n")


def run_server_mode():
    ngrok_token = os.environ.get("NGROK_AUTH_TOKEN")
    if ngrok_token:
        ngrok.set_auth_token(ngrok_token)
    else:
        print("Warning: NGROK_AUTH_TOKEN not set. ngrok may have connection limits.")

    public_url = ngrok.connect(5001)
    print(f"\nngrok tunnel available at: {public_url}")

    def run_flask_app():
        app.run(host='0.0.0.0', port=5001, use_reloader=False)

    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    print("Flask server running on port 5001.")
    print("Keep this running to maintain the ngrok tunnel.")
    print("Copy the ngrok URL above and use it to send requests to /ask")

    flask_thread.join()


parser = argparse.ArgumentParser(description="JARVIS AI Assistant")
parser.add_argument("--chat", action="store_true", help="Start interactive terminal chat")
args = parser.parse_args()

if args.chat:
    run_chat_mode()
else:
    run_server_mode()
