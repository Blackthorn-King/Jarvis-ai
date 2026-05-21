import urllib.request
import urllib.error
import json
import sys
import os
import argparse
import subprocess
import webbrowser
import time
import threading

# --- Optional: pyautogui for mouse/keyboard control ---
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# --- Optional: speech recognition for voice input ---
try:
    import speech_recognition as sr
    VOICE_INPUT_AVAILABLE = True
except ImportError:
    VOICE_INPUT_AVAILABLE = False

# --- Optional: pyttsx3 for voice output (JARVIS speaks back) ---
try:
    import pyttsx3
    tts_engine = pyttsx3.init()
    tts_engine.setProperty("rate", 175)
    voices = tts_engine.getProperty("voices")
    for v in voices:
        if "male" in v.name.lower() or "david" in v.name.lower() or "mark" in v.name.lower():
            tts_engine.setProperty("voice", v.id)
            break
    VOICE_OUTPUT_AVAILABLE = True
except ImportError:
    VOICE_OUTPUT_AVAILABLE = False

URL_SAVE_FILE = os.path.join(os.path.dirname(__file__), ".jarvis_url")

def load_saved_url():
    if os.path.exists(URL_SAVE_FILE):
        with open(URL_SAVE_FILE, "r") as f:
            return f.read().strip()
    return None

def save_url(url):
    with open(URL_SAVE_FILE, "w") as f:
        f.write(url)

def speak(text, voice_mode=False):
    print(f"JARVIS: {text}\n")
    if voice_mode and VOICE_OUTPUT_AVAILABLE:
        tts_engine.say(text)
        tts_engine.runAndWait()

def listen_for_voice():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 3000
    recognizer.dynamic_energy_threshold = True
    with sr.Microphone() as source:
        print("JARVIS: Listening... (speak now)", end="\r")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)
            print("JARVIS: Processing...          ", end="\r")
            text = recognizer.recognize_google(audio)
            print(f"You (voice): {text}")
            return text
        except sr.WaitTimeoutError:
            print("JARVIS: No speech detected.    ")
            return None
        except sr.UnknownValueError:
            print("JARVIS: Could not understand.  ")
            return None
        except sr.RequestError as e:
            print(f"JARVIS: Voice service error: {e}")
            return None

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
        return f"Connection error: Could not reach JARVIS: {e.reason}"
    except Exception as e:
        return f"Error: {e}"

# --- Computer Control Commands ---
def handle_computer_command(cmd):
    cmd_lower = cmd.lower().strip()

    if cmd_lower.startswith("open "):
        app = cmd[5:].strip()
        try:
            subprocess.Popen(app, shell=True)
            return f"Opening {app}."
        except Exception as e:
            return f"Could not open {app}: {e}"

    if cmd_lower.startswith("search "):
        query = cmd[7:].strip()
        webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        return f"Searching Google for: {query}"

    if cmd_lower.startswith("go to ") or cmd_lower.startswith("visit "):
        site = cmd.split(" ", 2)[-1].strip()
        if not site.startswith("http"):
            site = "https://" + site
        webbrowser.open(site)
        return f"Opening {site} in your browser."

    if "screenshot" in cmd_lower:
        if not GUI_AVAILABLE:
            return "pyautogui not installed. Run: pip install pyautogui"
        filename = f"screenshot_{int(time.time())}.png"
        pyautogui.screenshot(filename)
        return f"Screenshot saved as {filename}"

    if cmd_lower.startswith("type "):
        if not GUI_AVAILABLE:
            return "pyautogui not installed. Run: pip install pyautogui"
        text = cmd[5:].strip()
        time.sleep(1)
        pyautogui.typewrite(text, interval=0.05)
        return f"Typed: {text}"

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

    if "lock" in cmd_lower and "screen" in cmd_lower:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "Screen locked."

    if cmd_lower == "shutdown":
        subprocess.run(["shutdown", "/s", "/t", "30"])
        return "Shutting down in 30 seconds. Say cancel shutdown to stop."

    if cmd_lower == "cancel shutdown":
        subprocess.run(["shutdown", "/a"])
        return "Shutdown cancelled."

    if cmd_lower == "restart":
        subprocess.run(["shutdown", "/r", "/t", "30"])
        return "Restarting in 30 seconds. Say cancel shutdown to stop."

    if cmd_lower in ["help", "commands", "what can you do"]:
        return (
            "Computer commands: open app, search query, go to website, "
            "screenshot, type text, click, move mouse, scroll up or down, "
            "volume up or down, mute, lock screen, shutdown, restart."
        )

    return None

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="JARVIS VS Code Client")
parser.add_argument("--save-url", metavar="URL", help="Save a new ngrok URL and connect")
parser.add_argument("--reset-url", action="store_true", help="Forget the saved URL and enter a new one")
parser.add_argument("--offline", action="store_true", help="Computer control only, no JARVIS AI connection")
parser.add_argument("--voice", action="store_true", help="Enable voice mode (speak to JARVIS)")
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

voice_mode = args.voice
if voice_mode and not VOICE_INPUT_AVAILABLE:
    print("Voice input not available. Install with:")
    print("  pip install SpeechRecognition pyaudio pyttsx3\n")
    print("Falling back to text mode.\n")
    voice_mode = False

print("="*50)
print("  JARVIS - VS Code Client")
if voice_mode:
    print("  Voice mode ON - press Enter to speak")
    if VOICE_OUTPUT_AVAILABLE:
        print("  JARVIS will speak responses aloud")
else:
    print("  Text mode - type your message")
    if not voice_mode:
        print("  Tip: run with --voice to enable voice mode")
if not GUI_AVAILABLE:
    print("  Tip: pip install pyautogui for mouse/keyboard control")
print("  Type 'commands' to see all computer controls")
print("  Type 'exit' or 'quit' to stop")
print("="*50 + "\n")

while True:
    try:
        if voice_mode:
            input("[ Press Enter to speak ]")
            user_input = listen_for_voice()
            if not user_input:
                continue
        else:
            user_input = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nJARVIS: Goodbye!")
        break

    if not user_input:
        continue

    if user_input.lower() in ["exit", "quit"]:
        speak("Goodbye!", voice_mode)
        break

    result = handle_computer_command(user_input)
    if result:
        speak(result, voice_mode)
        continue

    if jarvis_url:
        print("JARVIS: Thinking...", end="\r")
        answer = ask_jarvis(jarvis_url, user_input)
        speak(answer, voice_mode)
    else:
        speak("No AI connection. Run without --offline to connect.", voice_mode)
