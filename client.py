import urllib.request
import urllib.error
import json
import sys
import os
import argparse
import subprocess
import webbrowser
import time

# --- Optional: pyautogui for mouse/keyboard control ---
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

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

# --- Computer Control Commands ---
def handle_computer_command(cmd):
    cmd_lower = cmd.lower().strip()

    # OPEN APP
    if cmd_lower.startswith("open "):
        app = cmd[5:].strip()
        try:
            subprocess.Popen(app, shell=True)
            return f"Opening {app}..."
        except Exception as e:
            return f"Could not open {app}: {e}"

    # SEARCH ONLINE
    if cmd_lower.startswith("search "):
        query = cmd[7:].strip()
        webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        return f"Searching Google for: {query}"

    # OPEN WEBSITE
    if cmd_lower.startswith("go to ") or cmd_lower.startswith("visit "):
        site = cmd.split(" ", 2)[-1].strip()
        if not site.startswith("http"):
            site = "https://" + site
        webbrowser.open(site)
        return f"Opening {site} in your browser."

    # SCREENSHOT
    if "screenshot" in cmd_lower:
        if not GUI_AVAILABLE:
            return "pyautogui not installed. Run: pip install pyautogui"
        filename = f"screenshot_{int(time.time())}.png"
        pyautogui.screenshot(filename)
        return f"Screenshot saved as {filename}"

    # TYPE TEXT
    if cmd_lower.startswith("type "):
        if not GUI_AVAILABLE:
            return "pyautogui not installed. Run: pip install pyautogui"
        text = cmd[5:].strip()
        time.sleep(1)
        pyautogui.typewrite(text, interval=0.05)
        return f"Typed: {text}"

    # CLICK
    if cmd_lower.startswith("click "):
        if not GUI_AVAILABLE:
            return "pyautogui not installed. Run: pip install pyautogui"
        parts = cmd_lower.replace("click", "").strip().split()
        if len(parts) == 2:
            try:
                x, y = int(parts[0]), int(parts[1])
                pyautogui.click(x, y)
                return f"Clicked at ({x}, {y})"
            except ValueError:
                pass
        pyautogui.click()
        return "Clicked at current mouse position."

    # MOVE MOUSE
    if cmd_lower.startswith("move mouse "):
        if not GUI_AVAILABLE:
            return "pyautogui not installed. Run: pip install pyautogui"
        parts = cmd_lower.replace("move mouse", "").strip().split()
        if len(parts) == 2:
            try:
                x, y = int(parts[0]), int(parts[1])
                pyautogui.moveTo(x, y, duration=0.5)
                return f"Mouse moved to ({x}, {y})"
            except ValueError:
                return "Usage: move mouse [x] [y]"

    # SCROLL
    if cmd_lower.startswith("scroll up"):
        if not GUI_AVAILABLE:
            return "pyautogui not installed. Run: pip install pyautogui"
        pyautogui.scroll(5)
        return "Scrolled up."

    if cmd_lower.startswith("scroll down"):
        if not GUI_AVAILABLE:
            return "pyautogui not installed. Run: pip install pyautogui"
        pyautogui.scroll(-5)
        return "Scrolled down."

    # VOLUME (Windows)
    if "volume up" in cmd_lower:
        subprocess.run(["powershell", "-c",
            "(New-Object -comObject WScript.Shell).SendKeys([char]175)"], capture_output=True)
        return "Volume increased."

    if "volume down" in cmd_lower:
        subprocess.run(["powershell", "-c",
            "(New-Object -comObject WScript.Shell).SendKeys([char]174)"], capture_output=True)
        return "Volume decreased."

    if "mute" in cmd_lower:
        subprocess.run(["powershell", "-c",
            "(New-Object -comObject WScript.Shell).SendKeys([char]173)"], capture_output=True)
        return "Toggled mute."

    # LOCK SCREEN
    if "lock" in cmd_lower and "screen" in cmd_lower:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "Screen locked."

    # SHUTDOWN / RESTART
    if cmd_lower == "shutdown":
        subprocess.run(["shutdown", "/s", "/t", "30"])
        return "Shutting down in 30 seconds. Type 'cancel shutdown' to stop."

    if cmd_lower == "cancel shutdown":
        subprocess.run(["shutdown", "/a"])
        return "Shutdown cancelled."

    if cmd_lower == "restart":
        subprocess.run(["shutdown", "/r", "/t", "30"])
        return "Restarting in 30 seconds. Type 'cancel shutdown' to stop."

    # LIST COMMANDS
    if cmd_lower in ["help", "commands", "what can you do"]:
        return """
Computer control commands:
  open [app]          - Open any app (e.g. open notepad)
  search [query]      - Google search
  go to [website]     - Open a website
  screenshot          - Take a screenshot
  type [text]         - Type text (needs pyautogui)
  click [x] [y]       - Click at position (needs pyautogui)
  move mouse [x] [y]  - Move mouse (needs pyautogui)
  scroll up/down      - Scroll (needs pyautogui)
  volume up/down      - Adjust volume
  mute                - Toggle mute
  lock screen         - Lock your PC
  shutdown/restart    - Shutdown or restart PC

For mouse/keyboard commands, install pyautogui:
  pip install pyautogui
"""

    return None  # Not a computer command — pass to JARVIS

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="JARVIS VS Code Client")
parser.add_argument("--save-url", metavar="URL", help="Save a new ngrok URL and connect")
parser.add_argument("--reset-url", action="store_true", help="Forget the saved URL and enter a new one")
parser.add_argument("--offline", action="store_true", help="Computer control only, no JARVIS AI connection")
args = parser.parse_args()

if args.reset_url and os.path.exists(URL_SAVE_FILE):
    os.remove(URL_SAVE_FILE)
    print("Saved URL cleared.\n")

jarvis_url = None
if not args.offline:
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
if not GUI_AVAILABLE:
    print("  Tip: pip install pyautogui for mouse/keyboard control")
print("  Type 'commands' to see all computer controls")
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

    # Try computer command first
    result = handle_computer_command(user_input)
    if result:
        print(f"JARVIS: {result}\n")
        continue

    # Otherwise send to JARVIS AI
    if jarvis_url:
        print("JARVIS: Thinking...", end="\r")
        answer = ask_jarvis(jarvis_url, user_input)
        print(f"JARVIS: {answer}\n")
    else:
        print("JARVIS: No AI connection. Run without --offline to connect.\n")
